"""
Sarathi — Internal Bridge Signature

Provides HMAC-SHA256 signatures for inter-service authorization.
Used by Bridge to sign execution results before Bucket write.
Used by Bucket to verify the request originated from Bridge.
Used by Execution System to verify the caller has valid authority.
"""
import os
import hmac
import hashlib
import time
import json
from typing import Dict, Any, Optional

BRIDGE_SECRET_ENV = "TANTRA_BRIDGE_SECRET"

def _get_secret() -> bytes:
    secret = os.environ.get(BRIDGE_SECRET_ENV)
    if not secret:
        secret = "tantra-bridge-hmac-secret-do-not-hardcode-in-prod"
    return secret.encode("utf-8")


class BridgeSigner:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._secret = _get_secret()

    def sign(self, data: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = int(time.time())
        payload = {
            "trace_id": data.get("trace_id", ""),
            "execution_id": data.get("execution_id", ""),
            "timestamp": timestamp,
            "nonce": os.urandom(16).hex(),
        }

        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(self._secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        return {
            **payload,
            "signature": signature,
        }

    def verify(self, data: Dict[str, Any]) -> bool:
        if not data.get("signature"):
            return False

        provided_sig = data.pop("signature")

        expected_payload = {
            "trace_id": data.get("trace_id", ""),
            "execution_id": data.get("execution_id", ""),
            "timestamp": data.get("timestamp"),
            "nonce": data.get("nonce"),
        }

        canonical = json.dumps(expected_payload, sort_keys=True, separators=(",", ":"))
        expected_sig = hmac.new(self._secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()

        data["signature"] = provided_sig

        return hmac.compare_digest(provided_sig, expected_sig)

    def verify_timestamp(self, data: Dict[str, Any], max_age_seconds: int = 60) -> bool:
        timestamp = data.get("timestamp")
        if timestamp is None:
            return False
        return (time.time() - int(timestamp)) <= max_age_seconds


bridge_signer = BridgeSigner()
