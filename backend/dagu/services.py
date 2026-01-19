"""
Business logic for MALCHA-DAGU.

- NaverShoppingService: 네이버 쇼핑 API 연동 + 캐싱 + 필터링
- SearchAggregatorService: 네이버 + DB 데이터 병합
- AIDescriptionService: AI 악기 설명 생성
"""

import hashlib
import logging
import re
import concurrent.futures
from difflib import SequenceMatcher
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.utils import timezone

from .models import Instrument, UserItem
from .config import CrawlerConfig
from .filters import (
    filter_naver_item,
    clean_html_tags,
    calculate_match_score,
    check_blacklist,
    check_min_price,
    check_category_fields,
    check_product_type,
    build_exclusion_query,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

NAVER_API_URL = 'https://openapi.naver.com/v1/search/shop.json'
CACHE_TTL = 60 * 60  # 1시간 (초 단위)


# =============================================================================
# Naver Shopping API Service
# =============================================================================

class NaverShoppingService:
    """
    네이버 쇼핑 API 연동 서비스.
    Redis 캐싱으로 API 호출 최소화.
    필터링 로직으로 품질 향상.
    """
    
    def __init__(self):
        self.client_id = settings.NAVER_CLIENT_ID
        self.client_secret = settings.NAVER_CLIENT_SECRET
        self.headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
        }
    
    def _get_cache_key(self, query: str, display: int = 20) -> str:
        """캐시 키 생성 (검색어 해시)"""
        key_base = f"naver_search:{query}:{display}"
        return hashlib.md5(key_base.encode()).hexdigest()
    
    def search(
        self, 
        query: str, 
        display: int = 20, 
        sort: str = 'sim',  # 가격낮은순 (유저 요청 반영)
        brand: str = None,
        category: str = None,
        min_price: int = None,
    ) -> list[dict]:
        """
        네이버 쇼핑 API 검색 + 필터링.
        
        Args:
            query: 검색어
            display: 결과 개수 (최대 100)
            sort: 정렬 (sim: 정확도, date: 날짜, asc: 가격낮은순, dsc: 가격높은순)
            brand: 브랜드 필터 (선택)
            category: 카테고리 필터 (선택)
            min_price: 최소 가격 필터 (선택)
        
        Returns:
            필터링된 검색 결과 리스트
        """
        # 0. 검색어 정규화 (한글 브랜드 -> 영어로 통일하여 캐시 효율성 증대)
        from .config import CategoryConfig
        normalized_query = query
        for kr_name, en_brand in CategoryConfig.BRAND_NAME_MAPPING.items():
            if kr_name in query:
                normalized_query = query.replace(kr_name, en_brand)
                logger.debug(f"[Cache] 검색어 정규화: '{query}' -> '{normalized_query}'")
                break
        
        # 1. 캐시 확인 (정규화된 검색어로 캐시 키 생성)
        cache_key = self._get_cache_key(normalized_query, display * 3)  # 필터링 고려하여 3배 요청
        cached_result = cache.get(cache_key)
        
        raw_items = []
        
        if cached_result is not None:
            logger.debug(f"Cache HIT for query: {query}")
            raw_items = cached_result
        else:
            logger.info(f"📡 Cache MISS - API 호출 시작: {query}")
            
            # 2. API 호출 (API 키가 없으면 빈 리스트 반환)
            if not self.client_id or not self.client_secret:
                logger.warning("⚠️ Naver API credentials not configured")
                return []
            
            try:
                # 제외 키워드 추가 (API 레벨 필터링) - 일단 비활성화
                # enhanced_query = build_exclusion_query(normalized_query)
                enhanced_query = normalized_query  # 정규화된 쿼리 사용
                logger.info(f"네이버 API 검색: '{enhanced_query}'")
                
                # 필터링 대비 넉넉하게 500개 수집 (병렬 처리)
                target_count = 200
                page_size = 100
                starts = range(1, target_count, page_size)  # 1, 101, 201, 301, 401
                
                raw_items = []
                
                # 내부 함수: 단일 페이지 요청
                def fetch_page(start_idx):
                    try:
                        p = {
                            'query': enhanced_query,
                            'display': page_size,
                            'start': start_idx,
                            'sort': sort,
                            'exclude': 'rental',
                        }
                        # logger.debug(f"📤 API 요청 시작: start={start_idx}")
                        res = requests.get(
                            NAVER_API_URL,
                            headers=self.headers,
                            params=p,
                            timeout=CrawlerConfig.TIMEOUT_NAVER,
                        )
                        res.raise_for_status()
                        data = res.json()
                        items = data.get('items', [])
                        # logger.debug(f"📥 API 응답 완료: start={start_idx}, 가져온 개수={len(items)}")
                        return items
                    except Exception as e:
                        logger.error(f"Naver API Error (start={start_idx}): {e}")
                        return []

                # ThreadPoolExecutor로 병렬 실행 (속도 최적화)
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    logger.info(f"� 병렬 수집 시작: {target_count}개 목표 (Workers=5)")
                    results = executor.map(fetch_page, starts)
                    
                    for items in results:
                        raw_items.extend(items)
                
                logger.info(f"✅ 병렬 수집 완료: 총 {len(raw_items)}개 아이템 확보")
                
                # 캐싱 (원본 데이터)
                cache.set(cache_key, raw_items, CACHE_TTL)
                logger.debug(f"[Cache] 캐싱 완료: {len(raw_items)}개 아이템")
                
            except requests.exceptions.Timeout:
                logger.error(f"Naver API timeout for query: {query}")
                return []
            except requests.exceptions.RequestException as e:
                logger.error(f"Naver API error for query {query}: {e}")
                return []
            except Exception as e:
                logger.exception(f"Unexpected error in Naver API: {e}")
                return []
        
        # 3. 필터링 적용
        filtered_items = []
        stats = {
            'total': 0, 
            'price_fail': 0, 
            'blacklist_fail': 0, 
            'brand_fail': 0, 
            'category_fail': 0,
            'category_field_fail': 0,
            'product_type_fail': 0,
            'passed': 0
        }
        
        logger.debug(f"필터링 시작: {len(raw_items)}개 아이템")

        for item in raw_items:
            stats['total'] += 1
            title = item.get('title', '')[:50]
            logger.debug(f"처리 중: {title}")
            price = int(item.get('lprice', 0) or 0)
            
            # 필터링 함수 호출
            filtered = filter_naver_item(
                item=item,
                query=query,
                brand=brand,
                category=category,
                min_price=min_price,
            )
            
            if filtered:
                stats['passed'] += 1
                filtered_items.append(filtered)
                logger.debug(f"✅ 통과: [{price:,}원] {title}...")
                
                # 목표 개수 달성 시 중단
                if len(filtered_items) >= display:
                    break
            else:
                # 실패 원인 로깅 (DEBUG 레벨)
                logger.debug(f"❌ 탈락: [{price:,}원] {title}...")
        
        # 4. 스코어순 정렬 후 가격순 정렬
        filtered_items.sort(key=lambda x: (-x.get('score', 0), x.get('lprice', 0)))
        
        # 통계 로깅
        logger.info(
            f"📊 [Naver] 필터링 완료: "
            f"원본({stats['total']}) → 통과({stats['passed']}) → 반환({len(filtered_items[:display])})"
        )
        
        # 상위 3개 결과 미리보기
        if filtered_items:
            logger.info("🏆 상위 결과:")
            for i, item in enumerate(filtered_items[:3], 1):
                logger.info(f"   {i}. [{item['lprice']:,}원] {item['title'][:40]}... ({item.get('mallName', 'N/A')})")
        
        return filtered_items[:display]


