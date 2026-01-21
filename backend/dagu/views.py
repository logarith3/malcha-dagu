"""
API Views for MALCHA-DAGU.
"""

import logging

from django.core.cache import cache
from django.db import models, transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle, UserRateThrottle
from rest_framework.views import APIView

from .models import Instrument, ItemClick, ItemReport, SearchQuery, UserItem
from .permissions import IsOwnerOrReadOnly
from .serializers import (
    AIDescriptionRequestSerializer,
    AIDescriptionResponseSerializer,
    InstrumentSerializer,
    SearchResultSerializer,
    UserItemCreateSerializer,
    UserItemSerializer,
)
from .services import SearchAggregatorService
# from .services import AIDescriptionService  # 임시 비활성화


# =============================================================================
# Auth Check API (SSO)
# =============================================================================

class AuthCheckView(APIView):
    """
    SSO 인증 상태 확인 API.
    HttpOnly 쿠키는 JS에서 읽을 수 없으므로, 서버에서 확인.

    GET /api/auth/check/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user and request.user.is_authenticated:
            return Response({
                'is_authenticated': True,
                'user_id': request.user.id,
                'username': request.user.username,
            })
        return Response({
            'is_authenticated': False,
        })


# =============================================================================
# Search API
# =============================================================================

class SearchView(APIView):
    """
    통합 검색 API.
    네이버 쇼핑 + DB 유저 매물을 가격순으로 병합.

    GET /api/search/?q={검색어}&display={개수}

    캐싱 전략:
    - 네이버 API 결과만 캐싱 (3분)
    - 유저 매물은 항상 실시간 DB 조회 (즉시 반영)
    """
    permission_classes = [AllowAny]  # 인증 없이 검색 가능
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'search'

    CACHE_TTL = 60 * 3  # 3분 (네이버 결과만 캐싱)

    def get(self, request):
        query = request.query_params.get('q', '').strip()

        if not query:
            return Response(
                {'error': '검색어를 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 검색어 길이 제한 (XSS/Injection 방지)
        if len(query) > 200:
            return Response(
                {'error': '검색어는 200자 이하로 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # display 파라미터 검증
        try:
            display = int(request.query_params.get('display', 20))
        except (ValueError, TypeError):
            display = 20
        display = min(max(display, 1), 100)  # 1~100 범위 제한

        # 통합 검색 수행 (네이버는 캐싱, 유저 매물은 실시간)
        try:
            service = SearchAggregatorService()
            result = service.search_with_cache(query, display, cache, self.CACHE_TTL)
        except Exception as e:
            logger.exception(f"Search error for query '{query}': {e}")
            return Response(
                {'error': '검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 검색어 추적 (서비스에서 정규화된 쿼리 사용)
        effective_query = result.get('query', query)
        self._track_search_query(effective_query)

        serializer = SearchResultSerializer(result)
        response_data = serializer.data

        return Response(response_data)

    def _track_search_query(self, query: str):
        """검색어 카운트 증가 (중복 시 업데이트)"""
        try:
            normalized = query.strip().lower()
            if len(normalized) < 2:
                return  # 너무 짧은 검색어 무시

            obj, created = SearchQuery.objects.get_or_create(
                query__iexact=normalized,
                defaults={'query': query}
            )
            if not created:
                # 검색 횟수 증가 + 최근 검색 시간 갱신
                # + 디스플레이용 쿼리(대소문자)를 최신으로 업데이트 (예: fender -> Fender)
                SearchQuery.objects.filter(pk=obj.pk).update(
                    search_count=F('search_count') + 1,
                    last_searched_at=timezone.now(),
                    query=query  # 최신 케이싱 반영
                )
        except Exception as e:
            logger.warning(f"Failed to track search query: {e}")


class PopularSearchView(APIView):
    """
    인기 검색어(트렌딩) API.
    최근 클릭 수 기반 "지금 뜨는" 악기 반환.

    GET /api/popular-searches/?limit=4

    트렌딩 로직:
    1시간 내 클릭 많은 순 → 데이터 부족 시 24시간 확장 → 그래도 부족 시 검색 횟수 fallback
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from datetime import timedelta
        from django.db.models import Count
        from .services.utils import normalize_brand, normalize_search_term

        # 파라미터
        try:
            limit = int(request.query_params.get('limit', 4))
        except (ValueError, TypeError):
            limit = 4
        limit = min(max(limit, 1), 10)  # 1~10 범위

        terms = []
        seen_normalized = set()  # 중복 제거용 (정규화된 키)

        def add_term(term):
            """검색어 추가 함수 (중복 체크 및 limit 확인)"""
            if len(terms) >= limit:
                return False
            
            if not term:
                return True

            # 정규화하여 중복 체크 (예: "펜더" -> "fender")
            # 브랜드명 통일 + 소문자/공백제거
            normalized = normalize_search_term(normalize_brand(term))
            
            if normalized not in seen_normalized:
                terms.append(term)
                seen_normalized.add(normalized)
            
            return True

        # 1단계: 실제 검색 횟수 우선 (최근 7일)
        # - 사용자가 실제로 입력한 "의도"가 가장 정확함
        week_ago = timezone.now() - timedelta(days=7)
        popular_searches = SearchQuery.objects.filter(
            last_searched_at__gte=week_ago
        ).order_by('-search_count')[:limit * 3]

        for sq in popular_searches:
            add_term(sq.query)

        # 2단계: 데이터 부족 시 최근 클릭된 매물 (보조)
        # - 검색 데이터가 없을 때 트렌딩 매물로 보완
        if len(terms) < limit:
            day_ago = timezone.now() - timedelta(hours=24)
            recent_clicks = UserItem.objects.filter(
                clicks__clicked_at__gte=day_ago,
                is_active=True,
            ).annotate(
                click_count=Count('clicks')
            ).order_by('-click_count')[:limit * 3]

            for item in recent_clicks:
                # 브랜드 + 이름 조합
                term_candidate = f"{item.instrument.brand} {item.instrument.name}"
                add_term(term_candidate)

        # 3단계: 최종 fallback - 기본값
        defaults = ['펜더 스트랫', '깁슨 레스폴', '테일러 어쿠스틱', '야마하 THR']
        for d in defaults:
            add_term(d)

        return Response({'terms': terms[:limit]})


