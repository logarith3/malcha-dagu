from .base import *

DEBUG = True

# 로컬호스트 모두 허용
ALLOWED_HOSTS = ['*']

# 개발용 SQLite 데이터베이스 사용
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
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# JWT Cookie (개발용 보안 완화)
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = False
SIMPLE_JWT['AUTH_COOKIE_DOMAIN'] = None

# Browsable API 활성화 (개발할 때 편함)
if 'rest_framework' in INSTALLED_APPS:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
        'rest_framework.renderers.BrowsableAPIRenderer'
    )

# 로컬 캐시 (Redis 없이 메모리 사용)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# =========================================================
# [중요] 네이버 API 키 강제 설정 (따옴표 안에 키를 넣으세요)
# =========================================================
NAVER_CLIENT_ID = 'MQM3ivXPDTKYHxTNCxie'
NAVER_CLIENT_SECRET = 'e0rnqffhai'

# =============================================================================
# 로컬 개발용 로깅 설정
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {asctime} {name} {message}',
            'style': '{',
        },
        'simple': {
            'format': '[{levelname}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dagu': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}