# =============================================================================
# Search Utilities (검색 유틸리티)
# =============================================================================

def normalize_search_term(term: str) -> str:
    """
    검색어 정규화: 대소문자, 하이픈, 공백 통일
    예: "DS-1", "ds1", "ds 1", "DS 1" → "ds1"
    """
    if not term:
        return ""
    # 소문자 변환
    result = term.lower().strip()
    # 하이픈, 언더스코어, 공백 제거
    result = re.sub(r'[-_\s]+', '', result)
    return result


def expand_query_with_aliases(query: str) -> list[str]:
    """
    검색어를 별칭 매핑으로 확장
    예: "ds1" → ["ds1", "DS-1"]
    """
    from .config import CategoryConfig

    expanded = [query]
    query_lower = query.lower().strip()
    query_normalized = normalize_search_term(query)

    # 별칭 → 정식 모델명 변환
    aliases = getattr(CategoryConfig, 'MODEL_ALIASES', {})

    # 정규화된 검색어로 별칭 찾기
    if query_normalized in aliases:
        expanded.append(aliases[query_normalized])

    # 원본 검색어(소문자)로도 별칭 찾기
    if query_lower in aliases:
        expanded.append(aliases[query_lower])

    # 검색어의 각 토큰별로 별칭 확장
    for token in query_lower.split():
        token_norm = normalize_search_term(token)
        if token_norm in aliases:
            expanded.append(aliases[token_norm])
        if token in aliases:
            expanded.append(aliases[token])

    return list(set(expanded))


