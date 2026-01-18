from .base import *

DEBUG = True

# 로컬호스트 모두 허용
ALLOWED_HOSTS = ['*']

# 개발용 SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# CORS: 개발용 프론트엔드 포트 허용
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True

# CSRF 신뢰
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# JWT Cookie (개발용 보안 완화)
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = False
SIMPLE_JWT['AUTH_COOKIE_DOMAIN'] = None # 로컬호스트는 도메인 설정 불필요

# Browsable API 활성화 (개발할 때 편함)
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
    'rest_framework.renderers.BrowsableAPIRenderer'
)

# 로컬 캐시 (Redis 없어도 돌아가게)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}