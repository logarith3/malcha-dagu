"""
Admin configuration for MALCHA-DAGU.
"""

from django.contrib import admin

from .models import Instrument, UserItem


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ['brand', 'name', 'category', 'reference_price', 'created_at']
    list_filter = ['category', 'brand']
    search_fields = ['name', 'brand']
    ordering = ['brand', 'name']


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