def tokenize_query(query: str) -> list[str]:
    """
    검색어를 토큰으로 분리
    예: "boss ds-1" → ["boss", "ds-1", "ds1"]
    """
    tokens = []
    # 공백으로 분리
    words = query.lower().strip().split()
    for word in words:
        tokens.append(word)
        # 하이픈 제거 버전도 추가
        normalized = re.sub(r'[-_]+', '', word)
        if normalized != word:
            tokens.append(normalized)
    return list(set(tokens))


def calculate_instrument_match_score(query: str, instrument) -> float:
    """
    검색어와 악기의 매칭 스코어 계산 (0.0 ~ 1.0)

    높은 점수 조건:
    - 모델명 정확 일치 (예: "ds-1" == "DS-1")
    - 브랜드+모델명 조합 일치
    - 별칭 매칭 (예: "ds1" → "DS-1")
    - 토큰 기반 부분 매칭
    """
    query_normalized = normalize_search_term(query)
    query_tokens = tokenize_query(query)

    # 검색어 별칭 확장 (ds1 → DS-1 등)
    expanded_queries = expand_query_with_aliases(query)

    name = instrument.name or ""
    brand = instrument.brand or ""
    name_normalized = normalize_search_term(name)
    brand_normalized = normalize_search_term(brand)
    full_name = f"{brand} {name}".strip()
    full_normalized = normalize_search_term(full_name)

    score = 0.0

    # 0. 별칭 확장된 쿼리로 정확 매칭 체크
    for expanded in expanded_queries:
        expanded_norm = normalize_search_term(expanded)
        if expanded_norm == name_normalized:
            score = 1.0
            logger.debug(f"[Score 1.0] 별칭 정확 일치: '{expanded}' == '{name}'")
            return score
        # 별칭이 모델명에 포함되어 있는지 확인 (예: "DS-1" in "BOSS DS-1 Distortion")
        if expanded.lower() in name.lower():
            score = 0.95
            logger.debug(f"[Score 0.95] 별칭 포함: '{expanded}' in '{name}'")
            return score

    # 1. 정규화된 모델명 정확 일치 (최고 점수)
    if query_normalized == name_normalized:
        score = 1.0
        logger.debug(f"[Score 1.0] 정확 일치: '{query}' == '{name}'")
        return score

    # 2. 정규화된 전체 이름(브랜드+모델) 정확 일치
    if query_normalized == full_normalized:
        score = 0.95
        logger.debug(f"[Score 0.95] 전체 일치: '{query}' == '{full_name}'")
        return score

    # 3. 모델명이 검색어에 포함 (예: "ds-1" in "boss ds-1")
    if name_normalized and name_normalized in query_normalized:
        score = 0.9
        logger.debug(f"[Score 0.9] 모델명 포함: '{name}' in '{query}'")
        return score

    # 4. 검색어가 모델명에 포함 (예: "ds" in "ds-1")
    if query_normalized and query_normalized in name_normalized:
        base_score = 0.7
        # 길이 비율로 보정 (짧은 검색어 페널티)
        length_ratio = len(query_normalized) / len(name_normalized) if name_normalized else 0
        score = base_score * length_ratio
        logger.debug(f"[Score {score:.2f}] 부분 포함: '{query}' in '{name}'")
        return max(score, 0.3)

    # 5. 토큰 기반 매칭 (별칭 포함)
    matched_tokens = 0
    all_tokens = query_tokens.copy()
    # 별칭 확장된 토큰도 추가
    for expanded in expanded_queries:
        all_tokens.extend(tokenize_query(expanded))
    all_tokens = list(set(all_tokens))

    for token in all_tokens:
        token_norm = normalize_search_term(token)
        if token_norm in name_normalized or token_norm in brand_normalized:
            matched_tokens += 1

    if matched_tokens > 0 and all_tokens:
        token_score = matched_tokens / len(all_tokens)
        score = 0.6 * token_score
        logger.debug(f"[Score {score:.2f}] 토큰 매칭: {matched_tokens}/{len(all_tokens)}")
        return score

    # 6. 유사도 기반 매칭 (SequenceMatcher)
    similarity = SequenceMatcher(None, query_normalized, name_normalized).ratio()
    if similarity > 0.6:
        score = 0.5 * similarity
        logger.debug(f"[Score {score:.2f}] 유사도: {similarity:.2f}")
        return score

    return score


