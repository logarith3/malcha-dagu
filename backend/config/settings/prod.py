from .base import *
import dj_database_url

DEBUG = False

# Heroku 도메인 추가 (앱 이름 바뀌면 수정 필요)
ALLOWED_HOSTS = ['malcha-dagu.herokuapp.com', 'dagu.malchalab.com']

# [DB] Heroku Postgres 연결 (DATABASE_URL 환경변수 자동 사용)
DATABASES = {
    'default': dj_database_url.config(conn_max_age=600, ssl_require=True)
}

# [React 통합] 프론트엔드 빌드 결과물(dist) 연결
# 주의: package.json에서 빌드한 위치가 frontend/dist 라고 가정
FRONTEND_DIST = BASE_DIR / '../frontend/dist'

# 1. 템플릿 경로에 추가 (index.html 찾기 위함)
TEMPLATES[0]['DIRS'] += [FRONTEND_DIST]

# 2. 정적 파일 경로에 추가 (js, css 찾기 위함)
STATICFILES_DIRS = [
    FRONTEND_DIST,
]

# [Static] WhiteNoise 압축 및 캐싱 최적화
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# [Security] 보안 강화
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

# [SSO] 도메인 쿠키 설정
COOKIE_DOMAIN = '.malchalab.com'
SIMPLE_JWT['AUTH_COOKIE_DOMAIN'] = COOKIE_DOMAIN
SIMPLE_JWT['AUTH_COOKIE_SECURE'] = True
SESSION_COOKIE_DOMAIN = COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = COOKIE_DOMAIN

# [CORS] 실제 운영 도메인만 허용
CORS_ALLOWED_ORIGINS = [
    'https://malchalab.com',
    'https://dagu.malchalab.com',
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# [Redis] Heroku Redis 연결
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}