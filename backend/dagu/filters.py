"""
Filter utilities for MALCHA-DAGU.
Quality filtering functions for search results.
"""

import logging
import re
from typing import Optional

from .config import FilterConfig, CategoryConfig, CrawlerConfig

logger = logging.getLogger(__name__)


# =============================================================================
# 블랙리스트 로딩 (앱 시작 시 1회)
# =============================================================================

def get_blacklist() -> list[str]:
    """
    블랙리스트 로드 및 정규화.
    - 소문자 변환
    - 중복 제거
    - 비정상적으로 긴 단어 경고
    """
    raw_list = getattr(FilterConfig, 'BLACKLIST_KEYWORDS', [])
    
    if not raw_list:
        logger.warning("⚠️ BLACKLIST_KEYWORDS가 비어있습니다.")
        return []
    
    result = []
    for item in raw_list:
        if item:
            word = str(item).strip().lower()
            # 비정상적으로 긴 단어 감지 (쉼표 누락으로 문자열 결합된 경우)
            if len(word) > 25:
                logger.warning(f"⚠️ 블랙리스트에 비정상적으로 긴 단어 발견: '{word}'")
            result.append(word)
    
    # 중복 제거
    result = list(set(result))
    logger.info(f"✅ 블랙리스트 로드 완료: {len(result)}개 키워드")
    return result


# 앱 시작 시 블랙리스트 로드
GLOBAL_BLACKLIST = get_blacklist()


# =============================================================================
# 필터 함수들
# =============================================================================

def check_blacklist(title: str) -> bool:
    """
    블랙리스트 검사.
    
    Returns:
        True = 통과 (블랙리스트에 없음)
        False = 탈락 (블랙리스트에 있음)
    """
    title_lower = title.lower()
    
    for blackword in GLOBAL_BLACKLIST:
        if blackword in title_lower:
            logger.debug(f"⛔ 블랙리스트 탈락: '{blackword}' in '{title[:50]}...'")
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
        logger.debug(f"⛔ 가격 탈락: {price:,}원 < {min_price:,}원")
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
                logger.debug(f"⛔ 브랜드 탈락: '{lower_brand}' (하위 브랜드) in '{title[:50]}...'")
                return False
    
    # 검색 브랜드가 제목에 있는지 확인
    if core_brand in title_lower:
        return True
    
    # 브랜드가 제목에 없으면 탈락
    logger.debug(f"⛔ 브랜드 탈락: '{core_brand}' not in '{title[:50]}...'")
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
    
    logger.debug(f"⛔ 토큰 탈락: {tokens} not in '{title[:50]}...'")
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
    search_cat = search_category.upper() if search_category else ""
    
    # GUITAR/BASS 검색 시
    if search_cat in ['GUITAR', 'BASS']:
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
    
    # ACOUSTIC 검색 시
    if search_cat == 'ACOUSTIC':
        # 페달/앰프만 제외
        pedal_keywords = getattr(FilterConfig, 'CATEGORY_PEDAL_KEYWORDS', [])
        amp_keywords = getattr(FilterConfig, 'CATEGORY_AMP_KEYWORDS', [])
        
        if any(kw.lower() in title_lower for kw in pedal_keywords):
            return False
        if any(kw.lower() in title_lower for kw in amp_keywords):
            return False
    
    # PEDAL 검색 시
    if search_cat == 'PEDAL':
        instrument_keywords = getattr(FilterConfig, 'CATEGORY_INSTRUMENT_KEYWORDS', [])
        if any(kw.lower() in title_lower for kw in instrument_keywords):
            return False
    
    # AMP 검색 시
    if search_cat == 'AMP':
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
        logger.debug(f"⛔ productType 탈락: {product_type} (허용: {valid_types})")
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
    title = clean_html_tags(item.get('title', ''))
    
    try:
        lprice = int(item.get('lprice', 0))
    except (ValueError, TypeError):
        return None
    
    # [필터 1] 최소 가격
    if not check_min_price(lprice, min_price):
        return None
    
    # [필터 2] 블랙리스트
    if not check_blacklist(title):
        return None
    
    # [필터 3] 브랜드 무결성 (브랜드가 주어진 경우)
    if brand and not check_brand_integrity(brand, title):
        return None
    
    # [필터 4] 카테고리 불일치 (카테고리가 주어진 경우)
    if category and not check_category_mismatch(category, title):
        return None
    
    # [필터 5] 카테고리 필드 검사 (category3, category4)
    if not check_category_fields(item):
        return None
    
    # [필터 6] 상품 타입 검사 (중고/단종/판매예정 제외)
    if not check_product_type(item):
        return None
    
    # 모든 필터 통과 - 정제된 아이템 반환
    image_url = item.get('image', '')
    
    return {
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
