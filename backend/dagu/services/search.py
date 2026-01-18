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
from ..filters import calculate_match_score, filter_user_item
from ..models import Instrument, UserItem, SearchMissLog
from .naver import NaverShoppingService
from .utils import (
    normalize_search_term,
    tokenize_query,
    expand_query_with_aliases,
    find_best_matching_instruments,
    extract_brand,
    normalize_brand,
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

        logger.debug(f"query='{query}', brand={brand}, category={category}")

        # Step 1: DB에서 매칭 악기 찾기
        matching_instruments, best_match = self._find_matching_instruments(query)

        # Step 2: 네이버 검색 (최적화된 쿼리)
        search_query, brand, category = self._build_search_query(
            query, best_match, brand, category
        )

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

        logger.info(
            f"검색 완료: 네이버({len(naver_items)}) + "
            f"유저({len(user_items)}) = 총({len(all_items)})"
        )

        return {
            'query': query,
            'search_query': search_query,  # 정규화된 검색어 (외부 링크용)
            'total_count': len(all_items),
            'reference': reference_info,
            'items': all_items,
            'naver_items': naver_items,
            'user_items': user_items,
        }

    def _detect_category(self, query: str) -> str:
        """검색어에서 카테고리 추론 (DB 값과 일치)"""
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

        return 'guitar'

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
        category: str,
    ) -> tuple[str, str | None, str]:
        """
        네이버 검색용 최적화된 쿼리 생성.

        Returns:
            (search_query, brand, category)
        """
        search_query = original_query
        detected_category = category  # 검색어 기반 카테고리 보존

        # 사용자가 입력한 브랜드 추출 (있으면 존중)
        user_brand = extract_brand(original_query)

        if best_match and best_match[1] >= 0.5:
            instrument = best_match[0]

            # 사용자가 입력한 브랜드와 DB 브랜드가 다르면 → 사용자 브랜드 존중
            # 예: "squier stratocaster" 검색 시 DB에 fender stratocaster만 있어도 squier 유지
            if user_brand and user_brand.lower() != instrument.brand.lower():
                # 모델명만 DB에서 가져오고, 브랜드는 사용자 입력 유지
                search_query = f"{user_brand} {instrument.name}"
                brand = user_brand.lower()
                logger.info(f"[쿼리 변환] '{original_query}' -> '{search_query}' (사용자 브랜드 유지)")
            else:
                # 브랜드 일치 또는 브랜드 없음 → DB 정보 사용
                search_query = f"{instrument.brand} {instrument.name}"
                brand = instrument.brand.lower() if instrument.brand else brand
                logger.info(f"[쿼리 변환] '{original_query}' -> '{search_query}'")

            # 검색어 기반 카테고리 우선 (페달 키워드 감지 시 DB 카테고리 무시)
            if detected_category != 'guitar':
                category = detected_category
            elif instrument.category:
                category = instrument.category
        else:
            # 한글 브랜드 -> 영문 치환
            search_query = normalize_brand(original_query)

            # 모델명 별칭도 확장 (스트랫 -> Stratocaster 등)
            tokens = search_query.split()
            expanded_tokens = []
            for token in tokens:
                expanded = expand_query_with_aliases(token)
                # 별칭이 있으면 첫 번째 확장된 값 사용 (원본 제외)
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

        if matching_instruments:
            # 매칭된 악기들의 UserItem 검색
            user_items_qs = UserItem.objects.filter(
                is_active=True,
                is_under_review=False,  # 검토 중 매물 제외
                expired_at__gt=now,
                instrument__in=matching_instruments,
            ).select_related('instrument')[:display * 2]  # 필터링 여유분
        else:
            # 매칭 악기 없으면 제목/브랜드 검색
            user_items_qs = UserItem.objects.filter(
                is_active=True,
                is_under_review=False,  # 검토 중 매물 제외
                expired_at__gt=now,
            ).filter(
                models.Q(instrument__name__icontains=query) |
                models.Q(instrument__brand__icontains=query) |
                models.Q(title__icontains=query)
            ).select_related('instrument')[:display * 2]

        # 딕셔너리 변환 + 필터링 (네이버와 동일 기준)
        user_items = []
        reference_info = None

        for item in user_items_qs:
            title = item.title or str(item.instrument)

            # 통합 필터 적용 (블랙리스트 + 가격 + 카테고리)
            if not filter_user_item(title, item.price, category):
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
