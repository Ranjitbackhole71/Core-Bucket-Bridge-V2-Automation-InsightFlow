"""
Sarathi — Authority Validator

Cryptographic authority validation layer.
Accepts JWT tokens signed with RSA private key.
Validates: signature, expiry, issuer, audience, replay attacks.

HARD FAIL on any violation. No bypass possible.
"""
import jwt
import time
import logging
from typing import Dict, Any, Optional, Tuple
from cryptography.hazmat.primitives import serialization

from .key_manager import sarathi_keys
from .replay_detector import replay_detector

logger = logging.getLogger("sarathi_authority")

SARATHI_ISSUER = "tantra-sarathi"
SARATHI_ALGORITHM = "RS256"
SARATHI_CLOCK_SKEW = 30
SARATHI_AUDIENCE = "tantra-bridge"


class SarathiValidationError(Exception):
    def __init__(self, reason: str, code: str):
        self.reason = reason
        self.code = code
        super().__init__(self.reason)


class SarathiAuthority:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def validate_token(self, authority_token: str) -> Dict[str, Any]:
        if not authority_token or not isinstance(authority_token, str) or authority_token.strip() == "":
            raise SarathiValidationError("Missing authority_token", "MISSING_TOKEN")

        token = authority_token.strip()

        public_key_pem = sarathi_keys.get_public_key_pem()

        try:
            payload = jwt.decode(
                token,
                public_key_pem,
                algorithms=[SARATHI_ALGORITHM],
                issuer=SARATHI_ISSUER,
                audience=SARATHI_AUDIENCE,
                options={
                    "require_exp": True,
                    "require_iat": True,
                    "require_iss": True,
                    "require_aud": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
                leeway=SARATHI_CLOCK_SKEW,
            )
        except jwt.ExpiredSignatureError:
            raise SarathiValidationError("Token expired", "EXPIRED_TOKEN")
        except jwt.InvalidIssuerError:
            raise SarathiValidationError("Invalid token issuer", "INVALID_ISSUER")
        except jwt.InvalidSignatureError:
            raise SarathiValidationError("Token signature invalid", "INVALID_SIGNATURE")
        except jwt.InvalidTokenError as e:
            raise SarathiValidationError(f"Token invalid: {str(e)}", "INVALID_TOKEN")

        jti = payload.get("jti")
        if not jti:
            raise SarathiValidationError("Token missing jti claim", "MISSING_JTI")

        if replay_detector.is_replayed(jti):
            raise SarathiValidationError("Token replay detected", "REPLAY_ATTACK")

        replay_detector.mark_used(jti)
        replay_detector.cleanup_expired()

        logger.info(f"[SARATHI] authority validated jti={jti}")

        return payload

    def issue_token(
        self,
        subject: str = "tantra-core",
        audience: str = "tantra-bridge",
        ttl_seconds: int = 300,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        import uuid

        now = int(time.time())
        jti = str(uuid.uuid4())

        payload = {
            "iss": SARATHI_ISSUER,
            "sub": subject,
            "aud": audience,
            "iat": now,
            "exp": now + ttl_seconds,
            "jti": jti,
        }

        if extra_claims:
            for key in ("trace_id", "execution_id", "scope"):
                if key in extra_claims:
                    payload[key] = extra_claims[key]

        private_key = sarathi_keys.get_private_key()
        token = jwt.encode(payload, private_key, algorithm=SARATHI_ALGORITHM)

        logger.info(f"[SARATHI] token issued jti={jti} ttl={ttl_seconds}s")

        return token


sarathi_authority = SarathiAuthority()
