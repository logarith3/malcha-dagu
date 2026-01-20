"""
Serializers for MALCHA-DAGU API.
"""

from rest_framework import serializers

from .models import Instrument, UserItem, Brand


class BrandSerializer(serializers.ModelSerializer):
    """브랜드 시리얼라이저"""
    class Meta:
        model = Brand
        fields = ['name', 'slug', 'logo_url', 'description']


class InstrumentSerializer(serializers.ModelSerializer):
    """악기 마스터 시리얼라이저"""
    
    category_display = serializers.CharField(
        source='get_category_display', 
        read_only=True
    )
    # 브랜드 상세 정보 (읽기 전용)
    brand_detail = BrandSerializer(source='brand_obj', read_only=True)
    
    class Meta:
        model = Instrument
        fields = [
            'id', 'name', 'brand', 'brand_detail', 'category', 'category_display',
            'image_url', 'reference_price', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InstrumentMinimalSerializer(serializers.ModelSerializer):
    """악기 간단 정보 (목록용)"""
    
    class Meta:
        model = Instrument
        fields = ['id', 'name', 'brand', 'image_url', 'reference_price']


class UserItemSerializer(serializers.ModelSerializer):
    """유저 매물 시리얼라이저"""

    instrument_detail = InstrumentMinimalSerializer(
        source='instrument',
        read_only=True
    )
    source_display = serializers.CharField(
        source='get_source_display',
        read_only=True
    )
    discount_rate = serializers.FloatField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = UserItem
        fields = [
            'id', 'instrument', 'instrument_detail', 'price', 'link',
            'source', 'source_display', 'title', 'is_active',
            'expired_at', 'extended_at', 'click_count', 'discount_rate',
            'is_expired', 'is_owner', 'report_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'click_count', 'extended_at', 'report_count', 'created_at', 'updated_at'
        ]

    def get_is_owner(self, obj):
        """현재 요청 유저가 소유자인지 확인"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.owner_id == request.user.id
        return False


class UserItemCreateSerializer(serializers.ModelSerializer):
    """유저 매물 생성용 시리얼라이저"""
    
    class Meta:
        model = UserItem
        fields = ['instrument', 'price', 'link', 'source', 'title']
        extra_kwargs = {
            'instrument': {'required': False, 'allow_null': True}  # 백엔드에서 자동 매칭
        }


class NaverItemSerializer(serializers.Serializer):
    """네이버 쇼핑 API 응답 시리얼라이저"""
    
    title = serializers.CharField()
    link = serializers.URLField()
    image = serializers.URLField()
    lprice = serializers.IntegerField()  # 최저가
    hprice = serializers.IntegerField(required=False, default=0)  # 최고가
    mallName = serializers.CharField()
    productId = serializers.CharField()
    productType = serializers.IntegerField()
    
    # 가공된 필드
    source = serializers.SerializerMethodField()
    
    def get_source(self, obj):
        return 'naver'


class SearchResultSerializer(serializers.Serializer):
    """통합 검색 결과 시리얼라이저"""

    # 검색 메타 정보
    query = serializers.CharField()
    search_query = serializers.CharField()  # 정규화된 검색어 (외부 링크용)
    total_count = serializers.IntegerField()

    # 신품 정보
    reference = serializers.DictField(required=False)
    
    # Taxonomy 정보 (DB 기반)
    taxonomy = serializers.DictField(required=False, allow_null=True)
    
    # 매칭된 악기 정보 (매물 등록용)
    matched_instrument = serializers.DictField(required=False, allow_null=True)
    
    # 가격순 정렬된 통합 결과
    items = serializers.ListField()
    
    # 네이버 결과만
    naver_items = serializers.ListField()
    
    # 유저 매물만
    user_items = serializers.ListField()


class AIDescriptionRequestSerializer(serializers.Serializer):
    """AI 설명 요청 시리얼라이저"""
    
    model_name = serializers.CharField(max_length=200)
    brand = serializers.CharField(max_length=100)
    category = serializers.CharField(max_length=50)


class AIDescriptionResponseSerializer(serializers.Serializer):
    """AI 설명 응답 시리얼라이저"""
    
    summary = serializers.CharField()
    check_point = serializers.CharField(allow_blank=True)
