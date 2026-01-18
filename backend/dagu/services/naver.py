"""
Naver Shopping API Service for MALCHA-DAGU.

Provides search functionality with caching and quality filtering.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import logging
from typing import Any

import requests
from django.conf import settings
from django.core.cache import cache

from ..config import CrawlerConfig
from ..filters import filter_naver_item, filter_naver_item_with_reason, calculate_dynamic_min_price
from .utils import normalize_brand

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

NAVER_API_URL = 'https://openapi.naver.com/v1/search/shop.json'
CACHE_TTL = 60 * 60  # 1시간


# =============================================================================
# Naver Shopping API Service
# =============================================================================

class NaverShoppingService:
    """
    네이버 쇼핑 API 연동 서비스.

    Features:
        - Redis 캐싱 (1시간 TTL)
        - 병렬 페이지 요청 (ThreadPoolExecutor)
        - 6단계 품질 필터링
        - 한글 브랜드명 정규화

    Usage:
        >>> service = NaverShoppingService()
        >>> results = service.search("BOSS DS-1", display=20)
    """

    def __init__(self) -> None:
        self.client_id = settings.NAVER_CLIENT_ID
        self.client_secret = settings.NAVER_CLIENT_SECRET
        self.headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
        }
        self._timeout = CrawlerConfig.TIMEOUT_NAVER

    def _get_cache_key(
        self,
        query: str,
        display: int,
        brand: str | None = None,
        category: str | None = None,
        min_price: int | None = None,
    ) -> str:
        """캐시 키 생성 (검색어 + 필터 조건 해시)"""
        key_base = f"naver_search:{query}:{display}:{brand or ''}:{category or ''}:{min_price or ''}"
        return hashlib.md5(key_base.encode()).hexdigest()

    def _normalize_query(self, query: str) -> str:
        """검색어 정규화 (한글 브랜드 -> 영문)"""
        return normalize_brand(query)

    def _fetch_page(self, query: str, start: int, sort: str) -> list[dict]:
        """단일 페이지 API 요청"""
        try:
            params = {
                'query': query,
                'display': 100,
                'start': start,
                'sort': sort,
                'exclude': 'rental',
            }
            response = requests.get(
                NAVER_API_URL,
                headers=self.headers,
                params=params,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return response.json().get('items', [])

        except requests.exceptions.RequestException as e:
            logger.error(f"Naver API Error (start={start}): {e}")
            return []

    def _fetch_all_pages(self, query: str, sort: str, target_count: int = 200) -> list[dict]:
        """병렬 페이지 요청으로 대량 아이템 수집"""
        page_size = 100
        starts = list(range(1, target_count, page_size))

        all_items = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            logger.info(f"병렬 수집 시작: {target_count}개 목표")

            futures = {
                executor.submit(self._fetch_page, query, start, sort): start
                for start in starts
            }

            for future in concurrent.futures.as_completed(futures):
                items = future.result()
                all_items.extend(items)

        logger.info(f"병렬 수집 완료: 총 {len(all_items)}개 아이템")
        return all_items

    def search(
        self,
        query: str,
        display: int = 20,
        sort: str = 'sim',
        brand: str | None = None,
        category: str | None = None,
        min_price: int | None = None,
        reference_price: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        네이버 쇼핑 API 검색 + 필터링.

        Args:
            query: 검색어
            display: 결과 개수 (최대 100)
            sort: 정렬 (sim: 정확도, date: 날짜, asc: 가격낮은순, dsc: 가격높은순)
            brand: 브랜드 필터 (선택)
            category: 카테고리 필터 (선택)
            min_price: 최소 가격 필터 (선택)
            reference_price: 신품 기준가 (있으면 이 값의 10%를 최소가로 사용)

        Returns:
            필터링된 검색 결과 리스트
        """
        # API 키 확인 - 누락 시 명확한 예외 발생
        if not self.client_id or not self.client_secret:
            logger.critical("Naver API credentials not configured - Search unavailable")
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "NAVER_CLIENT_ID and NAVER_CLIENT_SECRET must be set for search functionality"
            )

        # 검색어 정규화
        normalized_query = self._normalize_query(query)

        # 캐시 확인 (필터 조건 포함)
        cache_key = self._get_cache_key(
            normalized_query, display * 3, brand, category, min_price
        )
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            logger.debug(f"Cache HIT: {query}")
            raw_items = cached_result
        else:
            logger.info(f"Cache MISS - API 호출: {query}")

            try:
                raw_items = self._fetch_all_pages(normalized_query, sort)
                cache.set(cache_key, raw_items, CACHE_TTL)
                logger.debug(f"[Cache] 저장 완료: {len(raw_items)}개")

            except Exception as e:
                logger.exception(f"Naver API error: {e}")
                return []

        # 필터링 적용
        filtered_items = self._apply_filters(
            raw_items, query, brand, category, min_price, reference_price, display
        )

        # 스코어순 -> 가격순 정렬
        filtered_items.sort(key=lambda x: (-x.get('score', 0), x.get('lprice', 0)))

        self._log_results(raw_items, filtered_items, display)

        return filtered_items[:display]

    def _apply_filters(
        self,
        items: list[dict],
        query: str,
        brand: str | None,
        category: str | None,
        min_price: int | None,
        reference_price: int | None,
        display: int,
    ) -> list[dict]:
        """아이템 필터링 적용 (상세 로그 포함)"""
        filtered = []
        filter_stats = {
            'price': 0,
            'blacklist': 0,
            'brand': 0,
            'category': 0,
            'category_fields': 0,
            'product_type': 0,
            'dynamic_price': 0,
            'passed': 0,
        }

        # [동적 가격 필터링] reference_price가 없으면 가격 분포 기반으로 최소가 계산
        dynamic_min_price = None
        if not reference_price and not min_price:
            # 먼저 가격 목록 추출 (블랙리스트 제외 전)
            prices = []
            for item in items:
                try:
                    lprice = int(item.get('lprice', 0))
                    if lprice > 0:
                        prices.append(lprice)
                except (ValueError, TypeError):
                    pass

            if prices:
                dynamic_min_price = calculate_dynamic_min_price(prices)

        for item in items:
            result, reason = filter_naver_item_with_reason(
                item=item,
                query=query,
                brand=brand,
                category=category,
                min_price=min_price,
                reference_price=reference_price,
            )
            if result:
                # 동적 가격 필터 추가 적용 (reference_price 없을 때만)
                if dynamic_min_price and result['lprice'] < dynamic_min_price:
                    filter_stats['dynamic_price'] += 1
                    logger.debug(f"[동적필터] 제외: {result['lprice']:,}원 < {dynamic_min_price:,}원 - {result['title'][:40]}")
                    continue

                filter_stats['passed'] += 1
                filtered.append(result)
            else:
                filter_stats[reason] = filter_stats.get(reason, 0) + 1

        # 필터링 통계 로그
        logger.info(
            f"[필터 통계] 통과: {filter_stats['passed']} | "
            f"가격: {filter_stats['price']} | "
            f"동적가격: {filter_stats['dynamic_price']} | "
            f"블랙리스트: {filter_stats['blacklist']} | "
            f"브랜드: {filter_stats['brand']} | "
            f"카테고리: {filter_stats['category']} | "
            f"액세서리: {filter_stats['category_fields']} | "
            f"상품타입: {filter_stats['product_type']}"
        )

        # NOTE: truncation은 정렬 후 search()에서 수행
        return filtered

    def _log_results(
        self,
        raw_items: list[dict],
        filtered_items: list[dict],
        display: int,
    ) -> None:
        """결과 로깅"""
        logger.info(
            f"[Naver] 필터링: 원본({len(raw_items)}) -> "
            f"통과({len(filtered_items)}) -> 반환({min(len(filtered_items), display)})"
        )

        if filtered_items:
            logger.info("상위 결과:")
            for i, item in enumerate(filtered_items[:3], 1):
                logger.info(
                    f"  {i}. [{item['lprice']:,}원] "
                    f"{item['title'][:40]}... ({item.get('mallName', 'N/A')})"
                )