def find_best_matching_instruments(query: str, instruments_qs, min_score: float = 0.3):
    """
    검색어에 가장 잘 맞는 악기들을 스코어 순으로 반환

    Args:
        query: 검색어
        instruments_qs: Instrument QuerySet
        min_score: 최소 스코어 (이하는 제외)

    Returns:
        list of (instrument, score) tuples, sorted by score desc
    """
    scored_instruments = []

    for instrument in instruments_qs:
        score = calculate_instrument_match_score(query, instrument)
        if score >= min_score:
            scored_instruments.append((instrument, score))

    # 스코어 내림차순 정렬
    scored_instruments.sort(key=lambda x: x[1], reverse=True)

    if scored_instruments:
        logger.info(
            f"[매칭 결과] query='{query}' → "
            f"Best: {scored_instruments[0][0].brand} {scored_instruments[0][0].name} "
            f"(score={scored_instruments[0][1]:.2f})"
        )

    return scored_instruments


# =============================================================================
# Search Aggregator Service
# =============================================================================

class SearchAggregatorService:
    """
    네이버 쇼핑 + DB 유저 매물 통합 검색 서비스.
    가격순 정렬로 병합.
    """
    
    def __init__(self):
        self.naver_service = NaverShoppingService()
    
    def _extract_brand_from_query(self, query: str) -> str | None:
        """검색어에서 브랜드 추출 (간단한 휴리스틱)"""
        from .config import CategoryConfig
        
        query_lower = query.lower()
        
        # 알려진 브랜드 목록에서 찾기
        known_brands = CategoryConfig.GUITAR_BRANDS + [
            'boss', 'ibanez', 'jackson', 'charvel', 'schecter', 'suhr',
            'mesa', 'vox', 'marshall', 'orange', 'ampeg', 'tc electronic'
        ]
        
        # 0. 한글 브랜드 매핑 체크
        for kr_name, en_brand in CategoryConfig.BRAND_NAME_MAPPING.items():
            if kr_name in query_lower:
                return en_brand

        for brand in known_brands:
            if brand in query_lower:
                return brand
        
        # 첫 단어를 브랜드로 가정 (2글자 이상)
        first_word = query.split()[0] if query.split() else ""
        if len(first_word) > 2:
            return first_word.lower()
        
        return None
    
    def _detect_category(self, query: str) -> str | None:
        """검색어에서 카테고리 추론"""
        from .config import CategoryConfig
        
        query_lower = query.lower()
        
        if any(kw in query_lower for kw in CategoryConfig.BASS_KEYWORDS):
            return 'BASS'
        if any(kw in query_lower for kw in CategoryConfig.PEDAL_KEYWORDS):
            return 'PEDAL'
        if any(kw in query_lower for kw in CategoryConfig.AMP_KEYWORDS):
            return 'AMP'
        if any(kw in query_lower for kw in CategoryConfig.ACOUSTIC_KEYWORDS):
            return 'ACOUSTIC'
        
        # 기본값은 GUITAR
        return 'GUITAR'
    
    def search(self, query: str, display: int = 20) -> dict[str, Any]:
        """
        통합 검색 수행.
        
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
        # 브랜드/카테고리 추출
        brand = self._extract_brand_from_query(query)
        category = self._detect_category(query)
        
        logger.debug(f"query='{query}', brand={brand}, category={category}")
        
        from .config import CategoryConfig
        query_lower = query.lower().strip()
        query_normalized = normalize_search_term(query)

        # =================================================================
        # 1. DB에서 검색어와 매칭되는 악기(Instrument) 찾기
        # - 스마트 매칭: 정규화 + 스코어링 + 별칭 확장
        # - Unknown 브랜드 제외
        # =================================================================

        # 1-1. 후보 악기 조회 (넓게 검색)
        query_tokens = tokenize_query(query)
        expanded_queries = expand_query_with_aliases(query)  # 별칭 확장
        candidate_filter = models.Q()

        # [NEW] 브랜드 객체가 감지되면 해당 브랜드로 필터링 (우선순위 높음)
        from .models import Brand
        target_brand = None
        
        # 1. 쿼리 전체가 브랜드명과 일치하는지 확인
        try:
             target_brand = Brand.objects.get(name__iexact=brand) if brand else None
        except Brand.DoesNotExist:
             target_brand = None

        # 2. 브랜드 매핑에서 감지된 브랜드가 있으면 DB에서 조회
        if not target_brand and brand:
             target_brand = Brand.objects.filter(slug__iexact=brand).first() or \
                            Brand.objects.filter(name__icontains=brand).first()

        if target_brand:
            logger.info(f"Target Brand Detected: {target_brand.name}")
            # 해당 브랜드의 악기들만 검색 대상에 포함
            candidate_filter &= models.Q(brand_obj=target_brand)
            
            # 브랜드명을 제외한 나머지 쿼리로 모델명 검색 (옵션)
            # 예: "Fender Strat" -> brand="Fender", query="Strat"
            # 하지만 현재 effective_query는 전체 쿼리이므로 그대로 둠
        
        # 정규화된 검색어로 이름/브랜드 검색 (기존 로직 + brand_obj 추가)
        candidate_filter |= models.Q(name__icontains=query_normalized)
        candidate_filter |= models.Q(brand_obj__name__icontains=query_normalized) # Relation 기반 검색
        for token in query_tokens:
            candidate_filter |= models.Q(name__icontains=token)
            candidate_filter |= models.Q(brand__icontains=token)

        # 별칭 확장된 쿼리로도 검색 (예: ds1 → DS-1)
        for expanded in expanded_queries:
            candidate_filter |= models.Q(name__icontains=expanded)
            # 토큰 분리된 별칭도 검색
            for token in expanded.split():
                if len(token) > 1:
                    candidate_filter |= models.Q(name__icontains=token)

        # 원본 검색어로도 검색 (하이픈 포함 케이스)
        candidate_filter |= models.Q(name__icontains=query_lower)
        candidate_filter |= models.Q(brand__icontains=query_lower)

        logger.debug(f"별칭 확장: {query} → {expanded_queries}")

        candidate_instruments = Instrument.objects.filter(
            candidate_filter
        ).exclude(
            brand__iexact='unknown'
        )[:50]  # 스코어링을 위해 넉넉하게

        logger.debug(f"후보 악기 {candidate_instruments.count()}개 조회됨")

        # 1-2. 스코어링 기반 최적 매칭
        scored_matches = find_best_matching_instruments(
            query=query,
            instruments_qs=candidate_instruments,
            min_score=0.3  # 30% 이상 매칭만 포함
        )

        # 상위 10개만 사용
        matching_instruments = [inst for inst, score in scored_matches[:10]]
        best_match = scored_matches[0] if scored_matches else None

        if best_match:
            logger.info(
                f"[DB 매칭] '{query}' → '{best_match[0].brand} {best_match[0].name}' "
                f"(score={best_match[1]:.2f})"
            )

        # =================================================================
        # 2. 네이버 검색 - 최적 매칭 악기 기준으로 쿼리 생성
        # =================================================================
        naver_items = []
        search_query = query

        if best_match and best_match[1] >= 0.5:  # 50% 이상 매칭일 때만 치환
            best_instrument = best_match[0]
            search_query = f"{best_instrument.brand} {best_instrument.name}"
            brand = best_instrument.brand.lower() if best_instrument.brand else brand
            category = best_instrument.category if best_instrument.category else category
            logger.info(f"[쿼리 변환] '{query}' → '{search_query}'")
        else:
            # 한글 브랜드 -> 영어 브랜드 치환
            for kr_name, en_brand in CategoryConfig.BRAND_NAME_MAPPING.items():
                if kr_name in query:
                    search_query = query.replace(kr_name, en_brand)
                    break
        
        logger.info(f"검색 시작: '{search_query}' (브랜드: {brand}, 카테고리: {category})")
        
        naver_items = self.naver_service.search(
            query=search_query, 
            display=display,
            brand=brand,
            category=category,
        )
        
        # =================================================================
        # 3. DB 유저 매물 검색 - 매칭된 악기에 연결된 UserItem 우선
        # =================================================================
        now = timezone.now()

        # Taxonomy 정보 생성 (Brand 객체 기반)
        taxonomy = None
        if target_brand:
            taxonomy = {
                'title': target_brand.name,
                'type': 'brand',
                'brand': target_brand.name,
                'breadcrumbs': ['Home', target_brand.name],
                'description': target_brand.description or f"{target_brand.name} 브랜드의 악기 모음입니다.",
                'logo_url': target_brand.logo_url
            }
        elif best_match and best_match[1] >= 0.8:
             # 모델 매칭 (기존 로직 유지)
             best_inst = best_match[0]
             taxonomy = {
                'title': f"{best_inst.brand_obj.name if best_inst.brand_obj else best_inst.brand.title()} {best_inst.name}",
                'type': 'model',
                'brand': best_inst.brand_obj.name if best_inst.brand_obj else best_inst.brand.title(),
                'breadcrumbs': ['Home', best_inst.brand_obj.name if best_inst.brand_obj else 'Instrument', best_inst.name],
                'description': f"{best_inst.brand_obj.name if best_inst.brand_obj else best_inst.brand}의 {best_inst.name} 모델입니다."
            }

        if matching_instruments:  # 리스트이므로 len > 0 체크
            # 매칭된 악기들의 UserItem 가져오기
            user_items_qs = UserItem.objects.filter(
                is_active=True,
                expired_at__gt=now,
                instrument__in=matching_instruments
            ).select_related('instrument')[:display]
        else:
            # 매칭 악기 없으면 기존 방식 (제목/브랜드 검색)
            user_items_qs = UserItem.objects.filter(
                is_active=True,
                expired_at__gt=now,
            ).filter(
                models.Q(instrument__name__icontains=query) |
                models.Q(instrument__brand__icontains=query) |
                models.Q(title__icontains=query)
            ).select_related('instrument')[:display]
        
        # 유저 매물을 딕셔너리로 변환 + 필터링
        user_items = []
        reference_info = None
        
        for item in user_items_qs:
            title = item.title or str(item.instrument)
            
            # 블랙리스트 필터
            if not check_blacklist(title):
                continue
            
            # 최소 가격 필터 (유저 매물은 가격 제한 없이 노출)
            # if not check_min_price(item.price):
            #     continue
            
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
            })
            
            # 신품 기준가 정보 (첫 번째 매물 기준)
            if reference_info is None and item.instrument.reference_price > 0:
                reference_info = {
                    'name': str(item.instrument),
                    'price': item.instrument.reference_price,
                    'image_url': item.instrument.image_url,
                }
        
        # 악기 마스터에서도 기준가 검색 (유저 매물이 없을 경우)
        # best_match가 있으면 우선 사용
        if reference_info is None and best_match:
            instrument = best_match[0]
            if instrument.reference_price > 0:
                reference_info = {
                    'name': str(instrument),
                    'price': instrument.reference_price,
                    'image_url': instrument.image_url,
                }

        # 그래도 없으면 DB 검색
        if reference_info is None:
            instrument = Instrument.objects.filter(
                models.Q(name__icontains=query) |
                models.Q(brand__icontains=query)
            ).first()

            if instrument and instrument.reference_price > 0:
                reference_info = {
                    'name': str(instrument),
                    'price': instrument.reference_price,
                    'image_url': instrument.image_url,
                }
        
        # 3. 가격순 병합 정렬
        all_items = naver_items + user_items
        all_items.sort(key=lambda x: x.get('lprice', 0))
        
        logger.info(f"✅ 검색 완료: 네이버({len(naver_items)}) + 유저({len(user_items)}) = 총({len(all_items)})")
        
        return {
            'query': query,
            'total_count': len(all_items),
            'reference': reference_info,
            'items': all_items,
            'naver_items': naver_items,
            'user_items': user_items,
            'taxonomy': taxonomy,
        }


# =============================================================================
# AI Description Service
# =============================================================================

class AIDescriptionService:
    """
    AI 악기 설명 생성 서비스.
    할루시네이션 방지를 위한 프롬프트 엔지니어링 적용.
    """
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.api_url = 'https://api.openai.com/v1/chat/completions'
    
    def generate_description(
        self, 
        model_name: str, 
        brand: str, 
        category: str
    ) -> dict[str, str]:
        """
        악기 설명 생성 (할루시네이션 방지 적용).
        
        Returns:
            {'summary': str, 'check_point': str}
        """
        if not self.api_key:
            logger.warning("OpenAI API key not configured")
            return {
                'summary': f'{brand} {model_name} - 믿을 수 있는 선택',
                'check_point': '',
            }
        
        # 할루시네이션 방지 프롬프트
        system_prompt = """너는 악기 전문가이자 팩트 체크에 엄격한 에디터다.
