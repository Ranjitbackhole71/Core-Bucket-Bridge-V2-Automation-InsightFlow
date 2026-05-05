"""
Bridge — Non-Bypassable Execution Gate (HARDENED)

STRICT FLOW: Core -> Sarathi -> Bridge -> Execution System -> Bucket -> Response

HARDENING:
- Cryptographic authority validation (Sarathi JWT) BEFORE anything else
- Bridge signs every inter-service call (HMAC-SHA256)
- Execution System validates bridge signature
- Bucket Service validates bridge signature
- Reject invalid requests immediately
- Forward to execution system AFTER validation
- NEVER call Bucket before execution
- NEVER generate trace_id or execution_id
- NEVER bypass execution layer
- Idempotency enforcement (execution_id uniqueness)
- Trace immutability verification
"""
import logging
import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from ..sarathi.authority import sarathi_authority, SarathiValidationError
from ..sarathi.bridge_signer import bridge_signer
from ..execution.system import execution_system, ExecutionError
from .bucket_service import bucket_service, BucketUnauthorizedError
from .hash_service import compute_artifact_hash, verify_artifact_hash

logger = logging.getLogger("tantra_bridge")


class BridgeNonBypassError(Exception):
    """Raised when bridge invariant is violated."""
    pass


IDEMPOTENCY_FILE = None

def _get_idempotency_file() -> str:
    global IDEMPOTENCY_FILE
    if IDEMPOTENCY_FILE is None:
        data_dir = __import__("os").path.join(
            __import__("os").path.dirname(__import__("os").path.dirname(__import__("os").path.dirname(__file__))),
            "data"
        )
        __import__("os").makedirs(data_dir, exist_ok=True)
        IDEMPOTENCY_FILE = __import__("os").path.join(data_dir, "idempotency_store.json")
    return IDEMPOTENCY_FILE


