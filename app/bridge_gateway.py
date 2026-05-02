import hashlib
import json
import os
from fastapi import APIRouter
from typing import Dict, Any
from datetime import datetime

router = APIRouter()

# ============================================================
# ZERO-TRUST AUTHORITY TOKEN (env with hard fallback)
# ============================================================
_AUTHORITY_TOKEN = os.getenv("AUTHORITY_TOKEN", "valid_authority_bridge_key_2026")
_TOKEN_PREFIX = "valid_authority_"

def _classify_bad_token(token: str) -> str:
    """Distinguish invalid vs tampered.

    Tampered = structurally plausible token (correct prefix, reasonable length)
    that does not match the authority token.
    Invalid  = does not resemble a token at all.
    """
    if not isinstance(token, str):
        return "Invalid"
    if token.startswith(_TOKEN_PREFIX) and len(token) >= len(_TOKEN_PREFIX) + 4:
        return "Tampered"
    return "Invalid"

def _is_valid_authority(token: str) -> bool:
    """Strict equality check. No bypass possible."""
    if not isinstance(token, str):
        return False
    return token.strip() == _AUTHORITY_TOKEN

# ============================================================
# HELPER: build a compliant log entry
# ============================================================
def _log(status: str, reason: str, trace_id: Any, execution_id: Any, verified_write: bool = False) -> Dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "trace_id": str(trace_id) if trace_id is not None else "",
        "execution_id": str(execution_id) if execution_id is not None else "",
        "verified_write": verified_write,
    }

# ============================================================
# ENDPOINT
# ============================================================
@router.post("/validate_and_forward")
def validate_and_forward(request: Dict[str, Any]):

    execution_id = request.get("execution_id")
    trace_id = request.get("trace_id")
    authority_token = request.get("authority_token")
    payload = request.get("payload")

    # ============================================================
    # PHASE 1 — HARD BLOCKS (ZERO-TRUST)
    # ============================================================

    if not authority_token or (isinstance(authority_token, str) and authority_token.strip() == ""):
        return _log("BLOCKED", "Missing authority_token", trace_id, execution_id)

    if not _is_valid_authority(authority_token):
        classification = _classify_bad_token(authority_token)
        return _log("BLOCKED", f"{classification} authority_token", trace_id, execution_id)

    if not execution_id or not trace_id:
        return _log("BLOCKED", "Missing trace_id or execution_id", trace_id, execution_id)

    # ============================================================
    # PHASE 2 — BUCKET FORWARD + VERIFICATION
    # ============================================================

    verified_write = False
    artifact_hash = None

    try:
        from app.services.bucket_store import get_all_artifacts
        from app.services.hash_service import compute_artifact_hash
        from app.services.bucket_service import store_artifact

        # Provenance chain
        all_artifacts = get_all_artifacts()
        parent_hash = all_artifacts[-1].get("artifact_hash") if all_artifacts else None

        timestamp = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

        # Build artifact (no intelligence, only structure)
        artifact = {
            "artifact_id": f"artifact-{execution_id}",
            "artifact_type": "telemetry_record",
            "schema_version": "1.0.0",
            "source_module_id": "bridge_gateway",
            "timestamp_utc": timestamp,
            "parent_hash": parent_hash,
            "payload": payload,
        }

        artifact_hash = compute_artifact_hash(artifact)
        artifact["artifact_hash"] = artifact_hash

        # Write to bucket
        stored = store_artifact(artifact)

        # Read-after-write verification
        returned_hash = stored.get("artifact_hash") if stored else None
        verified_write = (returned_hash == artifact_hash)

    except ImportError as e:
        return _log("BLOCKED", f"Bucket service unavailable: {str(e)}", trace_id, execution_id)

    except Exception as e:
        return _log("BLOCKED", f"Bucket write failed: {str(e)}", trace_id, execution_id)

    # ============================================================
    # PHASE 3 — FINAL RESPONSE
    # ============================================================

    if not verified_write:
        return _log("BLOCKED", "Read-after-write verification failed", trace_id, execution_id)

    result = _log("FORWARDED", "Valid authority, artifact verified", trace_id, execution_id, verified_write=True)
    result["artifact_hash"] = artifact_hash
    return result