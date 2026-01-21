"""
Filter utilities for MALCHA-DAGU.
Quality filtering functions for search results.
"""

import logging
import re
from functools import lru_cache
from typing import Optional

from .config import FilterConfig, CategoryConfig, CrawlerConfig

logger = logging.getLogger(__name__)

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
    유저가 직접 등록한 매물이므로 가격 필터는 적용하지 않음.

    Returns:
        True = 통과, False = 탈락
    """
    # [필터 1] 블랙리스트

    return True


def filter_user_item_by_brand(
    query: str,
    item_brand: str,
) -> bool:
    """
    사용자 매물 브랜드 필터링.
    
    검색어에 명시된 브랜드와 매물의 악기 브랜드가 다르면 필터링.
    예: 'Squier Strat' 검색 시, instrument.brand가 'Fender'인 매물은 제외.
    
    Args:
        query: 사용자 검색어
        item_brand: 매물에 연결된 악기의 브랜드 (instrument.brand)
        
    Returns:
        True = 통과, False = 탈락
    """
    from .services.utils import extract_brand, is_known_brand
    
    # 1. 검색어에서 브랜드 추출
    query_brand = extract_brand(query)
    
    # 2. 검색어에 명시적 브랜드가 없으면 필터 안 함 (통과)
    if not query_brand or not is_known_brand(query_brand):
        return True
    
    # 3. 매물에 브랜드가 없으면 필터 안 함 (통과)
    if not item_brand:
        return True
    
    # 4. 브랜드 일치 여부 확인 (대소문자 무시)
    query_brand_lower = query_brand.lower()
    item_brand_lower = item_brand.lower()
    
    # 브랜드가 일치하면 통과
    if query_brand_lower in item_brand_lower or item_brand_lower in query_brand_lower:
        return True
    
    # 브랜드가 다르면 탈락
    logger.debug(f"[Brand Filter] 탈락: query_brand='{query_brand}', item_brand='{item_brand}'")
    return False


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
    블랙리스트 로드 및 정규화 (최적화 버전).
    - 중복 제거 및 소문자 정규화
    - 긴 단어 순서로 정렬 (필터링 정확도 향상)
    - 로깅 레벨 최적화 및 비정상 데이터 필터링
    """
    # 1. 설정값 가져오기 (없으면 빈 리스트)
    raw_list = getattr(FilterConfig, 'BLACKLIST_KEYWORDS', [])

    if not raw_list:
        logger.warning("⚠️ BLACKLIST_KEYWORDS가 설정되어 있지 않거나 비어있습니다.")
        return tuple()

    # 2. 데이터 정제 (Set Comprehension으로 속도 향상)
    # 문자열인 것만 골라내서 strip, lower 처리
    processed_set = {
        str(item).strip().lower()
        for item in raw_list
        if item and len(str(item).strip()) > 0
    }

    result_list = []
    for word in processed_set:
        # 비정상적으로 긴 단어 경고 (설정 파일 오타 감지)
        if len(word) > 25:
            logger.warning(f"🚩 블랙리스트에 비정상적으로 긴 단어 발견 (오타 확인 권장): '{word}'")

        # [기존 개선] 루프 안의 logger.error(word)는 서버 부하를 주므로 제거하거나 debug로 변경
        # logger.debug(f"Blacklist word loaded: {word}")
        result_list.append(word)

    # 3. 핵심 개선: 단어 길이에 따라 내림차순 정렬
    # '하드케이스'가 '케이스'보다 앞에 와야 정확한 매칭이 가능합니다.
    result_list.sort(key=len, reverse=True)

    logger.info(f"✅ 블랙리스트 로드 완료: {len(result_list)}개 키워드")
    return tuple(result_list)

def clear_blacklist_cache():
    """블랙리스트 캐시 초기화 (설정 변경 시 호출)"""
    get_blacklist.cache_clear()


# =============================================================================
# 필터 함수들
# =============================================================================

def _is_korean(text: str) -> bool:
    """한글 포함 여부 확인"""
    return any('\uac00' <= char <= '\ud7a3' for char in text)


