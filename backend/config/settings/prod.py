from .base import * # base.py의 모든 설정을 가져옴
import dj_database_url
import os

DEBUG = False

# =============================================================================
# 1. Host & Database
# =============================================================================
ALLOWED_HOSTS = [
    'malcha-dagu-7939098a2a2e.herokuapp.com',
    '.herokuapp.com',
]

# Heroku Postgres 연결
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# =============================================================================
# 2. React Integration (핵심)
# =============================================================================
# BASE_DIR은 'backend' 폴더입니다.
# React 빌드 폴더는 backend와 형제 위치인 'frontend/dist'에 있습니다.
FRONTEND_DIST = BASE_DIR.parent / 'frontend' / 'dist'

# (1) Template 경로 추가: Django가 index.html을 찾을 수 있게 함
TEMPLATES[0]['DIRS'] += [FRONTEND_DIST]

# (2) Static 경로 추가: Django가 리액트의 js, css, assets를 찾을 수 있게 함
STATICFILES_DIRS += [
    FRONTEND_DIST,
]

# WhiteNoise 설정 (정적 파일 압축 및 서빙)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# =============================================================================
# 3. Security & SSL
# =============================================================================
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'


# =============================================================================
# 4. Domain & CORS (Heroku 테스트용 수정)
# =============================================================================

# [주의] '.malchalab.com'으로 고정하면 헤로쿠 주소에서 로그인이 안 됩니다.
# 헤로쿠 테스트 중에는 주석 처리하여 현재 도메인(herokuapp.com)을 따르게 합니다.
# COOKIE_DOMAIN = '.malchalab.com'  <-- 나중에 실제 도메인 연결하면 주석 해제하세요.

# SIMPLE_JWT 설정 업데이트
# SIMPLE_JWT['AUTH_COOKIE_DOMAIN'] = COOKIE_DOMAIN <-- 주석 처리

SIMPLE_JWT['AUTH_COOKIE_SECURE'] = True
# SESSION_COOKIE_DOMAIN = COOKIE_DOMAIN <-- 주석 처리
# CSRF_COOKIE_DOMAIN = COOKIE_DOMAIN    <-- 주석 처리

# CORS 허용 도메인 (헤로쿠 주소 포함)
CORS_ALLOWED_ORIGINS = [
    'https://malchalab.com',
    'https://dagu.malchalab.com',
    'https://malcha-dagu-7939098a2a2e.herokuapp.com', # 이거 꼭 있어야 400 에러 안 남
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS


# =============================================================================
# 5. Redis (Heroku)
# =============================================================================
REDIS_URL = env('REDIS_URL', default=None)

if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }