@echo off
REM MALCHA-DAGU 개발 서버 실행 스크립트
REM 포트: 127.0.0.1:8001

cd /d "%~dp0backend"
python manage.py runserver 127.0.0.1:8001
