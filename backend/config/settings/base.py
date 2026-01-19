import os
from pathlib import Path
from datetime import timedelta
import environ

# =============================================================================
# 1. Path Setup
# =============================================================================
# backend/config/settings/base.py 위치 기준 -> 3단계 위가 backend 폴더
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# environ 초기화
env = environ.Env()
# .env 파일이 있으면 로드 (로컬 개발용)
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# =============================================================================
# 2. Core Config
# =============================================================================
SECRET_KEY = env('SHARED_SECRET_KEY', default=env('SECRET_KEY', default='django-insecure-dev-key'))

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third-party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # 'django_celery_beat', # 필요시 주석 해제
    # Local apps
    'dagu',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # [필수] 정적 파일 서빙
    'config.middleware.SecurityHeadersMiddleware', # 커스텀 미들웨어 (파일 존재 확인 필요)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'config.middleware.RequestLoggingMiddleware', # 필요시 주석 해제
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # 기본 템플릿 폴더
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
# 3. Static & I18N
# =============================================================================
LANGUAGE_CODE = 'ko-kr'
TIME_ZONE = 'Asia/Seoul'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# prod.py에서 extend 하기 위해 미리 정의
STATICFILES_DIRS = []

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# 4. REST Framework & JWT
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
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour',
        'search': '60/minute',
    },
    # 파일이 실제로 존재하는지 확인하고, 없다면 주석 처리하세요.
    'EXCEPTION_HANDLER': 'dagu.exceptions.custom_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'dagu.authentication.JWTCookieAuthentication',
    ],
}

# SSO JWT 설정
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_COOKIE": "malcha-access-token",
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Lax",
    "ISSUER": "malchalab.com",
    # AUDIENCE 자동 검증 비활성화 (authentication.py에서 수동 검증)
    # SimpleJWT가 배열 audience 처리를 제대로 못함
    # "AUDIENCE": ["malchalab.com", "dagu.malchalab.com"],
    "JTI_CLAIM": "jti",
    "TOKEN_TYPE_CLAIM": "token_type",
    "USER_ID_CLAIM": "user_id",
}

# =============================================================================
# 5. External API Keys
# =============================================================================
NAVER_CLIENT_ID = env('NAVER_CLIENT_ID', default='')
NAVER_CLIENT_SECRET = env('NAVER_CLIENT_SECRET', default='')
OPENAI_API_KEY = env('OPENAI_API_KEY', default='')