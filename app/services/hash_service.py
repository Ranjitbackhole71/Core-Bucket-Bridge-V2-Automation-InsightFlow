import hashlib
import json


def compute_artifact_hash(artifact: dict) -> str:
    """SHA-256 hex digest of the canonical JSON representation of an artifact."""
    canonical = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
