"""
WSGI config for config project.
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# [추가됨] 현재 파일(wsgi.py)의 2단계 상위 폴더(backend)를 경로에 추가
# 이렇게 해야 'config.settings'를 찾을 수 있습니다.
path = Path(__file__).resolve().parent.parent
if str(path) not in sys.path:
    sys.path.append(str(path))

# [기존 설정 유지]
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

application = get_wsgi_application()