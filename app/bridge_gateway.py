import hashlib
import json
import os
from fastapi import APIRouter
from typing import Dict, Any 
from datetime import datetime

router = APIRouter()

# ============================================================
# ZERO-TRUST AUTHORITY TOKEN (from environment)
# ============================================================
_AUTHORITY_TOKEN = os.getenv("AUTHORITY_TOKEN")

def _compute_token_integrity(token: str) -> str:
    """SHA-256 of the token for logging/debug only."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def _is_valid_authority(token: str) -> bool:
    """Strict equality check. No bypass possible."""
    if not isinstance(token, str):
        return False

    token = token.strip()

    if not _AUTHORITY_TOKEN:
        return False

    return token == _AUTHORITY_TOKEN

# ============================================================
# HELPER: build a compliant log entry
# ============================================================
def _block_log(status: str, reason: str, trace_id: Any, execution_id: Any) -> Dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "trace_id": str(trace_id) if trace_id is not None else "",
        "execution_id": str(execution_id) if execution_id is not None else "",
        "verified_write": False,
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
        return _block_log("BLOCKED", "Missing authority_token", trace_id, execution_id)

    if not _is_valid_authority(authority_token):
        return _block_log("BLOCKED", "Invalid authority_token", trace_id, execution_id)

    if not execution_id or not trace_id:
        return _block_log("BLOCKED", "Missing trace_id or execution_id", trace_id, execution_id)

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

        # Hash from bucket logic
        artifact_hash = compute_artifact_hash(artifact)
        artifact["artifact_hash"] = artifact_hash

        # Write to bucket
        stored = store_artifact(artifact)

        # Read-after-write verification
        returned_hash = stored.get("artifact_hash") if stored else None
        verified_write = (returned_hash == artifact_hash)

    except ImportError as e:
        return _block_log("BLOCKED", f"Bucket service unavailable: {str(e)}", trace_id, execution_id)

    except Exception as e:
        return _block_log("BLOCKED", f"Bucket write failed: {str(e)}", trace_id, execution_id)

    # ============================================================
    # PHASE 3 — FINAL RESPONSE
    # ============================================================

    if not verified_write:
        return _block_log("BLOCKED", "Read-after-write verification failed", trace_id, execution_id)

    return {
        "status": "FORWARDED",
        "reason": "Valid authority, artifact verified",
        "trace_id": trace_id,
        "execution_id": execution_id,
        "verified_write": True,
        "artifact_hash": artifact_hash,
    }