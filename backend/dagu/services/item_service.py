"""
Item Service
매물(UserItem) 관련 비즈니스 로직 처리
"""
import logging
from urllib.parse import urlparse
from django.db import models
from ..models import Instrument, UserItem
from .utils import (
    normalize_brand, tokenize_query, expand_query_with_aliases,
    find_best_matching_instruments, extract_brand
)

logger = logging.getLogger(__name__)

# 허용된 중고거래 사이트 도메인
ALLOWED_DOMAINS = [
    'mule.co.kr',           # 뮬
    'bunjang.co.kr',        # 번개장터
    'daangn.com',           # 당근마켓
    'danggeun.com',         # 당근마켓 (구 도메인)
    'cafe.naver.com',       # 중고나라 (네이버 카페)
    'joongna.com',          # 중고나라
    'secondhand.co.kr',     # 세컨핸드
]

def is_allowed_link(link: str) -> bool:
    """
    허용된 도메인 및 프로토콜 확인 (XSS/Open Redirect 방지)
    """
    try:
        parsed = urlparse(link.lower())
        # 프로토콜 검증: http/https만 허용
        if parsed.scheme not in ['http', 'https']:
            logger.warning(f"Invalid protocol detected: {parsed.scheme}")
            return False
        
        # 도메인 검증
        domain = parsed.netloc
        if not domain:
            return False
        
        return any(allowed in domain for allowed in ALLOWED_DOMAINS)
    except Exception as e:
        logger.warning(f"URL parsing error: {e}")
        return False


def resolve_and_standardize_item(title: str, instrument_id=None) -> tuple[Instrument | None, str]:
    """
    매물 등록 시 악기를 결정하고 제목을 표준화합니다.
    
    Args:
        title: 매물 제목
        instrument_id: Instrument 객체, ID (int/str), 또는 None
    
    Returns:
        (matched_instrument, standardized_title) 튜플
    """
    instrument = None

    # [Debug] 매물 등록 시도 정보 로깅
    detected_brand = extract_brand(title)
    logger.error(f"========== [매물등록 시도] Title: '{title}' | Detected Brand: '{detected_brand}' ==========")

    # 1. instrument_id 처리 (객체 또는 ID)
    if instrument_id:
        # 이미 Instrument 객체인 경우
        if isinstance(instrument_id, Instrument):
            instrument = instrument_id
            logger.info(f"[매물 등록] instrument 객체 직접 사용: {instrument}")
        else:
            # ID로 조회
            instrument = Instrument.objects.filter(id=instrument_id).first()
            if instrument:
                logger.info(f"[매물 등록] instrument ID 사용: {instrument}")

    # 2. ID가 없으면 title로 자동 매칭
    if not instrument and title:
        search_query = normalize_brand(title)
        query_tokens = tokenize_query(search_query)
        expanded_queries = expand_query_with_aliases(search_query)

        candidate_filter = models.Q()
        for token in query_tokens:
            if len(token) >= 2:
                candidate_filter |= models.Q(name__icontains=token)
                candidate_filter |= models.Q(brand__icontains=token)
        for expanded in expanded_queries:
            candidate_filter |= models.Q(name__icontains=expanded)

        candidates = Instrument.objects.filter(candidate_filter).exclude(
            brand__iexact='unknown'
        )[:30]

        if candidates.exists():
            scored_matches = find_best_matching_instruments(
                query=title,
                instruments_qs=candidates,
                min_score=0.4,
            )
            if scored_matches:
                instrument = scored_matches[0][0]
                logger.info(
                    f"[매물 등록] title 매칭: '{title}' -> "
                    f"'{instrument.brand} {instrument.name}' (score={scored_matches[0][1]:.2f})"
                )

    # 3. 제목 표준화 (Brand + Name)
    final_title = title
    if instrument:
        # 브랜드가 이름에 포함되지 않은 경우에만 병합 (중복 방지)
        if instrument.brand and instrument.brand.lower() not in instrument.name.lower():
            final_title = f"{instrument.brand} {instrument.name}"
        else:
            final_title = instrument.name
        
        if final_title != title:
            logger.info(f"[매물 등록] 제목 표준화: '{title}' -> '{final_title}'")

    return instrument, final_title
