from django.core.management.base import BaseCommand
from django.conf import settings
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenError
import jwt

class Command(BaseCommand):
    help = 'Debug JWT token validation'

    def add_arguments(self, parser):
        parser.add_argument('token', type=str, help='The JWT token to verify')

    def handle(self, *args, **options):
        token = options['token']
        self.stdout.write(self.style.HTTP_INFO(f"Testing token: {token[:20]}..."))
        
        # 1. Print Config
        simple_jwt = getattr(settings, 'SIMPLE_JWT', {})
        self.stdout.write(f"ALGORITHM: {simple_jwt.get('ALGORITHM')}")
        self.stdout.write(f"SIGNING_KEY (first 10): {simple_jwt.get('SIGNING_KEY')[:10]}...")
        self.stdout.write(f"AUDIENCE: {simple_jwt.get('AUDIENCE')}")
        self.stdout.write(f"ISSUER: {simple_jwt.get('ISSUER')}")

        # 2. Manual Decode with PyJWT (to see content)
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            self.stdout.write(self.style.SUCCESS(f"Payload (Unverified): {payload}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to decode payload: {e}"))

        # 3. Validation via TokenBackend (What SimpleJWT does)
        try:
            algorithm = simple_jwt.get('ALGORITHM', 'HS256')
            signing_key = simple_jwt.get('SIGNING_KEY')
            audience = simple_jwt.get('AUDIENCE')
            issuer = simple_jwt.get('ISSUER')
            
            # SimpleJWT backend
            token_backend = TokenBackend(algorithm, signing_key, audience=audience, issuer=issuer)
            
            valid_data = token_backend.decode(token, verify=True)
            self.stdout.write(self.style.SUCCESS(f"VALIDATION SUCCESS! Data: {valid_data}"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"VALIDATION FAILED: {type(e).__name__}: {e}"))
            
            # 4. Try to find WHY it failed
            # Check signature manually
            try:
                jwt.decode(token, signing_key, algorithms=[algorithm], options={"verify_aud": False, "verify_iss": False})
                self.stdout.write("-> Signature is VALID. Problem is claims (exp, aud, iss).")
            except jwt.InvalidSignatureError:
                self.stdout.write("-> Signature is INVALID. Keys do not match.")
            except jwt.ExpiredSignatureError:
                self.stdout.write("-> Token is EXPIRED.")
            except Exception as inner_e:
                self.stdout.write(f"-> Other error during manual check: {inner_e}")
