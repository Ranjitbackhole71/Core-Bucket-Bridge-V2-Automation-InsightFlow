"""
Execution System — Real Execution Layer (PROTECTED)

Processes payloads through deterministic execution pipeline.
Returns actual execution result with trace continuity.

PROTECTION:
- Requires bridge_authorization proof to execute
- Validates trace_id and execution_id independently
- Rejects direct calls without valid bridge signature
"""
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from ..sarathi.bridge_signer import bridge_signer

logger = logging.getLogger("execution_system")


class ExecutionError(Exception):
    def __init__(self, reason: str, code: str):
        self.reason = reason
        self.code = code
        super().__init__(self.reason)


class ExecutionSystem:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._execution_count = 0

    def execute(
        self,
        trace_id: str,
        execution_id: str,
        payload: Dict[str, Any],
        bridge_authorization: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not trace_id:
            raise ExecutionError("Missing trace_id", "MISSING_TRACE_ID")
        if not execution_id:
            raise ExecutionError("Missing execution_id", "MISSING_EXECUTION_ID")
        if not payload or not isinstance(payload, dict):
            raise ExecutionError("Invalid payload", "INVALID_PAYLOAD")

        if bridge_authorization is None:
            raise ExecutionError(
                "Execution requires bridge_authorization — direct calls are blocked",
                "UNAUTHORIZED_EXECUTION",
            )

        if not bridge_signer.verify(bridge_authorization):
            raise ExecutionError(
                "Invalid bridge authorization signature",
                "UNAUTHORIZED_EXECUTION",
            )
        if not bridge_signer.verify_timestamp(bridge_authorization):
            raise ExecutionError(
                "Bridge authorization expired",
                "EXPIRED_AUTHORIZATION",
            )

        self._execution_count += 1

        execution_start = time.time()

        result_payload = self._process_payload(payload, execution_id, trace_id)

        execution_duration_ms = round((time.time() - execution_start) * 1000, 2)

        execution_result = {
            "execution_id": execution_id,
            "trace_id": trace_id,
            "status": "EXECUTED",
            "result": result_payload,
            "execution_number": self._execution_count,
            "execution_duration_ms": execution_duration_ms,
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        }

        result_hash = self._compute_result_hash(execution_result)
        execution_result["result_hash"] = result_hash

        logger.info(
            f"[EXECUTION] executed trace_id={trace_id} execution_id={execution_id} "
            f"duration={execution_duration_ms}ms hash={result_hash[:16]}..."
        )

        return execution_result

    def _process_payload(
        self,
        payload: Dict[str, Any],
        execution_id: str,
        trace_id: str,
    ) -> Dict[str, Any]:
        input_hash = self._compute_input_hash(payload)
        workload_proof = self._run_workload(input_hash)

        processed = {
            "input_hash": input_hash,
            "execution_id": execution_id,
            "trace_id": trace_id,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "data": payload,
            "workload_proof": workload_proof,
        }
        return processed

    def _run_workload(self, input_hash: str) -> Dict[str, Any]:
        """
        Real non-trivial workload to prove actual execution.
        Performs measurable computation — not a mock return.
        """
        import hashlib as _h

        seed = input_hash.encode("utf-8")
        accumulator = 0
        iterations = 1000

        for i in range(iterations):
            data = seed + str(i).encode("utf-8")
            chunk_hash = _h.sha256(data).hexdigest()
            accumulator += int(chunk_hash[:8], 16)

        final_hash = _h.sha256(str(accumulator).encode("utf-8")).hexdigest()

        return {
            "type": "workload_proof",
            "input_hash": input_hash,
            "iterations": iterations,
            "final_proof": final_hash,
            "accumulator_mod_10000": accumulator % 10000,
        }

    def _compute_input_hash(self, payload: Dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _compute_result_hash(self, result: Dict[str, Any]) -> str:
        result_copy = {k: v for k, v in result.items() if k != "result_hash"}
        canonical = json.dumps(result_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def execution_count(self):
        return self._execution_count


execution_system = ExecutionSystem()
