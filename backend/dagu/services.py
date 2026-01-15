"""
Business logic services for MALCHA-DAGU.

- NaverShoppingService: 네이버 쇼핑 API 연동 + 캐싱 + 필터링
- SearchAggregatorService: 네이버 + DB 데이터 병합
- AIDescriptionService: AI 악기 설명 생성
"""

import hashlib
import logging
import re
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
        # 1. 캐시 확인 (필터 적용 전 원본 데이터)
        cache_key = self._get_cache_key(query, display * 3)  # 필터링 고려하여 3배 요청
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
                # enhanced_query = build_exclusion_query(query)
                enhanced_query = query  # 원본 쿼리 사용
                logger.info(f"📝 검색 쿼리: '{enhanced_query}'")
                
                # 필터링으로 탈락할 것 고려하여 더 많이 요청
                params = {
                    'query': enhanced_query,
                    'display': min(display * 3, 100),  # 최대 100개
                    'sort': sort,
                    'exclude': 'rental',  # 렌탈만 제외 (해외직구 허용)
                }
                
                logger.info(f"📤 API 요청: display={params['display']}, sort={params['sort']}, exclude={params['exclude']}")
                
                response = requests.get(
                    NAVER_API_URL,
                    headers=self.headers,
                    params=params,
                    timeout=CrawlerConfig.TIMEOUT_NAVER,
                )
                
                logger.info(f"📥 API 응답: status={response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                raw_items = data.get('items', [])
                total = data.get('total', 0)
                
                logger.info(f"📦 [Naver] API 결과: total={total}, items={len(raw_items)}")
                
                # 캐싱 (원본 데이터)
                cache.set(cache_key, raw_items, CACHE_TTL)
                logger.info(f"[Cache] 캐싱 완료: {len(raw_items)}개 아이템")
                
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
        
        logger.info(f"🔍 필터링 시작: {len(raw_items)}개 아이템")
        
        for item in raw_items:
            stats['total'] += 1
            title = item.get('title', '')[:50]
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
        
        logger.info(f"🔍 검색 시작: '{query}' (브랜드: {brand}, 카테고리: {category})")
        
        # 1. 네이버 API 검색 (필터링 적용)
        naver_items = self.naver_service.search(
            query=query, 
            display=display,
            brand=brand,
            category=category,
        )
        
        # 2. DB 유저 매물 검색 (활성 + 미만료)
        now = timezone.now()
        user_items_qs = UserItem.objects.filter(
            is_active=True,
            expired_at__gt=now,
        ).filter(
            # 검색어로 악기 이름/브랜드 또는 매물 제목 검색
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
            
            # 최소 가격 필터
            if not check_min_price(item.price):
                continue
            
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
