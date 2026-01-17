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
        ('other', '기타 악기'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=500, verbose_name='모델명')
    brand = models.CharField(max_length=100, verbose_name='브랜드')
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
        # 브랜드/모델명 소문자 정규화 (입력 편의)
        if self.brand:
            self.brand = self.brand.lower().strip()
        if self.name:
            self.name = self.name.lower().strip()
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
