"""
Admin configuration for MALCHA-DAGU.
"""

from django.contrib import admin
from django.utils import timezone

from .models import Instrument, UserItem, SearchMissLog


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['brand', 'name', 'parent', 'category', 'reference_price', 'created_at']
    list_filter = ['category', 'brand']
    search_fields = ['name', 'brand']
    ordering = ['brand', 'name']
    autocomplete_fields = ['parent']  # 부모 선택 시 검색 가능


@admin.register(UserItem)
class UserItemAdmin(admin.ModelAdmin):
    list_display = [
        'instrument', 'price', 'source', 'is_active', 
        'expired_at', 'click_count', 'created_at'
    ]
    list_filter = ['is_active', 'source', 'instrument__category']
    search_fields = ['instrument__name', 'instrument__brand', 'title']
    ordering = ['-created_at']
    readonly_fields = ['click_count', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('instrument')


@admin.register(SearchMissLog)
class SearchMissLogAdmin(admin.ModelAdmin):
    """미등록 검색어 관리 (자주 검색되지만 DB에 없는 악기)"""
    list_display = ['query', 'search_count', 'is_resolved', 'last_searched_at']
    list_filter = ['is_resolved']
    search_fields = ['query', 'normalized_query']
    ordering = ['-search_count']
    readonly_fields = ['query', 'normalized_query', 'search_count', 'created_at', 'last_searched_at']
    actions = ['mark_as_resolved']
    
    @admin.action(description="선택한 항목 처리 완료로 표시")
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True, resolved_at=timezone.now())