class TantraBridge:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True

    def process(
        self,
        trace_id: str,
        execution_id: str,
        authority_token: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        return self._validate_authority(
            trace_id, execution_id, authority_token, payload
        )

    def _validate_authority(
        self,
        trace_id: str,
        execution_id: str,
        authority_token: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not trace_id or trace_id.strip() == "":
            return self._blocked_response("Missing trace_id", "MISSING_TRACE_ID", trace_id, execution_id)
        if not execution_id or execution_id.strip() == "":
            return self._blocked_response("Missing execution_id", "MISSING_EXECUTION_ID", trace_id, execution_id)

        try:
            sarathi_payload = sarathi_authority.validate_token(authority_token)
        except SarathiValidationError as e:
            logger.error(f"[BRIDGE] authority rejected code={e.code} reason={e.reason}")
            return self._blocked_response(e.reason, e.code, trace_id, execution_id)
        except Exception as e:
            logger.error(f"[BRIDGE] authority validation crash: {e}")
            return self._blocked_response(
                "authority_validation_error", "AUTH_CRASH", trace_id, execution_id
            )

        return self._execute(
            trace_id, execution_id, sarathi_payload, payload
        )

    def _execute(
        self,
        trace_id: str,
        execution_id: str,
        sarathi_payload: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        idempotent_result = self._check_idempotency(trace_id, execution_id)
        if idempotent_result is not None:
            logger.info(f"[BRIDGE] idempotent hit execution_id={execution_id}")
            return idempotent_result

        bridge_auth = bridge_signer.sign({
            "trace_id": trace_id,
            "execution_id": execution_id,
        })

        try:
            exec_result = execution_system.execute(
                trace_id=trace_id,
                execution_id=execution_id,
                payload=payload,
                bridge_authorization=bridge_auth,
            )
        except ExecutionError as e:
            logger.error(f"[BRIDGE] execution failed code={e.code} reason={e.reason}")
            return self._blocked_response(e.reason, e.code, trace_id, execution_id)
        except Exception as e:
            logger.error(f"[BRIDGE] execution crash: {e}")
            return self._blocked_response(
                "execution_system_error", "EXEC_CRASH", trace_id, execution_id
            )

        return self._persist_to_bucket(
            trace_id, execution_id, exec_result, payload
        )

    def _persist_to_bucket(
        self,
        trace_id: str,
        execution_id: str,
        exec_result: Dict[str, Any],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            parent_hash = bucket_service.get_latest_hash()
            if parent_hash is None:
                parent_hash = "GENESIS"

            timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat() + "Z"

            artifact = {
                "artifact_id": f"artifact-{execution_id}",
                "timestamp_utc": timestamp,
                "schema_version": "1.0.0",
                "source_module_id": "tantra-bridge",
                "artifact_type": "telemetry_record",
                "parent_hash": parent_hash,
                "execution_id": execution_id,
                "trace_id": trace_id,
                "payload": {
                    "execution_result": exec_result["result"],
                    "result_hash": exec_result["result_hash"],
                    "original_payload": payload,
                },
            }

            artifact_hash = compute_artifact_hash(artifact)
            artifact["artifact_hash"] = artifact_hash

            bucket_bridge_auth = bridge_signer.sign({
                "trace_id": trace_id,
                "execution_id": execution_id,
            })

            stored = bucket_service.write_artifact(
                artifact,
                bridge_authorization=bucket_bridge_auth,
            )

            verification = bucket_service.verify_write(
                artifact_id=stored["artifact_id"],
                expected_hash=artifact_hash,
            )

            if verification["verified_write"]:
                logger.info(
                    f"[BRIDGE] verified_write=true artifact_id={stored['artifact_id']} "
                    f"trace_id={trace_id} execution_id={execution_id}"
                )

                result = self._forwarded_response(
                    trace_id=trace_id,
                    execution_id=execution_id,
                    artifact_id=stored["artifact_id"],
                    artifact_hash=artifact_hash,
                    verification=verification,
                    exec_result=exec_result,
                )

                self._store_idempotency(execution_id, result)

                return result
            else:
                return self._blocked_response(
                    verification["reason"], "BUCKET_VERIFY_FAILED",
                    trace_id, execution_id
                )

        except BucketUnauthorizedError as e:
            logger.error(f"[BRIDGE] bucket unauthorized: {e}")
            return self._blocked_response(str(e), "BUCKET_UNAUTHORIZED", trace_id, execution_id)
        except ValueError as e:
            logger.error(f"[BRIDGE] bucket write failed: {e}")
            return self._blocked_response(str(e), "BUCKET_WRITE_FAILED", trace_id, execution_id)
        except Exception as e:
            logger.error(f"[BRIDGE] bucket crash: {e}")
            return self._blocked_response(
                "bucket_service_error", "BUCKET_CRASH", trace_id, execution_id
            )

    def _check_idempotency(self, trace_id: str, execution_id: str) -> Optional[Dict[str, Any]]:
        idemp_file = _get_idempotency_file()
        if not __import__("os").path.exists(idemp_file):
            return None

        try:
            with open(idemp_file, "r", encoding="utf-8") as f:
                store = json.load(f)
            entry = store.get(execution_id)
            if entry is not None:
                return entry
        except Exception:
            pass
        return None

    def _store_idempotency(self, execution_id: str, result: Dict[str, Any]):
        idemp_file = _get_idempotency_file()
        store = {}
        if __import__("os").path.exists(idemp_file):
            try:
                with open(idemp_file, "r", encoding="utf-8") as f:
                    store = json.load(f)
            except Exception:
                store = {}

        store[execution_id] = result

        with open(idemp_file, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)

    def _forwarded_response(
        self,
        trace_id: str,
        execution_id: str,
        artifact_id: str,
        artifact_hash: str,
        verification: Dict[str, Any],
        exec_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "status": "FORWARDED",
            "reason": "authority_valid_executed_verified",
            "trace_id": trace_id,
            "execution_id": execution_id,
            "artifact_id": artifact_id,
            "artifact_hash": artifact_hash,
            "verified_write": verification["verified_write"],
            "hash_match": verification.get("hash_match", False),
            "schema_valid": verification.get("schema_valid", False),
            "execution_duration_ms": exec_result.get("execution_duration_ms"),
            "result_hash": exec_result.get("result_hash"),
        }

    def _blocked_response(
        self,
        reason: str,
        code: str,
        trace_id: Optional[str],
        execution_id: Optional[str],
    ) -> Dict[str, Any]:
        return {
            "status": "BLOCKED",
            "reason": reason,
            "code": code,
            "trace_id": str(trace_id) if trace_id is not None else "",
            "execution_id": str(execution_id) if execution_id is not None else "",
            "verified_write": False,
        }


tantra_bridge = TantraBridge()
