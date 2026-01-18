"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# [수정됨] 기본 설정 경로를 'config.settings.prod'로 변경
# Heroku에서 Gunicorn이 실행될 때 이 배포용 설정을 불러오게 됩니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

application = get_wsgi_application()