def check_blacklist(title: str) -> bool:
    """
    블랙리스트 검사.
    - 블랙리스트 키워드가 있으면 필터링
    - "세트", "포함" 등 예외 키워드는 더 이상 사용하지 않음

    Returns:
        True = 통과 (블랙리스트에 없음)
        False = 탈락 (블랙리스트에 있음)
    """
    title_lower = title.lower()
    current_blacklist = get_blacklist()

    for blackword in current_blacklist:
        if _is_korean(blackword):
            # 한글: 부분문자열 매칭
            if blackword in title_lower:
                logger.debug(f"[Blacklist] 탈락: '{blackword}' - {title[:50]}")
                return False
        else:
            # 영어: 단어 경계 검사
            pattern = rf'(?<![a-zA-Z0-9]){re.escape(blackword)}(?![a-zA-Z0-9])'
            if re.search(pattern, title_lower):
                logger.debug(f"[Blacklist] 탈락: '{blackword}' - {title[:50]}")
                return False

    return True


def check_min_price(price: int, category: str, reference_price: int, min_price: int = None) -> bool:
    """
    최소 가격 검사.
    부품/케이스 등 너무 싼 물건 제외.
    
    Returns:
        True = 통과
        False = 탈락
    """

    if min_price is None:
        min_price = calculate_min_price(category, reference_price)
    if price < min_price:
        return False
    
    return True


def check_brand_integrity(target_brand: str, title: str, category: str = None) -> bool:
    """
    카테고리별 브랜드 무결성 검사.
    - guitar, bass: 상위 브랜드 검색 시 하위 브랜드(Hierarchy) 엄격 제외
    - 카테고리 불확실(None): 하이어라키 검사 건너뜀 (오탐 방지)
    - 기타 카테고리: 브랜드 존재 여부 및 단어 경계만 검사 (유연함 유지)
    """
    if not target_brand or 'pending' in target_brand.lower():
        return True

    target_lower = target_brand.lower().strip()
    title_lower = title.lower()
    
    # 1. [기타/베이스 전용] 브랜드 하이어라키 검사
    # 카테고리가 확실할 때만 적용 (None = 확신 없음 → 하이어라키 검사 스킵)
    if category is not None and category in ['guitar', 'bass']:
        hierarchy = getattr(FilterConfig, 'BRAND_HIERARCHY', {})
        lower_brands = hierarchy.get(target_lower, [])

        for lb in lower_brands:
            if lb.lower() in title_lower:
                logger.debug(f"⛔ [BrandFilter] 하위 브랜드 제외 ({category}): '{lb}' in '{title[:50]}'")
                return False

    # 2. [공통] 허용 키워드 리스트업 (본래 이름 + 한/영 별칭)
    # BRAND_NAME_MAPPING에서 이 브랜드에 해당하는 별칭을 모두 가져옴
    aliases = [k for k, v in getattr(CategoryConfig, 'BRAND_NAME_MAPPING', {}).items() if v == target_lower]
    allowed_keywords = [target_lower] + aliases

    # 3. [공통] 정규표현식을 이용한 브랜드 존재 확인 (오탐 방지)
    # 제목에 검색한 브랜드나 그 별칭이 '단어'로서 존재하는지 확인합니다.
    for kw in allowed_keywords:
        # 영문/숫자 경계를 포함한 패턴 (예: 'ESP'가 'Response'에 걸리지 않도록)
        pattern = rf'(?<![a-zA-Z0-9]){re.escape(kw)}(?![a-zA-Z0-9])'
        if re.search(pattern, title_lower):
            return True

    logger.debug(f"❌ [BrandFilter] 브랜드 불일치: '{target_lower}' 없음 - {title[:50]}")
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


