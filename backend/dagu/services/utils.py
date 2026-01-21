"""
Search utility functions for MALCHA-DAGU.

Provides search term normalization, alias expansion, and instrument matching.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet
    from ..models import Instrument

logger = logging.getLogger(__name__)


def mask_sensitive_data(text: str) -> str:
    """
    문자열 내 개인정보(전화번호, 이메일) 마스킹
    """
    if not text:
        return text
    
    # 전화번호 (010-1234-5678, 01012345678)
    phone_pattern = r'01[016789]-?\d{3,4}-?\d{4}'
    text = re.sub(phone_pattern, '[PHONE]', text)
    
    # 이메일
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    text = re.sub(email_pattern, '[EMAIL]', text)
    
    return text


# =============================================================================
# Cached Config Accessors (성능 최적화)
# =============================================================================

@lru_cache(maxsize=1)
def _get_model_aliases() -> dict[str, str]:
    """MODEL_ALIASES 캐시 로드"""
    from ..config import CategoryConfig
    return getattr(CategoryConfig, 'MODEL_ALIASES', {})


@lru_cache(maxsize=1)
def _get_brand_mapping() -> dict[str, str]:
    """BRAND_NAME_MAPPING 캐시 로드"""
    from ..config import CategoryConfig
    return getattr(CategoryConfig, 'BRAND_NAME_MAPPING', {})


@lru_cache(maxsize=1)
def _get_guitar_brands() -> list[str]:
    """GUITAR_BRANDS 캐시 로드"""
    from ..config import CategoryConfig
    return getattr(CategoryConfig, 'GUITAR_BRANDS', [])


def clear_config_cache() -> None:
    """설정 캐시 초기화 (설정 변경 시 호출)"""
    _get_model_aliases.cache_clear()
    _get_brand_mapping.cache_clear()
    _get_guitar_brands.cache_clear()
    _get_known_brands.cache_clear()
    _get_category_keywords.cache_clear()


# =============================================================================
# Brand Normalization (통합 브랜드 처리)
# =============================================================================

@lru_cache(maxsize=1)
def _get_known_brands() -> list[str]:
    """KNOWN_BRANDS 캐시 로드"""
    from ..config import CategoryConfig
    return getattr(CategoryConfig, 'KNOWN_BRANDS', [])


def normalize_brand(query: str) -> str:
    """
    검색어에서 한글 브랜드를 영문으로 변환.

    Examples:
        >>> normalize_brand("펜더 스트랫")
        'fender 스트랫'
        >>> normalize_brand("boss ds-1")
        'boss ds-1'

    Args:
        query: 검색어

    Returns:
        영문 브랜드로 치환된 검색어
    """
    brand_mapping = _get_brand_mapping()
    result = query

    for kr_name, en_brand in brand_mapping.items():
        if kr_name in query:
            result = query.replace(kr_name, en_brand)
            logger.debug(f"[Brand] 정규화: '{query}' -> '{result}'")
            break

    return result


def extract_brand(query: str) -> str | None:
    """
    검색어에서 브랜드 추출.

    Examples:
        >>> extract_brand("펜더 스트랫")
        'fender'
        >>> extract_brand("BOSS DS-1")
        'boss'

    Args:
        query: 검색어

    Returns:
        추출된 브랜드 (소문자) 또는 None
    """
    query_lower = query.lower()

    # 한글 브랜드 매핑 체크
    brand_mapping = _get_brand_mapping()
    for kr_name, en_brand in brand_mapping.items():
        if kr_name in query_lower:
            return en_brand

    # 알려진 브랜드 목록에서 찾기
    guitar_brands = _get_guitar_brands()
    known_brands = _get_known_brands()
    all_brands = guitar_brands + known_brands

    for brand in all_brands:
        if brand in query_lower:
            return brand

    # 첫 단어를 브랜드로 가정 (2글자 이상)
    # 단, 모델명이나 카테고리 키워드인 경우 제외 (예: "sm57", "strat")
    words = query.split()
    if words and len(words[0]) > 2:
        candidate = words[0].lower()
        
        # 1. 모델 별칭 체크
        aliases = _get_model_aliases()
        if candidate in aliases:
            return None
            
        # 2. 카테고리 키워드 체크 (예: guitar, bass, sm57 등)
        category_keywords = _get_category_keywords()
        for kw_list in category_keywords.values():
            if candidate in kw_list:
                return None
        
        # 3. 모델명 밸류 체크 (Alias의 target 값)
        if candidate in [v.lower() for v in aliases.values()]:
            return None

        return candidate


def is_known_brand(brand_name: str) -> bool:
    """
    해당 브랜드명이 알려진 브랜드 목록(설정값)에 포함되는지 확인.
    검색 필터링 시 잘못된 브랜드 추정으로 인한 결과 누락 방지용.
    """
    if not brand_name:
        return False
        
    brand_lower = brand_name.lower()
    
    # 1. 기타 브랜드 목록
    if brand_lower in [b.lower() for b in _get_guitar_brands()]:
        return True
        
    # 2. 추가 알려진 브랜드 목록
    if brand_lower in [b.lower() for b in _get_known_brands()]:
        return True
        
    # 3. 매핑된 영문 브랜드 목록
    if brand_lower in [v.lower() for v in _get_brand_mapping().values()]:
        return True
        
    return False

    return None


# =============================================================================
# Category Detection
# =============================================================================

@lru_cache(maxsize=1)
def _get_category_keywords() -> dict[str, list[str]]:
    """카테고리별 키워드 캐시 로드"""
    from ..config import CategoryConfig
    return {
        'bass': getattr(CategoryConfig, 'BASS_KEYWORDS', []),
        'effect': getattr(CategoryConfig, 'PEDAL_KEYWORDS', []),
        'amp': getattr(CategoryConfig, 'AMP_KEYWORDS', []),
        'acoustic': getattr(CategoryConfig, 'ACOUSTIC_KEYWORDS', []),
        'mic': getattr(CategoryConfig, 'MIC_KEYWORDS', []),
    }


def detect_category(text: str) -> str:
    """
    텍스트에서 악기 카테고리 추론.

    Examples:
        >>> detect_category("BOSS DS-1 디스토션 페달")
        'effect'
        >>> detect_category("Fender Jazz Bass")
        'bass'
        >>> detect_category("Gibson Les Paul")
        'guitar'

    Args:
        text: 제목 또는 검색어

    Returns:
        카테고리 ('guitar', 'bass', 'effect', 'amp', 'acoustic')
    """
    text_lower = text.lower()
    keywords = _get_category_keywords()

    for category, kw_list in keywords.items():
        if any(kw in text_lower for kw in kw_list):
            return category

    return 'guitar'  # 기본값


# =============================================================================
# Search Term Normalization
# =============================================================================

def normalize_search_term(term: str) -> str:
    """
    검색어 정규화: 대소문자, 하이픈, 공백 통일.

    Examples:
        >>> normalize_search_term("DS-1")
        'ds1'
        >>> normalize_search_term("ds 1")
        'ds1'
        >>> normalize_search_term("Les Paul")
        'lespaul'

    Args:
        term: 원본 검색어

    Returns:
        정규화된 검색어 (소문자, 특수문자 제거)
    """
    if not term:
        return ""

    result = term.lower().strip()
    # 하이픈, 언더스코어, 공백 제거
    result = re.sub(r'[-_\s]+', '', result)
    return result





def tokenize_query(query: str) -> list[str]:
    """
    검색어를 토큰으로 분리.

    Examples:
        >>> tokenize_query("boss ds-1")
        ['boss', 'ds-1', 'ds1']
        >>> tokenize_query("Fender Strat")
        ['fender', 'strat']

    Args:
        query: 검색어

    Returns:
        토큰 리스트 (원본 + 정규화된 버전)
    """
    tokens = []
    words = query.lower().strip().split()

    for word in words:
        tokens.append(word)
        # 하이픈 제거 버전도 추가 (ds-1 -> ds1)
        normalized = re.sub(r'[-_]+', '', word)
        if normalized != word:
            tokens.append(normalized)

    return list(set(tokens))


def expand_query_with_aliases(query: str) -> list[str]:
    """
    검색어를 별칭 매핑으로 확장.

    Examples:
        >>> expand_query_with_aliases("ds1")
        ['ds1', 'DS-1']
        >>> expand_query_with_aliases("strat")
        ['strat', 'Stratocaster']

    Args:
        query: 검색어

    Returns:
        확장된 검색어 리스트 (원본 + 별칭 매핑된 정식명)
    """
    aliases = _get_model_aliases()
    expanded = [query]

    query_lower = query.lower().strip()
    query_normalized = normalize_search_term(query)

    # 정규화된 검색어로 별칭 찾기
    if query_normalized in aliases:
        expanded.append(aliases[query_normalized])

    # 원본 검색어(소문자)로도 별칭 찾기
    if query_lower in aliases:
        expanded.append(aliases[query_lower])

    # 각 토큰별로 별칭 확장
    for token in query_lower.split():
        token_norm = normalize_search_term(token)
        if token_norm in aliases:
            expanded.append(aliases[token_norm])
        if token in aliases:
            expanded.append(aliases[token])

    return list(set(expanded))


# =============================================================================
# Instrument Matching
# =============================================================================

def calculate_instrument_match_score(query: str, instrument: Instrument) -> float:
    """
    검색어와 악기의 매칭 스코어 계산.

    Scoring Tiers (개선된 우선순위):
        1.0  - 정규화된 이름 정확 일치 (DS-1 == DS-1)
        0.95 - 별칭 확장 후 정확 일치
        0.9  - 단어 경계 일치 (검색어가 완전한 토큰)
        0.7  - 부분 포함 + Length Penalty (접미사 없음)
        0.5  - 부분 포함 + 버전 접미사 있음 (DS-1W 등)
        0.4  - 토큰 기반 매칭
        0.3  - 유사도 기반 매칭

    Args:
        query: 검색어
        instrument: Instrument 모델 인스턴스

    Returns:
        0.0 ~ 1.0 사이의 매칭 스코어
    """
    query_normalized = normalize_search_term(query)
    query_tokens = tokenize_query(query)
    expanded_queries = expand_query_with_aliases(query)

    name = instrument.name or ""
    brand = instrument.brand or ""
    name_normalized = normalize_search_term(name)
    brand_normalized = normalize_search_term(brand)
    full_name = f"{brand} {name}".strip()
    full_normalized = normalize_search_term(full_name)

    # =========================================================================
    # Tier -1: 브랜드 불일치 필터링 (Brand Mismatch Hard Filter)
    # =========================================================================
    # 쿼리에서 명확한 브랜드가 감지되었는데, 악기 브랜드와 다르면 제외
    # 예: "Gibson Les Paul" 검색 시 "Epiphone Les Paul"은 제외되어야 함
    detected_brand = extract_brand(query)
    if detected_brand and is_known_brand(detected_brand):
        # 감지된 브랜드가 악기 브랜드(정규화됨)에 포함되지 않으면 불일치로 간주
        # (예: detected="gibson", brand="epiphone" -> 불일치)
        # (예: detected="fender", brand="squier by fender" -> 일치 허용)
        if brand_normalized and normalize_search_term(detected_brand) not in brand_normalized:
            logger.debug(f"[Score 0.0] 브랜드 불일치: 쿼리('{detected_brand}') != 악기('{brand}')")
            return 0.0

    # =========================================================================
    # Tier 0: 정규화된 이름 정확 일치 (최우선)
    # =========================================================================
    if query_normalized == name_normalized:
        logger.debug(f"[Score 1.0] 정확 일치: '{query}' == '{name}'")
        return 1.0

    # Tier 0.5: 전체 이름(브랜드+모델) 정확 일치
    if query_normalized == full_normalized:
        logger.debug(f"[Score 1.0] 전체 일치: '{query}' == '{full_name}'")
        return 1.0

    # =========================================================================
    # Tier 1: 별칭 확장 후 정확 일치
    # =========================================================================
    for expanded in expanded_queries:
        expanded_norm = normalize_search_term(expanded)
        if expanded_norm == name_normalized:
            logger.debug(f"[Score 0.95] 별칭 정확 일치: '{expanded}' == '{name}'")
            return 0.95

    # =========================================================================
    # Tier 2: 모델명이 검색어에 포함 (사용자가 더 긴 쿼리 입력)
    # =========================================================================
    if name_normalized and name_normalized in query_normalized:
        logger.debug(f"[Score 0.9] 모델명 포함: '{name}' in '{query}'")
        return 0.9

    # =========================================================================
    # Tier 3: 검색어가 모델명에 포함 (부분 일치)
    # - 버전 접미사 검사 (DS-1 vs DS-1W)
    # - Length Penalty 적용
    # =========================================================================
    if query_normalized and query_normalized in name_normalized:
        idx = name_normalized.find(query_normalized)
        suffix_start = idx + len(query_normalized)
        
        # 검색어 뒤에 문자가 붙어있는지 확인 (버전 접미사)
        if suffix_start < len(name_normalized):
            next_char = name_normalized[suffix_start]
            # 알파벳/숫자가 바로 붙어있으면 다른 모델 (DS-1W, SM57-LC 등)
            if next_char.isalnum():
                logger.debug(f"[Score 0.5] 버전 접미사 감지: '{query}' in '{name}' (suffix: '{name_normalized[suffix_start:]}')")
                return 0.5
        
        # 접미사 없음 → Length Penalty 적용
        length_diff = len(name_normalized) - len(query_normalized)
        # 글자 차이가 클수록 점수 감소 (최소 0.5)
        penalty = max(0.5, 1.0 - (length_diff * 0.05))
        score = 0.7 * penalty
        logger.debug(f"[Score {score:.2f}] 부분 포함: '{query}' in '{name}' (length_diff={length_diff})")
        return score

    # =========================================================================
    # Tier 4: 별칭 확장 쿼리가 모델명에 포함
    # =========================================================================
    for expanded in expanded_queries:
        if expanded.lower() in name.lower():
            logger.debug(f"[Score 0.6] 별칭 부분 포함: '{expanded}' in '{name}'")
            return 0.6

    # =========================================================================
    # Tier 5: 토큰 기반 매칭
    # =========================================================================
    all_tokens = query_tokens.copy()
    for expanded in expanded_queries:
        all_tokens.extend(tokenize_query(expanded))
    all_tokens = list(set(all_tokens))

    matched_tokens = sum(
        1 for token in all_tokens
        if normalize_search_term(token) in name_normalized
        or normalize_search_term(token) in brand_normalized
    )

    if matched_tokens > 0 and all_tokens:
        score = 0.4 * (matched_tokens / len(all_tokens))
        logger.debug(f"[Score {score:.2f}] 토큰 매칭: {matched_tokens}/{len(all_tokens)}")
        return score

    # =========================================================================
    # Tier 6: 유사도 기반 매칭 (fallback)
    # =========================================================================
    similarity = SequenceMatcher(None, query_normalized, name_normalized).ratio()
    if similarity > 0.6:
        score = 0.3 * similarity
        logger.debug(f"[Score {score:.2f}] 유사도: {similarity:.2f}")
        return score

    return 0.0


def find_best_matching_instruments(
    query: str,
    instruments_qs: QuerySet[Instrument],
    min_score: float = 0.3,
) -> list[tuple[Instrument, float]]:
    """
    검색어에 가장 잘 맞는 악기들을 스코어 순으로 반환.

    Args:
        query: 검색어
        instruments_qs: Instrument QuerySet
        min_score: 최소 스코어 (이하는 제외)

    Returns:
        (instrument, score) 튜플 리스트, 스코어 내림차순 정렬
    """
    scored_instruments = [
        (instrument, calculate_instrument_match_score(query, instrument))
        for instrument in instruments_qs
    ]

    # 최소 스코어 이상만 필터링
    scored_instruments = [
        (inst, score) for inst, score in scored_instruments
        if score >= min_score
    ]

    # 스코어 내림차순 정렬
    scored_instruments.sort(key=lambda x: x[1], reverse=True)

    if scored_instruments:
        best = scored_instruments[0]
        logger.info(
            f"[매칭 결과] query='{query}' -> "
            f"Best: {best[0].brand} {best[0].name} (score={best[1]:.2f})"
        )

    return scored_instruments
