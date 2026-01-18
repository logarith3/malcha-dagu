"""
URL configuration for MALCHA-DAGU project.
"""
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView

urlpatterns = [
    # 1. 관리자 및 API 주소 (먼저 검사)
    path('malcha_admin_site/', admin.site.urls),
    path('api/', include('dagu.urls')),

    # 2. 리액트 연동 (위 주소 외 모든 요청은 index.html로 보냄)
    # 이렇게 해야 새로고침 했을 때 404가 안 뜨고 리액트 라우터가 작동합니다.
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]