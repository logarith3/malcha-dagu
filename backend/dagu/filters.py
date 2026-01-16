"""
Filter utilities for MALCHA-DAGU.
Quality filtering functions for search results.
"""

import logging
import re
from functools import lru_cache
from typing import Optional

from .config import FilterConfig, CategoryConfig, CrawlerConfig

# =============================================================================
# 사용자 매물 필터링
# =============================================================================

def filter_user_item(
    title: str,
    price: int,
    category: str = None,
    min_price: int = None,
) -> bool:
    """
    사용자 매물 필터링.
    네이버 아이템과 동일한 기준 적용.

    Returns:
        True = 통과, False = 탈락
    """
    # [필터 1] 최소 가격 (카테고리별 차등 적용)
    if min_price is None:
        if category == 'effect':
            min_price = CrawlerConfig.MIN_PRICE_PEDAL
        else:
            min_price = CrawlerConfig.MIN_PRICE_KRW

    if not check_min_price(price, min_price):
        return False

    # [필터 2] 블랙리스트
    if not check_blacklist(title):
        return False

    # [필터 3] 카테고리 불일치 (카테고리가 주어진 경우)
    if category and not check_category_mismatch(category, title):
        return False

    return True

logger = logging.getLogger(__name__)


# =============================================================================
# 필터 통계 (디버깅용)
# =============================================================================

class FilterStats:
    """필터 통계 추적 (디버깅용)"""

    def __init__(self):
        self.reset()

    def reset(self):
        self.total = 0
        self.passed = 0
        self.failed_by = {
            'price': 0,
            'blacklist': 0,
            'brand': 0,
            'category': 0,
            'category_fields': 0,
            'product_type': 0,
        }

    def record_pass(self):
        self.total += 1
        self.passed += 1

    def record_fail(self, reason: str):
        self.total += 1
        if reason in self.failed_by:
            self.failed_by[reason] += 1

    def log_summary(self, prefix: str = ""):
        if self.total == 0:
            return
        logger.info(
            f"{prefix}[FilterStats] 총 {self.total}개 중 {self.passed}개 통과 "
            f"({self.passed/self.total*100:.1f}%)"
        )
        for reason, count in self.failed_by.items():
            if count > 0:
                logger.debug(f"  - {reason}: {count}개 탈락")


# 전역 통계 인스턴스 (선택적 사용)
_filter_stats = FilterStats()


# =============================================================================
# 블랙리스트 로딩 (캐싱으로 성능 최적화)
# =============================================================================

@lru_cache(maxsize=1)
def get_blacklist() -> tuple[str, ...]:
    """
    블랙리스트 로드 및 정규화 (캐싱 적용).
    - 소문자 변환
    - 중복 제거
    - 비정상적으로 긴 단어 경고
    - lru_cache로 앱 시작 시 1회만 처리

    Returns:
        tuple[str, ...]: 캐싱을 위해 불변 tuple 반환
    """
    raw_list = getattr(FilterConfig, 'BLACKLIST_KEYWORDS', [])

    if not raw_list:
        logger.warning("BLACKLIST_KEYWORDS가 비어있습니다.")
        return tuple()

    result = set()
    for item in raw_list:
        if item:
            word = str(item).strip().lower()
            # 비정상적으로 긴 단어 감지 (쉼표 누락으로 문자열 결합된 경우)
            if len(word) > 25:
                logger.warning(f"블랙리스트에 비정상적으로 긴 단어 발견: '{word}'")
            result.add(word)

    logger.info(f"블랙리스트 로드 완료: {len(result)}개 키워드")
    return tuple(result)


def clear_blacklist_cache():
    """블랙리스트 캐시 초기화 (설정 변경 시 호출)"""
    get_blacklist.cache_clear()


# =============================================================================
# 필터 함수들
# =============================================================================

def _is_korean(text: str) -> bool:
    """한글 포함 여부 확인"""
    return any('\uac00' <= char <= '\ud7a3' for char in text)


@lru_cache(maxsize=1)
def get_blacklist_exceptions() -> tuple[str, ...]:
    """블랙리스트 예외 키워드 로드 (캐싱)"""
    raw_list = getattr(FilterConfig, 'BLACKLIST_EXCEPTION_KEYWORDS', [])
    return tuple(word.lower() for word in raw_list if word)