def _contains_keywords(title_lower: str, config_key: str) -> bool:
    """
    config에서 키워드 목록을 가져와 제목에 '독립된 단어'로 포함되어 있는지 확인.
    정규표현식을 사용하여 부분 일치로 인한 오탐을 방지합니다.
    """
    keywords = getattr(FilterConfig, config_key, [])

    for kw in keywords:
        kw_clean = kw.lower().strip()
        if not kw_clean:
            continue

        # 1. 한글이 포함된 경우: 기존처럼 부분 일치 허용 (띄어쓰기 무관)
        if any('\uac00' <= char <= '\ud7a3' for char in kw_clean):
            if kw_clean in title_lower:
                return True
        else:
            # 2. 영문/숫자만 있는 경우: 단어 경계 검사 적용
            # (?<![a-zA-Z0-9]) : 앞뒤에 영문이나 숫자가 붙어있지 않아야 함
            pattern = rf'(?<![a-zA-Z0-9]){re.escape(kw_clean)}(?![a-zA-Z0-9])'
            if re.search(pattern, title_lower):
                return True

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
        if _contains_keywords(title_lower, 'CATEGORY_PEDAL_KEYWORDS'):
            logger.debug(f"⛔ 카테고리 탈락: 페달 키워드 in '{title[:50]}...'")
            return False
        if _contains_keywords(title_lower, 'CATEGORY_AMP_KEYWORDS'):
            logger.debug(f"⛔ 카테고리 탈락: 앰프 키워드 in '{title[:50]}...'")
            return False
        if _contains_keywords(title_lower, 'CATEGORY_ACOUSTIC_KEYWORDS'):
            logger.debug(f"⛔ 카테고리 탈락: 어쿠스틱 키워드 in '{title[:50]}...'")
            return False

    # acoustic 검색 시
    if search_cat == 'acoustic':
        if _contains_keywords(title_lower, 'CATEGORY_PEDAL_KEYWORDS'):
            return False
        if _contains_keywords(title_lower, 'CATEGORY_AMP_KEYWORDS'):
            return False

    # effect(이펙터) 검색 시
    if search_cat == 'effect':
        # "페달", "이펙터" 등이 제목에 있으면 확실히 이펙터이므로 통과
        if _contains_keywords(title_lower, 'EFFECT_CONFIRM_KEYWORDS'):
            return True
        # 그 외에는 기타 본체 키워드 확인
        if _contains_keywords(title_lower, 'CATEGORY_INSTRUMENT_KEYWORDS'):
            return False

    # amp 검색 시
    if search_cat == 'amp':
        if _contains_keywords(title_lower, 'CATEGORY_PEDAL_KEYWORDS'):
            return False

    # mic(마이크) 검색 시
    if search_cat == 'mic':
        # "마이크", "마이크로폰" 등이 제목에 있으면 확실히 마이크이므로 통과
        if _contains_keywords(title_lower, 'MIC_CONFIRM_KEYWORDS'):
            return True
        # 그 외에는 기타/앰프/이펙터 키워드 확인
        if _contains_keywords(title_lower, 'CATEGORY_MIC_EXCLUDE_KEYWORDS'):
            return False

    return True


