"""
Database models for MALCHA-DAGU.

- Instrument: 악기 마스터 데이터 (관리자만 수정 가능)
- UserItem: 유저가 등록한 중고 매물 (만료 시간 자동 관리)
"""

import uuid
from datetime import timedelta

from django.db import models
from django.utils import timezone


def default_expiry():
    """기본 만료 시간: 72시간 후"""
    return timezone.now() + timedelta(hours=72)



class Brand(models.Model):
    """
    브랜드 정보를 관리하는 모델.
    URL 슬러그, 로고, 설명을 포함하여 브랜드 페이지 구성에 사용됨.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='브랜드명 (정식)')
    slug = models.SlugField(max_length=100, unique=True, verbose_name='URL 슬러그')
    logo_url = models.URLField(max_length=2000, blank=True, verbose_name='로고 URL')
    description = models.TextField(blank=True, verbose_name='브랜드 설명')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = '브랜드'
        verbose_name_plural = '브랜드 목록'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # 기본 슬러그 생성 (간단한 처리)
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Instrument(models.Model):
    """
    악기 마스터 테이블.
    이 데이터는 관리자만 생성/수정 가능.
    """
    
    CATEGORY_CHOICES = [
        ('guitar', '기타'),
        ('bass', '베이스'),
        ('keyboard', '키보드/신디'),
        ('drum', '드럼/퍼커션'),
        ('effect', '이펙터'),
        ('amp', '앰프'),
        ('acoustic', '어쿠스틱'),
        ('mic', '마이크'),
        ('other', '기타 악기'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # [Refactor] 브랜드 관계형 데이터로 전환 중
    # 기존 문자열 필드는 하위 호환성을 위해 유지하되, save()에서 자동 동기화
    brand = models.CharField(max_length=100, verbose_name='브랜드 (Legacy)')
    brand_obj = models.ForeignKey(
        Brand, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='instruments',
        verbose_name='브랜드 (Relation)'
    )
    
    name = models.CharField(max_length=500, verbose_name='모델명')
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='guitar',
        verbose_name='카테고리'
    )
    image_url = models.URLField(max_length=2000, blank=True, verbose_name='대표 이미지 URL')
    reference_price = models.PositiveIntegerField(
        default=0, 
        verbose_name='신품 기준가',
        help_text='신품 정가 (원)'
    )
    description = models.TextField(blank=True, verbose_name='설명')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '악기'
        verbose_name_plural = '악기 목록'
        ordering = ['brand', 'name']
        indexes = [
            models.Index(fields=['brand']),
            models.Index(fields=['category']),
            models.Index(fields=['name']),
        ]

    def save(self, *args, **kwargs):
        # 1. 문자열 정규화
        if self.brand:
            self.brand = self.brand.lower().strip()
        if self.name:
            self.name = self.name.lower().strip()
            
        # 2. Brand 객체 자동 연결 (없으면 생성)
        if self.brand and not self.brand_obj:
            from django.utils.text import slugify
            brand_slug = slugify(self.brand)
            
            # Brand 찾거나 생성
            brand_instance, created = Brand.objects.get_or_create(
                slug=brand_slug,
                defaults={
                    'name': self.brand.title(), # Title Case로 저장 (예: fender -> Fender)
                }
            )
            self.brand_obj = brand_instance
            
        # 3. 반대로 brand_obj만 있고 brand 텍스트가 비어있으면 채워줌
        if self.brand_obj and not self.brand:
            self.brand = self.brand_obj.slug

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand} {self.name}"


class UserItem(models.Model):
    """
    유저가 등록한 중고 매물.
    만료 시간이 지나면 자동으로 비활성화됨 (Celery Beat).
    """
    
    SOURCE_CHOICES = [
        ('bunjang', '번개장터'),
        ('joonggonara', '중고나라'),
        ('danggn', '당근마켓'),
        ('mule', '뮬'),
        ('other', '기타'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    instrument = models.ForeignKey(
        Instrument, 
        on_delete=models.CASCADE, 
        related_name='user_items',
        verbose_name='악기'
    )
    price = models.PositiveIntegerField(verbose_name='판매가')
    link = models.URLField(max_length=2000, verbose_name='판매 링크')
    source = models.CharField(
        max_length=50, 
        choices=SOURCE_CHOICES, 
        default='other',
        verbose_name='출처'
    )
    title = models.CharField(max_length=300, blank=True, verbose_name='매물 제목')
    
    # Status & Lifecycle
    is_active = models.BooleanField(default=True, verbose_name='활성 상태')
    expired_at = models.DateTimeField(
        default=default_expiry, 
        db_index=True,  # 성능 핵심: 인덱싱 필수
        verbose_name='만료 시간'
    )
    click_count = models.PositiveIntegerField(default=0, verbose_name='클릭 수')

    # 소유자 정보 (JWT user_id 저장, FK 없이 정수만)
    owner_id = models.IntegerField(
        null=True, blank=True,
        db_index=True,
        verbose_name='등록자 ID'
    )
    extended_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name='연장 시점'
    )

    # 신고 관련
    report_count = models.PositiveIntegerField(default=0, verbose_name='신고 횟수')
    is_under_review = models.BooleanField(default=False, verbose_name='검토 중')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = '중고 매물'
        verbose_name_plural = '중고 매물 목록'
        ordering = ['price', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'expired_at']),
            models.Index(fields=['price']),
        ]
    
    def __str__(self):
        return f"{self.instrument} - ₩{self.price:,}"
    
    @property
    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expired_at
    
    @property
    def discount_rate(self):
        """신품 대비 할인율 계산"""
        if self.instrument.reference_price > 0:
            discount = (1 - self.price / self.instrument.reference_price) * 100
            return round(discount, 1)
        return 0
    
    def extend_expiry(self, hours=12):
        """
        클릭 시 만료 시간 연장.
        동시성 문제를 피하기 위해 save() 대신 update() 권장.
        """
        self.expired_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expired_at', 'updated_at'])


class SearchQuery(models.Model):
    """
    검색어 추적 모델.
    인기 검색어 집계용.
    """
    query = models.CharField(max_length=200, db_index=True, verbose_name='검색어')
    search_count = models.PositiveIntegerField(default=1, verbose_name='검색 횟수')
    last_searched_at = models.DateTimeField(auto_now=True, verbose_name='마지막 검색')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '검색어'
        verbose_name_plural = '검색어 목록'
        ordering = ['-search_count', '-last_searched_at']

    def __str__(self):
        return f"{self.query} ({self.search_count}회)"


class ItemReport(models.Model):
    """
    유저 신고 내역.
    중복 신고 방지 및 신고 사유 추적용.
    - 로그인 유저: reporter_id 사용
    - 비로그인 유저: session_key 사용
    """

    REASON_CHOICES = [
        ('wrong_price', '가격이 다릅니다'),
        ('sold_out', '이미 판매완료된 매물입니다'),
        ('fake', '허위/사기 매물입니다'),
        ('inappropriate', '부적절한 내용입니다'),
        ('other', '기타'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        UserItem,
        on_delete=models.CASCADE,
        related_name='reports',
        verbose_name='매물'
    )
    # 로그인 유저용
    reporter_id = models.IntegerField(
        null=True, blank=True,
        db_index=True,
        verbose_name='신고자 ID'
    )
    # 비로그인 유저용 (세션 키)
    session_key = models.CharField(
        max_length=40,
        null=True, blank=True,
        db_index=True,
        verbose_name='세션 키'
    )
    reason = models.CharField(
        max_length=50,
        choices=REASON_CHOICES,
        default='other',
        verbose_name='신고 사유'
    )
    detail = models.TextField(blank=True, verbose_name='상세 내용')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '매물 신고'
        verbose_name_plural = '매물 신고 목록'
        ordering = ['-created_at']
        # 복합 유니크 제약 제거 (코드에서 처리)

    def __str__(self):
        return f"{self.item} - {self.get_reason_display()}"


class ItemClick(models.Model):
    """
    클릭 로그 (트렌딩 계산용).
    시간대별 클릭 수를 집계하여 "지금 뜨는" 악기를 표시.
    """
    item = models.ForeignKey(
        UserItem,
        on_delete=models.CASCADE,
        related_name='clicks',
        verbose_name='매물'
    )
    clicked_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '클릭 로그'
        verbose_name_plural = '클릭 로그 목록'
        indexes = [
            models.Index(fields=['clicked_at']),
        ]

    def __str__(self):
        return f"{self.item} - {self.clicked_at}"


class SearchMissLog(models.Model):
    """
    DB 매칭 실패 검색어 로그.
    자주 검색되지만 DB에 없는 악기를 추적하여 우선 등록 대상 파악.
    """
    query = models.CharField(max_length=200, db_index=True, verbose_name='검색어')
    normalized_query = models.CharField(
        max_length=200,
        db_index=True,
        verbose_name='정규화된 검색어',
        help_text='소문자, 공백 정리된 검색어'
    )
    search_count = models.PositiveIntegerField(default=1, verbose_name='검색 횟수')
    last_searched_at = models.DateTimeField(auto_now=True, verbose_name='마지막 검색')
    created_at = models.DateTimeField(auto_now_add=True)

    # 처리 상태
    is_resolved = models.BooleanField(default=False, verbose_name='처리 완료')
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name='처리 시점')
    resolved_instrument = models.ForeignKey(
        Instrument,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_misses',
        verbose_name='등록된 악기'
    )

    class Meta:
        verbose_name = '미등록 검색어'
        verbose_name_plural = '미등록 검색어 목록'
        ordering = ['-search_count', '-last_searched_at']

    def __str__(self):
        status = "✓" if self.is_resolved else "○"
        return f"{status} {self.query} ({self.search_count}회)"

    @classmethod
    def log_miss(cls, query: str):
        """
        검색 미스 기록.
        이미 있으면 카운트 증가, 없으면 새로 생성.
        """
        normalized = query.lower().strip()

        # 너무 짧거나 긴 검색어는 무시
        if len(normalized) < 2 or len(normalized) > 100:
            return None

        obj, created = cls.objects.get_or_create(
            normalized_query=normalized,
            defaults={'query': query}
        )

        if not created:
            # 카운트 증가 (F 표현식으로 race condition 방지)
            from django.db.models import F
            cls.objects.filter(pk=obj.pk).update(
                search_count=F('search_count') + 1
            )

        return obj
