"""
URL configuration for DAGU app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# ViewSet router
router = DefaultRouter()
router.register(r'instruments', views.InstrumentViewSet, basename='instrument')
router.register(r'items', views.UserItemViewSet, basename='useritem')

urlpatterns = [
    # Auth Check API (SSO)
    path('auth/check/', views.AuthCheckView.as_view(), name='auth-check'),

    # Search API
    path('search/', views.SearchView.as_view(), name='search'),

    # AI Description API (임시 비활성화)
    # path('ai/describe/', views.AIDescriptionView.as_view(), name='ai-describe'),

    # ViewSet routes
    path('', include(router.urls)),
]
