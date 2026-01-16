"""
SSO JWT Cookie Authentication for MALCHA-DAGU.
Validates JWT tokens issued by Malcha (malchalab.com) from cookies.

Security Features:
- Issuer (iss) 검증: malchalab.com에서 발급된 토큰만 허용
- Audience (aud) 검증: dagu.malchalab.com이 수신자인 토큰만 허용
- Lazy User Sync: 유효한 토큰이면 Dagu DB에 자동 사용자 생성
- 상세 보안 로깅
"""

import logging
import time
from functools import lru_cache

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError, AuthenticationFailed

logger = logging.getLogger(__name__)
User = get_user_model()

# 인증 실패 추적용 캐시 키 prefix
AUTH_FAIL_CACHE_PREFIX = 'sso_auth_fail:'
AUTH_FAIL_THRESHOLD = 10  # 10회 실패
AUTH_FAIL_WINDOW = 300  # 5분


class JWTCookieAuthentication(JWTAuthentication):
    """
    Malcha에서 발급한 JWT 쿠키를 읽어 인증하는 클래스.

    SSO 구조:
    - Malcha (malchalab.com): JWT 발급 (Auth Server)
    - Dagu (dagu.malchalab.com): JWT 검증 (Resource Server)

    보안 기능:
    - Issuer/Audience claim 검증 (settings에서 자동 처리)
    - 인증 실패 Rate Limiting (IP 기반)
    - Lazy User Sync (유효한 토큰만)
    - 상세 보안 로깅
    """

    def authenticate(self, request):
        """
        쿠키에서 JWT access token을 추출하여 검증.

        Returns:
            tuple: (user, validated_token) 인증 성공 시
            None: 쿠키에 토큰이 없을 때

        Raises:
            AuthenticationFailed: Rate limit 초과 시
        """
        # 설정에서 쿠키명 가져오기
        cookie_name = getattr(settings, 'SIMPLE_JWT', {}).get('AUTH_COOKIE', 'malcha-access-token')

        # 쿠키에서 access token 추출
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            return None

        # Rate Limiting 체크 (IP 기반)
        client_ip = self._get_client_ip(request)
        if self._is_rate_limited(client_ip):
            logger.warning(f"SSO rate limit exceeded for IP: {client_ip}")
            raise AuthenticationFailed('Too many authentication attempts. Please try again later.')

        try:
            # 토큰 검증 (서명, 만료, iss, aud 등 - SimpleJWT가 자동 처리)
            validated_token = self.get_validated_token(raw_token)

            # 추가 보안 검증
            self._validate_token_claims(validated_token)

            # 토큰에서 사용자 정보 추출 또는 생성
            user = self._get_or_create_user(validated_token)

            if user:
                # 인증 성공 시 실패 카운터 리셋
                self._reset_fail_count(client_ip)
                logger.info(f"SSO authentication successful: user_id={user.id}, ip={client_ip}")
                return user, validated_token
            else:
                self._record_auth_failure(client_ip, "user_creation_failed")
                return None

        except TokenError as e:
            self._record_auth_failure(client_ip, f"token_error: {e}")
            logger.warning(f"SSO token validation failed: {e} (ip={client_ip})")
            return None
        except AuthenticationFailed:
            raise  # Rate limit 에러는 그대로 전달
        except Exception as e:
            self._record_auth_failure(client_ip, f"unexpected_error: {e}")
            logger.error(f"SSO authentication error: {e} (ip={client_ip})")
            return None

    def _get_client_ip(self, request) -> str:
        """클라이언트 IP 추출 (프록시 고려)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _is_rate_limited(self, client_ip: str) -> bool:
        """인증 실패 Rate Limiting 체크"""
        cache_key = f"{AUTH_FAIL_CACHE_PREFIX}{client_ip}"
        fail_count = cache.get(cache_key, 0)
        return fail_count >= AUTH_FAIL_THRESHOLD

    def _record_auth_failure(self, client_ip: str, reason: str):
        """인증 실패 기록"""
        cache_key = f"{AUTH_FAIL_CACHE_PREFIX}{client_ip}"
        fail_count = cache.get(cache_key, 0) + 1
        cache.set(cache_key, fail_count, AUTH_FAIL_WINDOW)
        logger.warning(f"SSO auth failure recorded: ip={client_ip}, count={fail_count}, reason={reason}")

    def _reset_fail_count(self, client_ip: str):
        """인증 성공 시 실패 카운터 리셋"""
        cache_key = f"{AUTH_FAIL_CACHE_PREFIX}{client_ip}"
        cache.delete(cache_key)

    def _validate_token_claims(self, validated_token):
        """
        추가 토큰 클레임 검증.
        SimpleJWT가 iss/aud는 자동 검증하므로 여기서는 추가 검증만 수행.
        """
        # token_type 검증 (access 토큰만 허용)
        token_type = validated_token.get('token_type')
        if token_type != 'access':
            raise TokenError(f"Invalid token type: {token_type}")

        # user_id 존재 여부 확인
        user_id = validated_token.get('user_id')
        if not user_id:
            raise TokenError("Missing user_id claim")

        # jti (JWT ID) 존재 여부 확인 (블랙리스트 체크용)
        jti = validated_token.get('jti')
        if not jti:
            logger.warning("Token missing jti claim - blacklist check unavailable")

    def _get_or_create_user(self, validated_token):
        """
        토큰에서 사용자 조회 또는 생성 (Lazy Sync).

        Malcha의 user_id를 사용하여 Dagu DB에서 조회.
        없으면 자동 생성.

        보안 고려사항:
        - user_id 타입 검증 (정수만 허용)
        - 생성 시 최소 권한만 부여
        - 상세 로깅
        """
        try:
            # 기본 방식으로 사용자 조회 시도
            return self.get_user(validated_token)
        except Exception:
            pass

        # 사용자가 없으면 토큰에서 정보 추출하여 생성
        try:
            user_id = validated_token.get('user_id')
            if not user_id:
                logger.warning("SSO token missing user_id claim")
                return None

            # user_id 타입 검증 (정수만 허용 - injection 방지)
            if not isinstance(user_id, int):
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError):
                    logger.error(f"SSO invalid user_id type: {type(user_id)}")
                    return None

            # user_id 범위 검증 (음수 방지)
            if user_id <= 0:
                logger.error(f"SSO invalid user_id value: {user_id}")
                return None

            # Malcha user_id로 Dagu DB에 사용자 생성/조회
            user, created = User.objects.get_or_create(
                id=user_id,
                defaults={
                    'username': f'malcha_user_{user_id}',
                    'is_active': True,
                    # 보안: staff/superuser 권한 부여 안함
                    'is_staff': False,
                    'is_superuser': False,
                }
            )

            if created:
                logger.info(f"SSO: Created new user in Dagu DB (id={user_id})")
            else:
                logger.debug(f"SSO: Found existing user in Dagu DB (id={user_id})")

            return user

        except Exception as e:
            logger.error(f"SSO user sync failed: {e}")
            return None