def check_category_fields(item: dict) -> bool:
    # 1. 필드 값 확보 (소문자화 및 None 방지)
    # 네이버 API는 category1~4까지 제공하므로 3, 4를 중점적으로 봅니다.
    cat3 = str(item.get('category3', '')).lower()
    cat4 = str(item.get('category4', '')).lower()

    # 카테고리 정보가 아예 없으면 일단 통과 (제목 필터에서 걸러질 것을 기대)
    if not cat3 and not cat4:
        return True

    # 2. 블랙리스트 로드 (미리 소문자화된 리스트를 가져온다고 가정)
    # 예: ['용품', '케이스', '소모품', '부품', '피크', '스트랩', '스탠드']
    blacklist = getattr(FilterConfig, 'ACCESSORY_CATEGORY_BLACKLIST', [])

    for kw in blacklist:
        kw_lower = kw.lower()
        # 3. 부분 일치 검사
        if kw_lower in cat3 or kw_lower in cat4:
            logger.debug(f"⛔ [CategoryFieldFilter] 탈락: '{kw_lower}' 발견 "
                         f"(cat3: '{cat3}', cat4: '{cat4}')")
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
    - 검색어 토큰 매칭률 (핵심)
    - 이미지 유무, 중고 여부, 정품 여부
    
    Returns:
        0-100 점수
    """
    score = 0
    
    # 중복 제거 (점수 뻥튀기 방지)
    query_tokens = list(set([t.lower() for t in query.split() if len(t) > 1]))
    title_lower = title.lower()
    
    if not query_tokens:
        return 50  # 쿼리 없으면 기본 점수
    
    # 토큰 매칭률 (최대 70점)
    matched = sum(1 for t in query_tokens if t in title_lower)
    match_ratio = matched / len(query_tokens)
    
    score += int(match_ratio * 70)
    
    # 모든 토큰이 다 포함되면 보너스 (+15점)
    if match_ratio == 1.0:
        score += 15
    
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


def calculate_min_price(category: str = None, reference_price: int = None) -> int:
    """
    최소 가격 계산.
    - reference_price가 있으면: 신품가의 MIN_PRICE_RATIO (10%)
    - 없으면: 카테고리별 기본값 사용
    """
    # 신품 기준가가 있으면 비율로 계산
    if reference_price and reference_price > 0:
        calculated = int(reference_price * CrawlerConfig.MIN_PRICE_RATIO)
        # 최소 1만원은 보장
        return max(calculated, 10000)

    # 폴백: 카테고리별 기본값
    if category == 'effect':
        return CrawlerConfig.MIN_PRICE_PEDAL
    elif category == 'mic':
        return CrawlerConfig.MIN_PRICE_MIC
    else:
        return CrawlerConfig.MIN_PRICE_KRW


def calculate_dynamic_min_price(prices: list[int], threshold_ratio: float = 0.15) -> int:
    """
    동적 가격 필터링 (DB에 없는 악기용).
    가격 분포의 중간값(Median)을 구하고, 그 중간값의 threshold_ratio 이하인 상품은 제외.

    Args:
        prices: 검색 결과 가격 리스트
        threshold_ratio: 중간값 대비 최소가 비율 (기본 15%)

    Returns:
        동적으로 계산된 최소 가격
    """
    if not prices or len(prices) < 5:
        return 0  # 데이터 부족 시 필터링 안 함

    sorted_prices = sorted(prices)
    n = len(sorted_prices)

    # 중간값 계산
    if n % 2 == 0:
        median = (sorted_prices[n // 2 - 1] + sorted_prices[n // 2]) // 2
    else:
        median = sorted_prices[n // 2]

    # 중간값의 threshold_ratio를 최소가로 설정
    dynamic_min = int(median * threshold_ratio)

    # 최소 1만원 보장
    dynamic_min = max(dynamic_min, 10000)

    logger.info(f"[동적필터] 가격분포: {len(prices)}개, 중간값: {median:,}원 → 최소가: {dynamic_min:,}원")

    return dynamic_min


def filter_naver_item_with_reason(
    item: dict,
    query: str,
    brand: str = None,
    category: str = None,
    min_price: int = None,
    reference_price: int = None,
) -> tuple[Optional[dict], str]:
    """
    네이버 쇼핑 아이템 필터링 (탈락 이유 반환).

    Args:
        reference_price: 신품 기준가 (있으면 이 값의 10%를 최소가로 사용)

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

    if not check_min_price(lprice,category,reference_price, min_price):
        return None, 'price'

    # [필터 5] 카테고리 필드 검사
    if not check_category_fields(item):
        cat_info = f"[{item.get('category1', '')}/{item.get('category2', '')}/{item.get('category3', '')}/{item.get('category4', '')}]"
        logger.info(f"[Filter] ❌ 액세서리카테고리 {cat_info} - {title[:60]}")
        return None, 'category_fields'


    # [필터 2] 블랙리스트
    if not check_blacklist(title):
        logger.info(f"[Filter] ❌ 블랙리스트 - {title[:60]}")
        return None, 'blacklist'


    # [필터 4] 카테고리 불일치
    if category and not check_category_mismatch(category, title):
        cat_info = f"[{item.get('category1', '')}/{item.get('category2', '')}/{item.get('category3', '')}/{item.get('category4', '')}]"
        logger.info(f"[Filter] ❌ 카테고리불일치 '{category}' {cat_info} - {title[:60]}")
        return None, 'category'

    # [필터 3] 브랜드 무결성
    if brand and not check_brand_integrity(brand, title, category):
        logger.info(f"[Filter] ❌ 브랜드불일치 '{brand}' - {title[:60]}")
        return None, 'brand'




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
    reference_price: int = None,
) -> Optional[dict]:
    """
    네이버 쇼핑 아이템 필터링.
    모든 필터를 통과하면 정제된 아이템 반환, 탈락하면 None 반환.
    """
    result, _ = filter_naver_item_with_reason(item, query, brand, category, min_price, reference_price)
    return result
