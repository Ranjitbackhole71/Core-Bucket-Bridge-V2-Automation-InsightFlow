"""
Hash Service — Deterministic SHA-256 artifact hashing.

Computes canonical hash excluding the self-referential artifact_hash field.
"""
import hashlib
import json
from typing import Dict, Any


def compute_artifact_hash(artifact: Dict[str, Any]) -> str:
    artifact_copy = {k: v for k, v in artifact.items() if k != "artifact_hash"}
    canonical = json.dumps(artifact_copy, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def verify_artifact_hash(artifact: Dict[str, Any]) -> bool:
    if "artifact_hash" not in artifact:
        return False
    return compute_artifact_hash(artifact) == artifact["artifact_hash"]