# =============================================================================
# Instrument ViewSet (CRUD)
# =============================================================================

class InstrumentViewSet(viewsets.ModelViewSet):
    """
    악기 마스터 CRUD API.

    GET    /api/instruments/          - 목록 (모두 허용)
    POST   /api/instruments/          - 생성 (관리자만)
    GET    /api/instruments/{id}/     - 상세 (모두 허용)
    PUT    /api/instruments/{id}/     - 수정 (관리자만)
    DELETE /api/instruments/{id}/     - 삭제 (관리자만)
    """
    queryset = Instrument.objects.all()
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        """액션별 권한 분기"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 필터링 옵션
        brand = self.request.query_params.get('brand')
        category = self.request.query_params.get('category')
        search = self.request.query_params.get('search')
        
        if brand:
            queryset = queryset.filter(brand__icontains=brand)
        if category:
            queryset = queryset.filter(category=category)
        if search:
            # 검색어를 공백으로 분리하여 각 단어가 브랜드나 이름 중 하나에 포함되어야 함 (AND 조건)
            # 예: "fender strat" -> (brand="fender" OR name="fender") AND (brand="strat" OR name="strat")
            search_terms = search.split()
            for term in search_terms:
                queryset = queryset.filter(
                    models.Q(name__icontains=term) |
                    models.Q(brand__icontains=term)
                )
        
        return queryset


# =============================================================================
# UserItem ViewSet (CRUD + Click Tracking)
# =============================================================================

class CreateItemThrottle(UserRateThrottle):
    """매물 등록 스팸 방지 (분당 10회로 완화)"""
    rate = '10/min'


class UserItemViewSet(viewsets.ModelViewSet):
    """
    유저 매물 CRUD API.

    GET    /api/items/              - 목록 (모두 허용)
    POST   /api/items/              - 생성 (로그인 필수, Rate Limit: 3/min)
    GET    /api/items/{id}/         - 상세 (모두 허용)
    PUT    /api/items/{id}/         - 수정 (본인만, IDOR 방지)
    DELETE /api/items/{id}/         - 삭제 (본인만, IDOR 방지)
    POST   /api/items/{id}/click/   - 클릭 추적 (모두 허용)
    """

    queryset = UserItem.objects.filter(is_active=True, is_under_review=False)
    permission_classes = [IsOwnerOrReadOnly]

    def get_permissions(self):
        """액션별 권한 분기"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrReadOnly()]
        return [AllowAny()]
    
    def get_throttles(self):
        """액션별 Throttle 분기"""
        if self.action == 'create':
            return [CreateItemThrottle()]
        return super().get_throttles()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return UserItemCreateSerializer
        return UserItemSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 만료된 항목 제외
        now = timezone.now()
        queryset = queryset.filter(expired_at__gt=now)
        
        # 필터링 옵션
        instrument_id = self.request.query_params.get('instrument')
        source = self.request.query_params.get('source')
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if instrument_id:
            queryset = queryset.filter(instrument_id=instrument_id)
        if source:
            queryset = queryset.filter(source=source)
        if min_price:
            try:
                min_price_int = int(min_price)
                if min_price_int < 0:
                    raise ValueError("min_price must be positive")
                queryset = queryset.filter(price__gte=min_price_int)
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'min_price': f'유효하지 않은 값: {min_price}'})
        if max_price:
            try:
                max_price_int = int(max_price)
                if max_price_int < 0:
                    raise ValueError("max_price must be positive")
                queryset = queryset.filter(price__lte=max_price_int)
            except (ValueError, TypeError):
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'max_price': f'유효하지 않은 값: {max_price}'})
        
        return queryset.select_related('instrument')

    def create(self, request, *args, **kwargs):
        logger.debug(f"UserItemViewSet.create called with data: {request.data}")
        response = super().create(request, *args, **kwargs)
        logger.debug(f"create success, response: {response.data}")
        # 캐시 무효화 불필요: 유저 매물은 항상 실시간 DB 조회됨
        return response

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

    def _is_allowed_link(self, link: str) -> bool:
        """허용된 도메인 및 프로토콜 확인 (XSS/Open Redirect 방지)"""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(link.lower())
            # 프로토콜 검증: http/https만 허용 (javascript:, data: 등 차단)
            if parsed.scheme not in ['http', 'https']:
                logger.warning(f"Invalid protocol detected: {parsed.scheme}")
                return False
            # 도메인 검증
            domain = parsed.netloc
            if not domain:  # 도메인이 없으면 거부
                return False
            return any(allowed in domain for allowed in self.ALLOWED_DOMAINS)
        except Exception as e:
            logger.warning(f"URL parsing error: {e}")
            return False

    def perform_create(self, serializer):
        """
        매물 생성 시 악기 정보를 연결합니다.
        1. instrument ID가 있으면 바로 사용 (검색 결과의 matched_instrument)
        2. 없으면 title로 자동 매칭
        """
        from rest_framework.exceptions import ValidationError
        from .services.utils import (
            normalize_brand, tokenize_query, expand_query_with_aliases,
            find_best_matching_instruments
        )

        link = serializer.validated_data.get('link', '').strip()
        instrument_id = serializer.validated_data.get('instrument')
        title = serializer.validated_data.get('title', '').strip()

        # 허용된 사이트 검증
        if not self._is_allowed_link(link):
            raise ValidationError({
                'link': '허용되지 않은 사이트입니다. (뮬, 번개장터, 당근마켓, 중고나라만 가능)'
            })

        # 링크 중복 체크 (활성 매물 중)
        if UserItem.objects.filter(link=link, is_active=True).exists():
            raise ValidationError({'link': '이미 등록된 매물입니다.'})

        # 악기 결정
        instrument = None

        # 1. instrument ID가 전달되면 바로 사용
        if instrument_id:
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

        if not instrument:
            raise ValidationError({
                'title': '해당하는 악기를 찾을 수 없습니다. 검색 결과 페이지에서 등록해주세요.'
            })

        # owner_id 저장 (JWT user_id)
        owner_id = self.request.user.id if self.request.user.is_authenticated else None
        serializer.save(instrument=instrument, owner_id=owner_id)

    @action(detail=True, methods=['post'])
    def extend(self, request, pk=None):
        """
        유효기간 연장 API (본인 매물만)
        - JWT user_id로 소유자 검증
        - expired_at 72시간 연장
        - extended_at 기록 (우선순위용)
        """
        item = self.get_object()

        # 소유자 검증 (JWT user_id vs owner_id)
        if not request.user.is_authenticated or item.owner_id != request.user.id:
            return Response(
                {'error': '본인 매물만 연장 가능합니다.'},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            item.expired_at = timezone.now() + timezone.timedelta(hours=72)
            item.extended_at = timezone.now()
            item.save(update_fields=['expired_at', 'extended_at'])

        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """
        클릭 추적 API.
        - click_count 증가 (Atomic Update로 동시성 문제 방지)
        - expired_at 12시간 연장
        - ItemClick 로그 기록 (트렌딩 계산용)
        """
        item = self.get_object()

        with transaction.atomic():
            # Atomic update로 click_count 증가
            UserItem.objects.filter(pk=pk).update(
                click_count=F('click_count') + 1,
                expired_at=timezone.now() + timezone.timedelta(hours=12),
            )
            # 클릭 로그 저장 (트렌딩 계산용)
            ItemClick.objects.create(item=item)

        # 갱신된 데이터 반환
        item.refresh_from_db()
        serializer = self.get_serializer(item)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """
        허위 매물 신고 API (로그인 불필요, 세션 기반)
        - 로그인 유저: reporter_id로 중복 체크
        - 비로그인 유저: session_key로 중복 체크
        - 'wrong_price' 3회 이상 → 자동 삭제 (is_active=False)
        - 기타 사유 3회 이상 → 검토 중 상태
        """
        item = self.get_object()

        # 세션 키 확보 (없으면 생성)
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key

        # 본인 매물 신고 방지 (로그인 유저만)
        if request.user.is_authenticated and item.owner_id == request.user.id:
            return Response(
                {'error': '본인 매물은 신고할 수 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reason = request.data.get('reason', 'other')
        detail = request.data.get('detail', '')

        # 유효한 사유인지 확인
        valid_reasons = [choice[0] for choice in ItemReport.REASON_CHOICES]
        if reason not in valid_reasons:
            reason = 'other'

        # 중복 신고 체크
        if request.user.is_authenticated:
            exists = ItemReport.objects.filter(
                item=item, reporter_id=request.user.id
            ).exists()
        else:
            exists = ItemReport.objects.filter(
                item=item, session_key=session_key
            ).exists()

        if exists:
            return Response(
                {'error': '이미 신고한 매물입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # 신고 생성
                ItemReport.objects.create(
                    item=item,
                    reporter_id=request.user.id if request.user.is_authenticated else None,
                    session_key=session_key if not request.user.is_authenticated else None,
                    reason=reason,
                    detail=detail[:500]
                )

                # 신고 횟수 증가
                UserItem.objects.filter(pk=pk).update(
                    report_count=F('report_count') + 1
                )
                item.refresh_from_db()

                # 'wrong_price' 3회 이상 → 자동 삭제
                wrong_price_count = ItemReport.objects.filter(
                    item=item, reason='wrong_price'
                ).count()

                is_deleted = False
                if wrong_price_count >= 3:
                    item.is_active = False
                    item.save(update_fields=['is_active'])
                    is_deleted = True
                    logger.info(f"Item {pk} auto-deleted (wrong_price count: {wrong_price_count})")
                # 기타 사유 3회 이상 → 검토 중
                elif item.report_count >= 3:
                    item.is_under_review = True
                    item.save(update_fields=['is_under_review'])
                    logger.info(f"Item {pk} marked for review (report_count: {item.report_count})")

            return Response({
                'message': '신고가 접수되었습니다.' + (' 해당 매물이 삭제되었습니다.' if is_deleted else ''),
                'report_count': item.report_count,
                'is_under_review': item.is_under_review,
                'is_deleted': is_deleted
            })

        except Exception as e:
            logger.exception(f"Report error for item {pk}: {e}")
            return Response(
                {'error': '신고 처리 중 오류가 발생했습니다.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def update_price(self, request, pk=None):
        """
        가격 업데이트 API (로그인 필수)
        - 가격 변동 사항을 유저가 직접 수정
        - 어뷰징 방지를 위해 로그인 필수
        """
        if not request.user.is_authenticated:
            return Response(
                {'error': '로그인이 필요합니다.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        item = self.get_object()

        try:
            new_price = int(request.data.get('price', 0))
        except (ValueError, TypeError):
            return Response(
                {'error': '유효한 가격을 입력해주세요.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_price <= 0:
            return Response(
                {'error': '가격은 0보다 커야 합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_price > 100_000_000:  # 1억원 제한
            return Response(
                {'error': '가격이 너무 높습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 가격 업데이트 (누가 수정했는지 로깅)
        old_price = item.price
        item.price = new_price
        item.save(update_fields=['price', 'updated_at'])

        logger.info(
            f"Price updated for item {pk}: {old_price} -> {new_price} "
            f"by user {request.user.id}"
        )

        serializer = self.get_serializer(item)
        return Response(serializer.data)


# =============================================================================
# AI Description API (임시 비활성화)
# =============================================================================

# class AIDescriptionView(APIView):
#     """
#     AI 악기 설명 생성 API.
#     할루시네이션 방지 프롬프트 적용.
#
#     POST /api/ai/describe/
#     {
#         "model_name": "DS-1",
#         "brand": "BOSS",
#         "category": "effect"
#     }
#     """
#
#     def post(self, request):
#         serializer = AIDescriptionRequestSerializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#
#         data = serializer.validated_data
#
#         service = AIDescriptionService()
#         result = service.generate_description(
#             model_name=data['model_name'],
#             brand=data['brand'],
#             category=data['category'],
#         )
#
#         response_serializer = AIDescriptionResponseSerializer(result)
#         return Response(response_serializer.data)