사용자가 요청한 악기에 대한 '한 줄 평'과 '구매 가이드'를 작성하라.

# Rules (Strict)
1. **No Hallucination:** Input Data와 너의 지식 베이스가 100% 일치하는 팩트만 서술하라.
   출시 연도나 세부 스펙이 확실하지 않으면 절대 언급하지 말고 톤/음색 특징 위주로 서술하라.
2. **Tone:** "이 악기는~" 처럼 지루하게 시작하지 마라.
   "따뜻한 배음이 매력적입니다", "입문용으로 최고의 선택입니다" 같이 핵심부터 찌르는 간결한 문체를 써라.
3. **Structure:**
   - [summary]: 20자 이내 임팩트 있는 문구.
   - [check_point]: 중고 거래 시 반드시 확인해야 할 고질병(노브 잡음, 넥 휨 등) 1가지. 모르면 빈 문자열.

JSON 형식으로 { "summary": "...", "check_point": "..." } 만 출력하라."""
        
        user_prompt = f"""# Input Data
- 모델명: {model_name}
- 브랜드: {brand}
- 카테고리: {category}"""
        
        try:
            import json
            response = requests.post(
                self.api_url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': 'gpt-4o-mini',
                    'messages': [
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_prompt},
                    ],
                    'temperature': 0.2,  # 창의성 낮춤 (팩트 위주)
                    'max_tokens': 200,
                },
                timeout=10,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # JSON 파싱
            result = json.loads(content)
            return {
                'summary': result.get('summary', ''),
                'check_point': result.get('check_point', ''),
            }
            
        except Exception as e:
            logger.exception(f"AI description generation error: {e}")
            return {
                'summary': f'{brand} {model_name}',
                'check_point': '',
            }
