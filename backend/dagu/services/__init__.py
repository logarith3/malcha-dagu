"""
Services package for MALCHA-DAGU.

This package contains the core business logic split into focused modules:
- naver: Naver Shopping API integration
- search: Search aggregation service
- ai: AI description generation
- utils: Search utility functions
"""

from .naver import NaverShoppingService
from .search import SearchAggregatorService
# from .ai import AIDescriptionService  # 임시 비활성화
from .utils import (
    normalize_search_term,
    expand_query_with_aliases,
    tokenize_query,
    calculate_instrument_match_score,
    find_best_matching_instruments,
)

__all__ = [
    # Services
    'NaverShoppingService',
    'SearchAggregatorService',
    # 'AIDescriptionService',  # 임시 비활성화
    # Utilities
    'normalize_search_term',
    'expand_query_with_aliases',
    'tokenize_query',
    'calculate_instrument_match_score',
    'find_best_matching_instruments',
]
