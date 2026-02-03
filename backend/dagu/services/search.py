"""
Search Aggregator Service for MALCHA-DAGU.

Combines Naver Shopping API results with user-posted listings.
"""

from __future__ import annotations

import logging
from typing import Any

from django.db import models
from django.utils import timezone

from ..config import CategoryConfig
from ..filters import calculate_match_score, filter_user_item, filter_user_item_by_brand
from ..models import Instrument, UserItem, SearchMissLog
from .naver import NaverShoppingService
from .utils import (
    normalize_search_term,
    tokenize_query,
    expand_query_with_aliases,
    find_best_matching_instruments,
    extract_brand,
    normalize_brand,
    is_known_brand,
    mask_sensitive_data,
)

logger = logging.getLogger(__name__)


class SearchAggregatorService:
    """
    네이버 쇼핑 + DB 유저 매물 통합 검색 서비스.

    Flow:
        1. DB에서 검색어와 매칭되는 Instrument 찾기 (스코어 기반)
        2. 매칭된 악기 정보로 네이버 API 검색 최적화
        3. 유저 등록 매물 검색 (매칭된 악기 우선)
        4. 가격순 병합 정렬

    Usage:
        >>> service = SearchAggregatorService()
        >>> result = service.search("BOSS DS-1", display=20)
    """

    def __init__(self) -> None:
        self.naver_service = NaverShoppingService()

    def search(self, query: str, display: int = 20) -> dict[str, Any]:
        """
        통합 검색 수행.

        Args:
            query: 검색어
            display: 결과 개수

        Returns:
            {
                'query': str,
                'total_count': int,
                'reference': { ... },  # 신품 기준가 정보
                'items': [ ... ],      # 가격순 통합 결과
                'naver_items': [ ... ],
                'user_items': [ ... ],
            }
        """
        # 브랜드/카테고리 추출 (utils 통합 함수 사용)
        brand = extract_brand(query)
        category = self._detect_category(query)


        # Step 1: DB에서 매칭 악기 찾기
        matching_instruments, best_match = self._find_matching_instruments(query)
        # Step 2: 네이버 검색 (최적화된 쿼리)
        search_query, brand, category = self._build_search_query(
            query, best_match, brand, category
        )
        logger.error(f"쿼리는='{best_match[0]}', brand={brand}, category={category}")
        # 신품 기준가 가져오기 (가격 필터링용)
        reference_price = None
        if best_match:
            reference_price = best_match[0].reference_price
        naver_items = self.naver_service.search(
            query=search_query,
            display=display,
            brand=brand,
            category=category,
            reference_price=reference_price,
        )


        # Step 3: 유저 매물 검색 (동일 필터 적용)
        user_items, reference_info = self._search_user_items(
            query, matching_instruments, best_match, display, category
        )

        # Step 4: 가격순 + 연장 우선순위 병합
        all_items = naver_items + user_items
        # 정렬: 1) 가격 오름차순, 2) 연장된 매물 우선 (extended_at 있으면 0, 없으면 1)
        all_items.sort(key=lambda x: (
            x.get('lprice', 0),
            0 if x.get('extended_at') else 1
        ))

        logger.error(
            f"검색 완료: 네이버({len(naver_items)}) + "
            f"유저({len(user_items)}) = 총({len(all_items)})"
        )

        # 매칭된 악기 정보 (매물 등록용)
        matched_instrument = None
        if best_match:
            inst = best_match[0]
            matched_instrument = {
                'id': str(inst.id),
                'name': inst.name,
                'brand': inst.brand,
                'category': inst.category,
            }
        else:
            # DB 미매칭 검색어 로깅 (자주 검색되지만 DB에 없는 악기 추적)
            SearchMissLog.log_miss(mask_sensitive_data(query))

        return {
            'query': query,
            'search_query': search_query,  # 정규화된 검색어 (외부 링크용)
            'total_count': len(all_items),
            'reference': reference_info,
            'matched_instrument': matched_instrument,  # 매물 등록용 악기 정보
            'items': all_items,
            'naver_items': naver_items,
            'user_items': user_items,
            'is_valid_query': True,
        }

    def _is_whitelisted_query(self, query: str) -> bool:
        """
        검색어가 악기 관련 키워드를 포함하는지 확인 (화이트리스트 검증).
        브랜드명, 카테고리명, 악기명 등이 포함되어야 API 호출을 허용.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return False

        from ..config import CategoryConfig
        
        # 0. [사용자 커스텀] 화이트리스트 최우선 확인
        custom_whitelist = getattr(CategoryConfig, 'CUSTOM_WHITELIST_KEYWORDS', [])
        for kw in custom_whitelist:
            if kw and kw in query_lower:
                logger.debug(f"[Whitelist] 통과: 커스텀 키워드 감지 '{kw}'")
                return True

        # 1. 알려진 브랜드 확인 (extract_brand는 너무 관대하므로 is_known_brand로 재검증)
        detected_brand = extract_brand(query)
        if detected_brand and is_known_brand(detected_brand):
            logger.debug(f"[Whitelist] 통과: 알려진 브랜드 감지 '{detected_brand}'")
            return True

        # 2. 카테고리별 키워드 확인 (BASS_KEYWORDS, PEDAL_KEYWORDS 등)
        category_attrs = [
            'BASS_KEYWORDS', 'PEDAL_KEYWORDS', 
            'AMP_KEYWORDS', 'ACOUSTIC_KEYWORDS', 'MIC_KEYWORDS'
        ]
        for attr in category_attrs:
            keywords = getattr(CategoryConfig, attr, [])
            for kw in keywords:
                if kw and kw in query_lower:
                    logger.debug(f"[Whitelist] 통과: 카테고리 키워드 감지 '{kw}'")
                    return True

        # 3. VALID_INSTRUMENT_CATEGORIES (한글 악기명)
        from ..config import FilterConfig
        valid_cats = getattr(FilterConfig, 'VALID_INSTRUMENT_CATEGORIES', {})
        for cat_list in valid_cats.values():
            for kw in cat_list:
                if kw and kw in query_lower:
                    logger.debug(f"[Whitelist] 통과: 유효 악기명 감지 '{kw}'")
                    return True

        # 4. 모델 별칭 검증 (ds1, strat 등)
        aliases = getattr(CategoryConfig, 'MODEL_ALIASES', {})
        for alias_key in aliases.keys():
            if alias_key and alias_key in query_lower:
                logger.debug(f"[Whitelist] 통과: 모델 별칭 감지 '{alias_key}'")
                return True

        # 5. 최소한의 일반 명칭 (매우 제한적)
        minimal_whitelist = ['guitar', 'bass', 'amp', 'pedal', 'mic', '기타', '베이스', '앰프', '페달', '마이크', '악기']
        for kw in minimal_whitelist:
            if kw in query_lower:
                logger.debug(f"[Whitelist] 통과: 일반 악기 명칭 감지 '{kw}'")
                return True

        logger.info(f"[Whitelist] 차단: '{query}' - 악기 관련 키워드 없음")
        return False

    def search_with_cache(self, query: str, display: int, cache, cache_ttl: int) -> dict[str, Any]:
        """
        네이버 결과만 캐싱하고 유저 매물은 실시간 조회하는 검색.
        
        Args:
            query: 검색어
            display: 결과 개수
            cache: Django cache instance
            cache_ttl: 캐시 TTL (초)
        
        Returns:
            search() 메서드와 동일한 형식
        """
        # [2026-02-03] 화이트리스트 검증 비활성화 - 리스트에 없는 악기도 검색 가능하도록
        # Step 0: 화이트리스트 검증 (API 호출 전 사전 차단) - 비활성화
        # if not self._is_whitelisted_query(query):
        #     logger.info(f"[Whitelist] 차단된 검색어: '{query}'")
        #     return {
        #         'query': query,
        #         'search_query': query,
        #         'total_count': 0,
        #         'items': [],
        #         'naver_items': [],
        #         'user_items': [],
        #         'reference': None,
        #         'matched_instrument': None,
        #         'is_valid_query': False, # 프론트엔드 알림용
        #     }

        # 브랜드/카테고리 추출
        brand = extract_brand(query)
        category = self._detect_category(query)

        # Step 1: DB에서 매칭 악기 찾기
        matching_instruments, best_match = self._find_matching_instruments(query)
        
        # Step 2: 네이버 검색용 쿼리 생성
        search_query, brand, category = self._build_search_query(
            query, best_match, brand, category
        )
        logger.error(f"쿼리는='{best_match[0] if best_match else query}', brand={brand}, category={category}")
        
        # 신품 기준가
        reference_price = best_match[0].reference_price if best_match else None
        
        # Step 3: 네이버 결과 조회 (캐싱 적용)
        naver_cache_key = f"naver:{search_query.lower()}:{display}:{brand or ''}:{category or ''}"
        naver_items = cache.get(naver_cache_key)
        
        if naver_items is None:
            # 캐시 미스: 네이버 API 호출
            naver_items = self.naver_service.search(
                query=search_query,
                display=display,
                brand=brand,
                category=category,
                reference_price=reference_price,
            )
            cache.set(naver_cache_key, naver_items, cache_ttl)
            logger.debug(f"[Naver Cache SET] {naver_cache_key} (TTL: {cache_ttl}s)")
        else:
            logger.debug(f"[Naver Cache HIT] {naver_cache_key}")

        # Step 4: 유저 매물 실시간 조회 (캐싱 없음)
        user_items, reference_info = self._search_user_items(
            query, matching_instruments, best_match, display, category
        )

        # Step 5: 가격순 + 연장 우선순위 병합
        all_items = naver_items + user_items
        all_items.sort(key=lambda x: (
            x.get('lprice', 0),
            0 if x.get('extended_at') else 1
        ))

        logger.info(
            f"검색 완료: 네이버({len(naver_items)}) + "
            f"유저({len(user_items)}) = 총({len(all_items)})"
        )

        # 매칭된 악기 정보 (매물 등록용)
        matched_instrument = None
        if best_match:
            inst = best_match[0]
            matched_instrument = {
                'id': str(inst.id),
                'name': inst.name,
                'brand': inst.brand,
                'category': inst.category,
            }
        else:
            # DB 미매칭 검색어 로깅
            SearchMissLog.log_miss(query)

        return {
            'query': query,
            'search_query': search_query,
            'total_count': len(all_items),
            'reference': reference_info,
            'matched_instrument': matched_instrument,
            'items': all_items,
            'naver_items': naver_items,
            'user_items': user_items,
        }

    def _detect_category(self, query: str) -> str | None:
        """
        검색어에서 카테고리 추론.
        
        Returns:
            카테고리 문자열 또는 None (확신 없음)
        """
        query_lower = query.lower()

        bass_keywords = getattr(CategoryConfig, 'BASS_KEYWORDS', [])
        pedal_keywords = getattr(CategoryConfig, 'PEDAL_KEYWORDS', [])
        amp_keywords = getattr(CategoryConfig, 'AMP_KEYWORDS', [])
        acoustic_keywords = getattr(CategoryConfig, 'ACOUSTIC_KEYWORDS', [])
        mic_keywords = getattr(CategoryConfig, 'MIC_KEYWORDS', [])

        if any(kw in query_lower for kw in bass_keywords):
            return 'bass'
        if any(kw in query_lower for kw in pedal_keywords):
            return 'effect'  # DB: 'effect' = 이펙터
        if any(kw in query_lower for kw in amp_keywords):
            return 'amp'
        if any(kw in query_lower for kw in acoustic_keywords):
            return 'acoustic'
        if any(kw in query_lower for kw in mic_keywords):
            return 'mic'

        # 확신할 수 없으면 None 반환 (DB 카테고리 우선 사용하도록)
        return None

    def _find_matching_instruments(
        self,
        query: str,
    ) -> tuple[list[Instrument], tuple[Instrument, float] | None]:
        """
        DB에서 매칭 악기 찾기 (스마트 매칭).

        Returns:
            (matching_instruments, best_match)
        """
        query_tokens = tokenize_query(query)
        expanded_queries = expand_query_with_aliases(query)

        # 브랜드 정규화 (펜더 → fender)
        normalized_query = normalize_brand(query)
        brand = extract_brand(query)

        # 후보 필터 구성
        candidate_filter = models.Q()

        # 원본 토큰으로 검색
        for token in query_tokens:
            candidate_filter |= models.Q(name__icontains=token)
            candidate_filter |= models.Q(brand__icontains=token)

        # 별칭 확장으로 검색 (스트랫 → Stratocaster)
        for expanded in expanded_queries:
            candidate_filter |= models.Q(name__icontains=expanded)
            candidate_filter |= models.Q(brand__icontains=expanded)
            for token in expanded.split():
                if len(token) > 1:
                    candidate_filter |= models.Q(name__icontains=token)

        # 브랜드로 직접 검색 (펜더 → fender 변환됨)
        if brand:
            candidate_filter |= models.Q(brand__iexact=brand)
            candidate_filter |= models.Q(brand__icontains=brand)

        query_lower = query.lower().strip()
        candidate_filter |= models.Q(name__icontains=query_lower)
        candidate_filter |= models.Q(brand__icontains=query_lower)

        logger.debug(f"별칭 확장: {query} -> {expanded_queries}")

        # 후보 조회 (Unknown 브랜드 제외)
        candidates = Instrument.objects.filter(
            candidate_filter
        ).exclude(
            brand__iexact='unknown'
        )[:50]

        logger.debug(f"후보 악기 {candidates.count()}개 조회됨")

        # 스코어링 기반 매칭
        scored_matches = find_best_matching_instruments(
            query=query,
            instruments_qs=candidates,
            min_score=0.3,
        )

        matching_instruments = [inst for inst, _ in scored_matches[:10]]
        best_match = scored_matches[0] if scored_matches else None

        if best_match:
            logger.info(
                f"[DB 매칭] '{query}' -> "
                f"'{best_match[0].brand} {best_match[0].name}' "
                f"(score={best_match[1]:.2f})"
            )

        return matching_instruments, best_match

    def _build_search_query(
        self,
        original_query: str,
        best_match: tuple[Instrument, float] | None,
        brand: str | None,
        detected_category: str | None,
    ) -> tuple[str, str | None, str | None]:
        """
        네이버 검색용 최적화된 쿼리 생성.

        Args:
            detected_category: 검색어에서 감지된 카테고리 (None = 확신 없음)

        Returns:
            (search_query, brand, category)
        """
        search_query = original_query
        category = detected_category  # 검색어 기반 카테고리 (None일 수 있음)

        # 사용자가 입력한 브랜드 추출 (있으면 존중)
        user_brand = extract_brand(original_query)

        if best_match and best_match[1] >= 0.5:
            instrument = best_match[0]

            # 사용자가 입력한 브랜드와 DB 브랜드가 다르면 → 사용자 브랜드 존중
            if user_brand and user_brand.lower() != instrument.brand.lower():
                # [Fix] 사용자 브랜드가 이미 모델명에 포함되어 있으면, 브랜드가 아니라 모델명일 가능성이 높음
                # 예: "sm57" 검색 -> brand='sm57' (오탐), name='sm57' -> 이 경우 DB 브랜드 'Shure'를 사용해야 함
                if user_brand.lower() in instrument.name.lower():
                    search_query = f"{instrument.brand} {instrument.name}"
                    brand = instrument.brand.lower() if instrument.brand else brand
                    logger.info(f"[오탐 보정] '{user_brand}'는 모델명임 -> DB 브랜드 '{brand}' 사용")
                else:
                    # 진짜 다른 브랜드인 경우 (예: Squier vs Fender)
                    search_query = f"{user_brand} {instrument.name}"
                    brand = user_brand.lower()
                    logger.info(f"[쿼리 변환] '{original_query}' -> '{search_query}' (사용자 브랜드 유지)")
            else:
                search_query = f"{instrument.brand} {instrument.name}"
                brand = instrument.brand.lower() if instrument.brand else brand
                logger.info(f"[쿼리 변환] '{original_query}' -> '{search_query}'")

            # 카테고리 결정: DB 정보 우선 사용, 없으면 검색어 감지 결과 사용
            if instrument.category:
                # 1순위: DB Instrument 카테고리 (가장 신뢰)
                category = instrument.category
                logger.info(f"[카테고리] DB 기반: {category}")
            elif detected_category is not None:
                # 2순위: 검색어에서 감지된 카테고리
                category = detected_category
                logger.debug(f"[카테고리] 검색어 기반: {category} (DB 정보 없음)")
        else:
            # 한글 브랜드 -> 영문 치환
            search_query = normalize_brand(original_query)

            # 모델명 별칭도 확장 (스트랫 -> Stratocaster 등)
            tokens = search_query.split()
            expanded_tokens = []
            for token in tokens:
                expanded = expand_query_with_aliases(token)
                alias = next((e for e in expanded if e.lower() != token.lower()), None)
                expanded_tokens.append(alias if alias else token)
            search_query = ' '.join(expanded_tokens)
            logger.info(f"[쿼리 확장] '{original_query}' -> '{search_query}'")

        logger.info(f"검색 시작: '{search_query}' (브랜드: {brand}, 카테고리: {category})")

        return search_query, brand, category

    def _search_user_items(
        self,
        query: str,
        matching_instruments: list[Instrument],
        best_match: tuple[Instrument, float] | None,
        display: int,
        category: str = None,
    ) -> tuple[list[dict], dict | None]:
        """
        유저 매물 검색.

        Returns:
            (user_items, reference_info)
        """
        now = timezone.now()

        # 1. 쿼리를 토큰으로 분리하여 AND 조건으로 검색
        # 모든 토큰이 title/brand/name 중 하나에 포함되어야 결과에 포함
        query_tokens = [t.lower() for t in query.split() if len(t) > 1]
        
        if query_tokens:
            # AND 기반 필터 구성
            q_filter = models.Q()
            for i, token in enumerate(query_tokens):
                token_condition = (
                    models.Q(title__icontains=token) |
                    models.Q(instrument__name__icontains=token) |
                    models.Q(instrument__brand__icontains=token)
                )
                if i == 0:
                    q_filter = token_condition
                else:
                    q_filter &= token_condition  # AND 결합
        else:
            # 토큰이 없으면 전체 query로 검색
            q_filter = models.Q(instrument__name__icontains=query) | \
                       models.Q(instrument__brand__icontains=query) | \
                       models.Q(title__icontains=query)

        # best_match가 있으면 해당 악기의 매물도 추가 (정확히 일치하는 악기만)
        if best_match and best_match[1] >= 0.8:  # 점수 0.8 이상만
            q_filter |= models.Q(instrument=best_match[0])

        # 부모-자식 계층형 검색: best_match가 있으면 해당 악기의 자식들도 포함
        if best_match and best_match[1] >= 0.8:
            parent_instrument = best_match[0]
            descendants = parent_instrument.get_all_descendants()
            if descendants:
                q_filter |= models.Q(instrument__in=descendants)
                logger.info(
                    f"[계층형 검색] '{parent_instrument}' 하위 악기 {len(descendants)}개 포함"
                )

        logger.info(f"UserItem search filter: {q_filter}")

        user_items_qs = UserItem.objects.filter(
            q_filter,
            # is_active=True,         # 유저 요청으로 활성 체크 해제
            # is_under_review=False,  # 유저 요청으로 검토 체크 해제
            # expired_at__gt=now,     # 만료 체크 해제
        ).select_related('instrument')[:display * 2]
        
        logger.info(f"Found {user_items_qs.count()} user items")

        # 딕셔너리 변환 + 필터링 제거 (유저 매물은 필터링하지 않음)
        user_items = []
        reference_info = None

        for item in user_items_qs:
            title = item.title or str(item.instrument)

            # [필터 1] 브랜드 필터링 - 검색 브랜드와 매물 브랜드 불일치 시 제외
            if not filter_user_item_by_brand(query, item.instrument.brand):
                continue

            if len(user_items) >= display:
                break

            user_items.append({
                'id': str(item.id),
                'title': title,
                'link': item.link,
                'image': item.instrument.image_url,
                'lprice': item.price,
                'source': item.source,
                'source_display': item.get_source_display(),
                'discount_rate': item.discount_rate,
                'instrument_id': str(item.instrument.id),
                'instrument_name': item.instrument.name,
                'instrument_brand': item.instrument.brand,
                'score': calculate_match_score(query, title, item.instrument.image_url),
                'extended_at': item.extended_at.isoformat() if item.extended_at else None,
                'report_count': item.report_count,
                'owner_id': item.owner_id,
            })

            # 신품 기준가 정보 (첫 번째 매물 기준)
            if reference_info is None and item.instrument.reference_price > 0:
                reference_info = {
                    'name': str(item.instrument),
                    'price': item.instrument.reference_price,
                    'image_url': item.instrument.image_url,
                }

        # 기준가 보완 (best_match 또는 DB 검색)
        reference_info = self._get_reference_info(
            reference_info, best_match, query
        )

        return user_items, reference_info

    def _get_reference_info(
        self,
        existing_ref: dict | None,
        best_match: tuple[Instrument, float] | None,
        query: str,
    ) -> dict | None:
        """신품 기준가 정보 조회"""
        if existing_ref:
            return existing_ref

        # best_match 우선
        if best_match:
            instrument = best_match[0]
            if instrument.reference_price > 0:
                return {
                    'name': str(instrument),
                    'price': instrument.reference_price,
                    'image_url': instrument.image_url,
                }

        # DB 검색 fallback
        instrument = Instrument.objects.filter(
            models.Q(name__icontains=query) |
            models.Q(brand__icontains=query)
        ).first()

        if instrument and instrument.reference_price > 0:
            return {
                'name': str(instrument),
                'price': instrument.reference_price,
                'image_url': instrument.image_url,
            }

        return None