def check_blacklist(title: str) -> bool:
    """
    블랙리스트 검사.
    - 예외 키워드(세트, 포함 등)가 있으면 블랙리스트 무시
    - 영어 키워드: 단어 경계 검사 (word boundary)
    - 한글 키워드: 부분문자열 매칭

    Returns:
        True = 통과 (블랙리스트에 없음)
        False = 탈락 (블랙리스트에 있음)
    """
    title_lower = title.lower()

    # 예외 키워드 확인 ("세트", "동시 구매" 등이 있으면 블랙리스트 무시)
    exceptions = get_blacklist_exceptions()
    if any(exc in title_lower for exc in exceptions):
        logger.debug(f"[Blacklist] 예외 통과 (세트/포함): {title[:50]}")
        return True

    current_blacklist = get_blacklist()

    for blackword in current_blacklist:
        if _is_korean(blackword):
            # 한글: 부분문자열 매칭
            if blackword in title_lower:
                logger.debug(f"[Blacklist] 탈락: '{blackword}' - {title[:50]}")
                return False
        else:
            # 영어: 단어 경계 검사 (앞뒤로 알파벳이 아닌 문자)
            pattern = rf'(?<![a-zA-Z]){re.escape(blackword)}(?![a-zA-Z])'
            if re.search(pattern, title_lower):
                logger.debug(f"[Blacklist] 탈락: '{blackword}' - {title[:50]}")
                return False

    return True


def check_min_price(price: int, min_price: int = None) -> bool:
    """
    최소 가격 검사.
    부품/케이스 등 너무 싼 물건 제외.
    
    Returns:
        True = 통과
        False = 탈락
    """
    if min_price is None:
        min_price = CrawlerConfig.MIN_PRICE_KRW
    
    if price < min_price:
        logger.debug(f"[PriceFilter] 탈락: {price:,}원 < {min_price:,}원")
        return False
    
    return True


def check_brand_integrity(target_brand: str, title: str) -> bool:
    """
    브랜드 무결성 검사.
    - 상위 브랜드(Fender) 검색 시 하위 브랜드(Squier) 제외
    - BRAND_HIERARCHY 기반
    
    Returns:
        True = 통과
        False = 탈락
    """
    target_lower = target_brand.lower().strip()
    title_lower = title.lower()
    
    # 브랜드가 없거나 Pending이면 통과
    if not target_lower or 'pending' in target_lower:
        return True
    
    # 핵심 브랜드명 추출 (첫 단어)
    core_brand = target_lower.split()[0] if target_lower else ""
    if not core_brand or len(core_brand) <= 1:
        return True
    
    # 브랜드 하이어라키 검사
    hierarchy = getattr(FilterConfig, 'BRAND_HIERARCHY', {})
    if core_brand in hierarchy:
        for lower_brand in hierarchy[core_brand]:
            if lower_brand in title_lower:
                logger.debug(f"[BrandFilter] 하위 브랜드: '{lower_brand}' - {title[:50]}")
                return False
    
    # 검색 브랜드(또는 한글 별칭)가 제목에 있는지 확인
    aliases = [k for k, v in getattr(CategoryConfig, 'BRAND_NAME_MAPPING', {}).items() if v == core_brand]
    allowed_keywords = [core_brand] + aliases
    
    if any(alias in title_lower for alias in allowed_keywords):
        return True
    
    # 브랜드가 제목에 없으면 탈락
    logger.debug(f"[BrandFilter] 브랜드 불일치: '{core_brand}'(및 별칭 {aliases}) 없음 - {title[:50]}")
    return False


def validate_tokens(model_name: str, title: str) -> bool:
    """
    모델명 토큰 검증.
    - 모델명의 주요 토큰이 제목에 포함되어 있는지 확인
    - 동의어도 확인 (TOKEN_SYNONYMS)
    
    Returns:
        True = 통과 (최소 1개 토큰 매칭)
        False = 탈락
    """
    # Pending 처리
    clean_model = model_name.replace("[Pending] Pending...", "").strip()
    tokens = [t.lower() for t in clean_model.split() if len(t) > 1]
    
    # 토큰이 없으면 통과
    if not tokens:
        return True
    
    title_lower = title.lower()
    synonyms_map = getattr(FilterConfig, 'TOKEN_SYNONYMS', {})
    
    # 모든 토큰 중 하나라도 매칭되면 통과
    for token in tokens:
        # 직접 매칭
        if token in title_lower:
            return True
        # 동의어 매칭
        synonyms = synonyms_map.get(token, [])
        if any(syn in title_lower for syn in synonyms):
            return True
    
    logger.debug(f"토큰 탈락: {tokens} not in '{title[:50]}...'")
    return False


