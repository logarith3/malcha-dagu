"""
Custom exception handling for MALCHA-DAGU API.
표준화된 에러 응답 형식 제공.
"""

import logging

from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    DRF 전역 예외 핸들러.

    표준화된 에러 응답 형식:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "사용자 친화적 메시지",
            "detail": "상세 정보 (개발용)"
        }
    }
    """
    # 기본 DRF 예외 핸들러 호출
    response = exception_handler(exc, context)

    # 요청 정보 로깅
    request = context.get('request')
    view = context.get('view')
    view_name = view.__class__.__name__ if view else 'Unknown'

    if response is not None:
        # DRF 예외 처리됨
        error_response = format_error_response(exc, response)
        response.data = error_response

        # 로깅 (500 에러는 ERROR, 그 외는 WARNING)
        if response.status_code >= 500:
            logger.error(
                f"API Error [{response.status_code}] {view_name}: {exc}",
                extra={'request': request}
            )
        else:
            logger.warning(
                f"API Warning [{response.status_code}] {view_name}: {exc}",
                extra={'request': request}
            )

        return response

    # DRF에서 처리되지 않은 예외
    if isinstance(exc, Http404):
        return Response(
            format_error_response(exc, None, code='NOT_FOUND', message='요청한 리소스를 찾을 수 없습니다.'),
            status=status.HTTP_404_NOT_FOUND
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            format_error_response(exc, None, code='PERMISSION_DENIED', message='권한이 없습니다.'),
            status=status.HTTP_403_FORBIDDEN
        )

    if isinstance(exc, ValidationError):
        return Response(
            format_error_response(exc, None, code='VALIDATION_ERROR', message='입력값이 올바르지 않습니다.'),
            status=status.HTTP_400_BAD_REQUEST
        )

    # 예상치 못한 예외 (500 에러)
    logger.exception(f"Unhandled exception in {view_name}: {exc}")
    return Response(
        {
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': '서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.',
            }
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )


def format_error_response(exc, response, code=None, message=None):
    """에러 응답 형식 표준화"""

    # Rate Limit 초과
    if isinstance(exc, Throttled):
        return {
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': f'요청이 너무 많습니다. {exc.wait}초 후에 다시 시도해주세요.',
                'retry_after': exc.wait,
            }
        }

    # 기본 에러 코드 추출
    if code is None:
        code = getattr(exc, 'default_code', 'ERROR')
        if hasattr(exc, 'status_code'):
            code = {
                400: 'BAD_REQUEST',
                401: 'UNAUTHORIZED',
                403: 'FORBIDDEN',
                404: 'NOT_FOUND',
                405: 'METHOD_NOT_ALLOWED',
                429: 'RATE_LIMIT_EXCEEDED',
                500: 'INTERNAL_ERROR',
            }.get(exc.status_code, code)

    # 메시지 추출
    if message is None:
        if hasattr(exc, 'detail'):
            message = str(exc.detail)
        else:
            message = str(exc)

    return {
        'error': {
            'code': code.upper() if isinstance(code, str) else 'ERROR',
            'message': message,
        }
    }
