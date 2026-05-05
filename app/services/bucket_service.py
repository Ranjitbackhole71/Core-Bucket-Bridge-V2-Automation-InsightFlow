"""
Bucket Service — Production Memory Layer (PROTECTED)

Append-only artifact storage with:
- Server-side hash computation
- Read-after-write verification
- Schema validation
- Hash chain integrity
- Thread-safe concurrent writes
- BRIDGE SIGNATURE VERIFICATION (non-bypassable)
"""
import json
import os
import hashlib
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple

from ..sarathi.bridge_signer import bridge_signer

logger = logging.getLogger("bucket_service")

BUCKET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
os.makedirs(BUCKET_DIR, exist_ok=True)
BUCKET_FILE = os.path.join(BUCKET_DIR, "bucket_artifacts.json")
CHAIN_FILE = os.path.join(BUCKET_DIR, "chain_state.json")


REQUIRED_ENVELOPE_FIELDS = [
    "artifact_id", "timestamp_utc", "schema_version",
    "source_module_id", "artifact_type", "parent_hash", "payload", "artifact_hash"
]

ALLOWED_ARTIFACT_TYPES = [
    "telemetry_record", "truth_event", "projection_event",
    "registry_snapshot", "policy_snapshot", "replay_proof",
]


class BucketUnauthorizedError(Exception):
    """Raised when write attempt lacks valid bridge signature."""
    pass


class BucketService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._lock = threading.Lock()
            self._ensure_files()

    def _ensure_files(self):
        if not os.path.exists(BUCKET_FILE):
            with open(BUCKET_FILE, "w", encoding="utf-8") as f:
                json.dump([], f)
        if not os.path.exists(CHAIN_FILE):
            with open(CHAIN_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_hash": None, "count": 0}, f)

    def get_latest_hash(self) -> Optional[str]:
        with self._lock:
            try:
                with open(CHAIN_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                return state.get("last_hash")
            except Exception:
                return None

    def get_all_artifacts(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._get_all_artifacts_internal()

    def _get_all_artifacts_internal(self) -> List[Dict[str, Any]]:
        if not os.path.exists(BUCKET_FILE):
            return []
        with open(BUCKET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_artifact_by_id(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._get_artifact_by_id_internal(artifact_id)

    def _get_artifact_by_id_internal(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        artifacts = self._get_all_artifacts_internal()
        for artifact in artifacts:
            if artifact.get("artifact_id") == artifact_id:
                return artifact
        return None

    def compute_hash(self, artifact: Dict[str, Any]) -> str:
        artifact_copy = {k: v for k, v in artifact.items() if k != "artifact_hash"}
        canonical = json.dumps(artifact_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def validate_schema(self, artifact: Dict[str, Any]) -> Tuple[bool, str]:
        for field in REQUIRED_ENVELOPE_FIELDS:
            if field not in artifact:
                return False, f"Missing required field: {field}"
        if artifact.get("artifact_type") not in ALLOWED_ARTIFACT_TYPES:
            return False, f"Invalid artifact_type: {artifact.get('artifact_type')}"
        if artifact.get("schema_version") != "1.0.0":
            return False, f"Invalid schema_version: {artifact.get('schema_version')}"
        return True, ""

    def write_artifact(
        self,
        artifact: Dict[str, Any],
        bridge_authorization: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if bridge_authorization is None:
            raise BucketUnauthorizedError(
                "Bucket write requires bridge_authorization — direct writes are blocked"
            )

        if not bridge_signer.verify(bridge_authorization):
            raise BucketUnauthorizedError("Invalid bridge authorization signature")

        if not bridge_signer.verify_timestamp(bridge_authorization):
            raise BucketUnauthorizedError("Bridge authorization expired")

        with self._lock:
            return self._write_artifact_internal(artifact)

    def _write_artifact_internal(self, artifact: Dict[str, Any]) -> Dict[str, Any]:
        valid, error = self.validate_schema(artifact)
        if not valid:
            raise ValueError(f"Schema validation failed: {error}")

        computed_hash = self.compute_hash(artifact)

        if "artifact_hash" in artifact and artifact["artifact_hash"] != computed_hash:
            raise ValueError(
                f"Client hash mismatch: expected {computed_hash}, got {artifact['artifact_hash']}"
            )

        if "artifact_hash" not in artifact:
            artifact["artifact_hash"] = computed_hash

        artifacts = self._get_all_artifacts_internal()

        chain_state = {}
        if os.path.exists(CHAIN_FILE):
            with open(CHAIN_FILE, "r", encoding="utf-8") as f:
                chain_state = json.load(f)

        expected_parent = chain_state.get("last_hash")
        provided_parent = artifact.get("parent_hash")
        if len(artifacts) == 0:
            if provided_parent is not None and provided_parent != "GENESIS":
                raise ValueError("First artifact must have parent_hash=null or 'GENESIS'")
        else:
            if provided_parent != expected_parent:
                raise ValueError(
                    f"Parent hash broken: expected {expected_parent}, got {provided_parent}"
                )

        artifacts.append(artifact)

        with open(BUCKET_FILE, "w", encoding="utf-8") as f:
            json.dump(artifacts, f, indent=2)

        chain_state["last_hash"] = computed_hash
        chain_state["count"] = len(artifacts)
        with open(CHAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(chain_state, f, indent=2)

        logger.info(f"[BUCKET] wrote artifact_id={artifact['artifact_id']} hash={computed_hash[:16]}...")

        return artifact

    def read_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._get_artifact_by_id_internal(artifact_id)

    def verify_write(self, artifact_id: str, expected_hash: str) -> Dict[str, Any]:
        with self._lock:
            return self._verify_write_internal(artifact_id, expected_hash)

    def _verify_write_internal(self, artifact_id: str, expected_hash: str) -> Dict[str, Any]:
        stored = self._get_artifact_by_id_internal(artifact_id)

        if stored is None:
            return {
                "verified_write": False,
                "reason": "artifact_not_found_after_write",
            }

        computed = self.compute_hash(stored)

        if computed != expected_hash:
            return {
                "verified_write": False,
                "reason": "hash_mismatch",
                "expected": expected_hash,
                "computed": computed,
            }

        schema_valid, schema_error = self.validate_schema(stored)
        if not schema_valid:
            return {
                "verified_write": False,
                "reason": f"schema_invalid: {schema_error}",
            }

        return {
            "verified_write": True,
            "artifact_id": artifact_id,
            "hash_match": True,
            "schema_valid": True,
        }


bucket_service = BucketService()