def check_category_mismatch(search_category: str, title: str) -> bool:
    """
    카테고리 불일치 검사.
    - 기타/베이스 검색 시 페달/앰프 제외
    - 페달 검색 시 기타 본체 제외

    Returns:
        True = 통과
        False = 탈락 (불일치)
    """
    title_lower = title.lower()
    search_cat = search_category.lower() if search_category else ""

    # guitar/bass 검색 시
    if search_cat in ['guitar', 'bass']:
        # 페달 제외
        pedal_keywords = getattr(FilterConfig, 'CATEGORY_PEDAL_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in pedal_keywords):
            logger.debug(f"⛔ 카테고리 탈락: 페달 키워드 in '{title[:50]}...'")
            return False

        # 앰프 제외
        amp_keywords = getattr(FilterConfig, 'CATEGORY_AMP_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in amp_keywords):
            logger.debug(f"⛔ 카테고리 탈락: 앰프 키워드 in '{title[:50]}...'")
            return False

        # 어쿠스틱 제외 (일렉 위주)
        acoustic_keywords = getattr(FilterConfig, 'CATEGORY_ACOUSTIC_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in acoustic_keywords):
            logger.debug(f"⛔ 카테고리 탈락: 어쿠스틱 키워드 in '{title[:50]}...'")
            return False

    # acoustic 검색 시
    if search_cat == 'acoustic':
        # 페달/앰프만 제외
        pedal_keywords = getattr(FilterConfig, 'CATEGORY_PEDAL_KEYWORDS', [])
        amp_keywords = getattr(FilterConfig, 'CATEGORY_AMP_KEYWORDS', [])

        if any(kw.lower() in title_lower for kw in pedal_keywords):
            return False
        if any(kw.lower() in title_lower for kw in amp_keywords):
            return False

    # effect(이펙터) 검색 시
    if search_cat == 'effect':
        # "페달", "이펙터" 등이 제목에 있으면 확실히 이펙터이므로 통과
        effect_confirm_keywords = ['pedal', 'effect', 'stomp', '페달', '이펙터', '이펙트']
        if any(kw in title_lower for kw in effect_confirm_keywords):
            return True  # 확실한 이펙터 → 통과

        # 그 외에는 기타 본체 키워드 확인
        instrument_keywords = getattr(FilterConfig, 'CATEGORY_INSTRUMENT_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in instrument_keywords):
            return False

    # amp 검색 시
    if search_cat == 'amp':
        pedal_keywords = getattr(FilterConfig, 'CATEGORY_PEDAL_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in pedal_keywords):
            return False

    return True


def check_category_fields(item: dict) -> bool:
    """
    API 응답의 category3, category4 필드 검사.
    액세서리 카테고리면 제외.
    
    Returns:
        True = 통과 (본품)
        False = 탈락 (액세서리/부품)
    """
    category3 = item.get('category3', '').lower()
    category4 = item.get('category4', '').lower()
    
    blacklist = getattr(FilterConfig, 'ACCESSORY_CATEGORY_BLACKLIST', [])
    
    for cat_kw in blacklist:
        cat_kw_lower = cat_kw.lower()
        if cat_kw_lower in category3 or cat_kw_lower in category4:
            logger.debug(f"⛔ 카테고리 필드 탈락: '{cat_kw}' in category3='{category3}' / category4='{category4}'")
            return False
    
    return True


def check_product_type(item: dict) -> bool:
    """
    productType 필드 검사.
    중고(4), 단종(5), 판매예정(6) 제외.
    
    Returns:
        True = 통과
        False = 탈락
    """
    try:
        product_type = int(item.get('productType', 1))
    except (ValueError, TypeError):
        return True  # 파싱 실패시 통과
    
    valid_types = getattr(FilterConfig, 'VALID_PRODUCT_TYPES', [1, 2, 3])
    
    if product_type not in valid_types:
        logger.debug(f"[ProductType] 탈락: {product_type} (허용: {valid_types}) - {item.get('title', '')[:30]}")
        return False
    
    return True


def build_exclusion_query(query: str) -> str:
    """
    쿼리에 제외 키워드를 추가하여 API 레벨에서 액세서리 필터링.
    예: 'BOSS DS-1' -> 'BOSS DS-1 -어댑터 -케이블 -노브'
    
    Returns:
        제외 키워드가 추가된 쿼리 문자열
    """
    exclusion_keywords = getattr(FilterConfig, 'QUERY_EXCLUSION_KEYWORDS', [])
    
    if not exclusion_keywords:
        return query
    
    # 제외 연산자 추가
    exclusions = ' '.join([f'-{kw}' for kw in exclusion_keywords])
    return f'{query} {exclusions}'


def calculate_match_score(query: str, title: str, image_url: str = None) -> int:
    """
    매칭 스코어 계산.
    - 검색어 토큰 매칭률
    - 이미지 유무
    - 중고/신품 구분
    
    Returns:
        0-100 점수
    """
    score = 50  # 기본 점수
    
    query_tokens = [t.lower() for t in query.split() if len(t) > 1]
    title_lower = title.lower()
    
    if not query_tokens:
        return score
    
    # 토큰 매칭률 (최대 +30점)
    matched = sum(1 for t in query_tokens if t in title_lower)
    match_ratio = matched / len(query_tokens)
    score += int(match_ratio * 30)
    
    # 이미지 있으면 +10점
    if image_url and 'http' in str(image_url):
        score += 10
    
    # 중고품이면 +5점 (중고 거래 사이트이므로)
    if '중고' in title_lower or 'used' in title_lower:
        score += 5
    
    # 정품 키워드 있으면 +5점
    if '정품' in title_lower or 'genuine' in title_lower or 'authentic' in title_lower:
        score += 5
    
    return min(score, 100)


def clean_html_tags(text: str) -> str:
    """HTML 태그 및 특수문자 제거"""
    # HTML 태그 제거
    clean = re.sub(r'<[^>]+>', '', text)
    # &nbsp; 등 HTML 엔티티 제거
    clean = clean.replace('\xa0', ' ')
    # 연속 공백 정리
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def filter_naver_item_with_reason(
    item: dict,
    query: str,
    brand: str = None,
    category: str = None,
    min_price: int = None,
) -> tuple[Optional[dict], str]:
    """
    네이버 쇼핑 아이템 필터링 (탈락 이유 반환).

    Returns:
        (정제된 아이템 또는 None, 탈락 이유)
    """
    title = clean_html_tags(item.get('title', ''))

    try:
        lprice = int(item.get('lprice', 0))
    except (ValueError, TypeError):
        logger.info(f"[Filter] ❌ 가격파싱실패 - {title[:60]}")
        return None, 'price'

    # [필터 1] 최소 가격
    if min_price is None:
        if category == 'effect':
            min_price = CrawlerConfig.MIN_PRICE_PEDAL
        else:
            min_price = CrawlerConfig.MIN_PRICE_KRW

    if not check_min_price(lprice, min_price):
        logger.info(f"[Filter] ❌ 가격미달 {lprice:,}원 < {min_price:,}원 - {title[:60]}")
        return None, 'price'

    # [필터 2] 블랙리스트
    if not check_blacklist(title):
        logger.info(f"[Filter] ❌ 블랙리스트 - {title[:60]}")
        return None, 'blacklist'

    # [필터 3] 브랜드 무결성
    if brand and not check_brand_integrity(brand, title):
        logger.info(f"[Filter] ❌ 브랜드불일치 '{brand}' - {title[:60]}")
        return None, 'brand'

    # [필터 4] 카테고리 불일치
    if category and not check_category_mismatch(category, title):
        cat_info = f"[{item.get('category1', '')}/{item.get('category2', '')}/{item.get('category3', '')}/{item.get('category4', '')}]"
        logger.info(f"[Filter] ❌ 카테고리불일치 '{category}' {cat_info} - {title[:60]}")
        return None, 'category'

    # [필터 5] 카테고리 필드 검사
    if not check_category_fields(item):
        cat_info = f"[{item.get('category1', '')}/{item.get('category2', '')}/{item.get('category3', '')}/{item.get('category4', '')}]"
        logger.info(f"[Filter] ❌ 액세서리카테고리 {cat_info} - {title[:60]}")
        return None, 'category_fields'

    # [필터 6] 상품 타입 검사
    if not check_product_type(item):
        logger.info(f"[Filter] ❌ 상품타입(중고/단종) - {title[:60]}")
        return None, 'product_type'

    # 모든 필터 통과
    image_url = item.get('image', '')
    result = {
        'title': title,
        'link': item.get('link', ''),
        'image': image_url,
        'lprice': lprice,
        'hprice': int(item.get('hprice', 0) or 0),
        'mallName': item.get('mallName', ''),
        'productId': item.get('productId', ''),
        'productType': item.get('productType', 0),
        'brand': item.get('brand', ''),
        'maker': item.get('maker', ''),
        'category1': item.get('category1', ''),
        'category2': item.get('category2', ''),
        'category3': item.get('category3', ''),
        'category4': item.get('category4', ''),
        'source': 'naver',
        'score': calculate_match_score(query, title, image_url),
        'is_used': '중고' in title.lower() or item.get('productType') in [4, 5, 6],
    }
    return result, 'passed'


def filter_naver_item(
    item: dict,
    query: str,
    brand: str = None,
    category: str = None,
    min_price: int = None,
) -> Optional[dict]:
    """
    네이버 쇼핑 아이템 필터링.
    모든 필터를 통과하면 정제된 아이템 반환, 탈락하면 None 반환.
    """
    result, _ = filter_naver_item_with_reason(item, query, brand, category, min_price)
    return result
