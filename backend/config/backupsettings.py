"""
Django settings for MALCHA-DAGU project.
Production-ready configuration with environment variables.
"""

import os
from datetime import timedelta
from pathlib import Path

import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
)

# Read .env file if it exists
env_file = BASE_DIR.parent / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# =============================================================================
# Core Settings
# =============================================================================

# SSO: Malcha와 동일한 SECRET_KEY 사용 (JWT 서명 검증)
# 프로덕션에서는 SHARED_SECRET_KEY 환경변수 필수
SECRET_KEY = env('SHARED_SECRET_KEY', default=env('SECRET_KEY', default='django-insecure-dev-key-change-in-production'))
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# =============================================================================
# Application definition
# =============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',  # SSO: JWT 검증
    'corsheaders',
    # Local apps
    'dagu',
]

# Add celery beat if available (production)
try:
    import django_celery_beat
    INSTALLED_APPS.append('django_celery_beat')
except ImportError:
    pass

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # Must be before CommonMiddleware
    'django.middleware.security.SecurityMiddleware',
    'config.middleware.SecurityHeadersMiddleware',  # 커스텀 보안 헤더
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.RequestLoggingMiddleware',  # 보안 로깅
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# =============================================================================
# Database
# =============================================================================

# Use DATABASE_URL if available, otherwise default to SQLite for development
DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR / "db.sqlite3"}')
}

# =============================================================================
# Cache (Redis or Local Memory)
# =============================================================================

REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

# Use Redis if available, otherwise fallback to local memory cache
try:
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }
except ImportError:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# =============================================================================
# Celery Configuration
# =============================================================================

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Seoul'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# =============================================================================
# REST Framework
# =============================================================================

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # Rate Limiting (프로덕션 환경에서 API 남용 방지)
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',      # 비인증 사용자: 시간당 100회
        'user': '1000/hour',     # 인증 사용자: 시간당 1000회
        'search': '60/minute',   # 검색 API: 분당 60회
    },
    # 전역 예외 핸들러 (표준화된 에러 응답)
    'EXCEPTION_HANDLER': 'dagu.exceptions.custom_exception_handler',
}

# Add BrowsableAPI in debug mode
if DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
        'rest_framework.renderers.BrowsableAPIRenderer'
    )

# =============================================================================
# SSO: JWT 쿠키 인증 설정 (Malcha 발급 JWT 검증)
# =============================================================================

# 서브도메인 쿠키 공유를 위한 도메인 설정 (점(.) 접두사 필수)
COOKIE_DOMAIN = '.malchalab.com' if not DEBUG else None

# SimpleJWT 설정 (Malcha와 동일한 설정으로 검증)
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,  # Malcha와 동일한 키
    "AUTH_HEADER_TYPES": ("Bearer",),
    # SSO: Malcha가 발급한 쿠키명
    "AUTH_COOKIE": "malcha-access-token",
    "AUTH_COOKIE_DOMAIN": COOKIE_DOMAIN,
    "AUTH_COOKIE_SECURE": not DEBUG,
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",

    # SSO 보안: 토큰 발급자/수신자 검증 (Malcha 설정과 일치해야 함)
    "ISSUER": "malchalab.com",  # 토큰 발급자 검증
    "AUDIENCE": "dagu.malchalab.com",  # Dagu가 허용된 수신자인지 확인

    # 추가 보안 설정
    "JTI_CLAIM": "jti",
    "TOKEN_TYPE_CLAIM": "token_type",
    "USER_ID_CLAIM": "user_id",
}

# JWT 쿠키 인증 클래스 추가
REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = [
    'dagu.authentication.JWTCookieAuthentication',
]

# =============================================================================
# CORS Settings
# =============================================================================

# 환경 변수에서 CORS 도메인 로드 (쉼표로 구분)
# 예: CORS_ORIGINS=https://example.com,https://www.example.com
_cors_origins_env = env('CORS_ORIGINS', default='')
_cors_origins_from_env = [origin.strip() for origin in _cors_origins_env.split(',') if origin.strip()]

# 기본 개발 환경 도메인 + 환경 변수 도메인
CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:5173',
    'http://127.0.0.1:3000',
    'http://127.0.0.1:5173',
] + _cors_origins_from_env

# 프로덕션 환경에서는 개발 도메인 제거
if not DEBUG:
    CORS_ALLOWED_ORIGINS = _cors_origins_from_env if _cors_origins_from_env else CORS_ALLOWED_ORIGINS

CORS_ALLOW_CREDENTIALS = True

# CORS preflight 캐싱 (성능 최적화)
CORS_PREFLIGHT_MAX_AGE = 86400  # 24시간

# =============================================================================
# Password validation
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# =============================================================================
# Internationalization
# =============================================================================

LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

# =============================================================================
# Static files
# =============================================================================

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# =============================================================================
# Default primary key field type
# =============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# External API Keys
# =============================================================================

NAVER_CLIENT_ID = env('NAVER_CLIENT_ID', default='')
NAVER_CLIENT_SECRET = env('NAVER_CLIENT_SECRET', default='')
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')

# =============================================================================
# Security Settings (Production)
# =============================================================================

# SSO: 서브도메인 쿠키 공유
SESSION_COOKIE_DOMAIN = COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = COOKIE_DOMAIN

# CSRF 신뢰 출처 (SSO)
if DEBUG:
    CSRF_TRUSTED_ORIGINS = [
        'http://localhost:5173', 'http://127.0.0.1:5173',  # Malcha frontend
        'http://localhost:3000', 'http://127.0.0.1:3000',  # Dagu frontend
    ]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://malchalab.com',
        'https://www.malchalab.com',
        'https://dagu.malchalab.com',
    ]

if not DEBUG:
    # HTTPS 강제
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # HSTS (HTTP Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000  # 1년
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Cookie 보안
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True

    # XSS 방지
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Clickjacking 방지
    X_FRAME_OPTIONS = 'DENY'

# =============================================================================
# Logging
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
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
        'dagu': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'dagu.services': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'dagu.filters': {
            'handlers': ['console'],
            'level': 'DEBUG',  # 필터 탈락 로그 활성화
            'propagate': False,
        },
    },
}
