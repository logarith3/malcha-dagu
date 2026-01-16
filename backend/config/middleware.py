"""
Security middleware for MALCHA-DAGU.
Adds additional security headers to all responses.
"""

import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """
    추가 보안 헤더를 모든 응답에 추가하는 미들웨어.

    추가되는 헤더:
    - X-Content-Type-Options: nosniff (MIME 타입 스니핑 방지)
    - X-Frame-Options: DENY (클릭재킹 방지)
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: 불필요한 브라우저 기능 비활성화
    - Cache-Control: API 응답 캐시 방지 (민감한 데이터)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # MIME 타입 스니핑 방지
        response['X-Content-Type-Options'] = 'nosniff'

        # 클릭재킹 방지 (iframe 삽입 차단)
        response['X-Frame-Options'] = 'DENY'

        # Referrer 정책 (외부 사이트에 URL 노출 제한)
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permissions-Policy (불필요한 브라우저 API 비활성화)
        response['Permissions-Policy'] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # API 응답은 캐시하지 않음 (민감한 데이터 보호)
        if request.path.startswith('/api/'):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
            response['Pragma'] = 'no-cache'

        return response


class RequestLoggingMiddleware:
    """
    보안 모니터링을 위한 요청 로깅 미들웨어.

    로깅 항목:
    - 인증 실패 요청
    - 의심스러운 요청 패턴
    - Rate limit 근접 요청
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 인증 실패 응답 로깅 (401, 403)
        if response.status_code in [401, 403]:
            client_ip = self._get_client_ip(request)
            logger.warning(
                f"Auth failure: {request.method} {request.path} "
                f"status={response.status_code} ip={client_ip} "
                f"user_agent={request.META.get('HTTP_USER_AGENT', 'unknown')[:100]}"
            )

        # Rate limit 응답 로깅 (429)
        if response.status_code == 429:
            client_ip = self._get_client_ip(request)
            logger.warning(
                f"Rate limit exceeded: {request.method} {request.path} "
                f"ip={client_ip}"
            )

        return response

    def _get_client_ip(self, request) -> str:
        """클라이언트 IP 추출 (프록시 고려)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')
