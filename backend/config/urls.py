"""
URL configuration for MALCHA-DAGU project.
"""
from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

import os

urlpatterns = [
    # 1. 관리자 및 API 주소 (먼저 검사)
    path(os.getenv('ADMIN_URL', 'malcha_admin_site/'), admin.site.urls),
    path('api/', include('dagu.urls')),
]

# 2. 리액트 연동 (프로덕션에서만)
# 로컬 개발 시에는 React dev server가 별도로 돌아가므로 필요 없음
if not settings.DEBUG:
    urlpatterns += [
        re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
    ]