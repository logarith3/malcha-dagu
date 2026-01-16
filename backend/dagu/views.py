"""
API Views for MALCHA-DAGU.
"""

import logging

from django.db import models, transaction

logger = logging.getLogger(__name__)
from django.db.models import F
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Instrument, UserItem
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
    """
    permission_classes = [AllowAny]  # 인증 없이 검색 가능
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'search'

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

        # 통합 검색 수행
        try:
            service = SearchAggregatorService()
            result = service.search(query, display)
        except Exception as e:
            logger.exception(f"Search error for query '{query}': {e}")
            return Response(
                {'error': '검색 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        serializer = SearchResultSerializer(result)
        return Response(serializer.data)


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
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(brand__icontains=search)
            )
        
        return queryset


# =============================================================================
# UserItem ViewSet (CRUD + Click Tracking)
# =============================================================================

class UserItemViewSet(viewsets.ModelViewSet):
    """
    유저 매물 CRUD API.

    GET    /api/items/              - 목록 (모두 허용)
    POST   /api/items/              - 생성 (로그인 필수)
    GET    /api/items/{id}/         - 상세 (모두 허용)
    PUT    /api/items/{id}/         - 수정 (로그인 필수)
    DELETE /api/items/{id}/         - 삭제 (로그인 필수)
    POST   /api/items/{id}/click/   - 클릭 추적 (모두 허용)
    """

    queryset = UserItem.objects.filter(is_active=True)

    def get_permissions(self):
        """액션별 권한 분기"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            from rest_framework.permissions import IsAuthenticated
            return [IsAuthenticated()]
        return [AllowAny()]
    
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
        return response

    def perform_create(self, serializer):
        """
        매물 생성 시 악기 정보를 자동으로 연결합니다.
        1. 이름이 일치하는 악기가 있으면 연결
        2. 없으면 새로운 악기(Unknown 브랜드) 생성 후 연결
        """
        title = serializer.validated_data.get('title', '').strip()
        
        # 악기 찾기 또는 생성
        instrument = Instrument.objects.filter(name__iexact=title).first()
        
        if not instrument:
            instrument = Instrument.objects.create(
                name=title,
                brand='Unknown',
                category='other'
            )
            
        serializer.save(instrument=instrument)
    
    @action(detail=True, methods=['post'])
    def click(self, request, pk=None):
        """
        클릭 추적 API.
        - click_count 증가 (Atomic Update로 동시성 문제 방지)
        - expired_at 12시간 연장
        """
        item = self.get_object()
        
        with transaction.atomic():
            # Atomic update로 click_count 증가
            UserItem.objects.filter(pk=pk).update(
                click_count=F('click_count') + 1,
                expired_at=timezone.now() + timezone.timedelta(hours=12),
            )
        
        # 갱신된 데이터 반환
        item.refresh_from_db()
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
