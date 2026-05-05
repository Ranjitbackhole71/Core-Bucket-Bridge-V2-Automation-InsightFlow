"""
TANTRA Phase 6 — End-to-End Proof

Demonstrates ONE REAL FLOW:
  Core → Sarathi issues token → Bridge validates → Execution runs → Bucket writes → Verification

NO MOCK DATA. Real cryptographic validation. Real execution. Real persistence.
"""
import sys
import os
import json
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.sarathi.authority import sarathi_authority, SarathiValidationError, SARATHI_ISSUER, SARATHI_AUDIENCE, SARATHI_ALGORITHM
from app.sarathi.key_manager import sarathi_keys
from app.execution.system import execution_system
from app.services.bridge_integration import tantra_bridge
from app.services.bucket_service import bucket_service
from app.services.hash_service import compute_artifact_hash, verify_artifact_hash

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tantra_e2e")


def reset_all():
    from app.sarathi.replay_detector import replay_detector
    replay_detector.clear()
    execution_system._execution_count = 0
    bucket_data = os.path.join(BASE_DIR, "data", "bucket_artifacts.json")
    chain_data = os.path.join(BASE_DIR, "data", "chain_state.json")
    os.makedirs(os.path.dirname(bucket_data), exist_ok=True)
    if os.path.exists(bucket_data):
        with open(bucket_data, "w") as f:
            json.dump([], f)
    if os.path.exists(chain_data):
        with open(chain_data, "w") as f:
            json.dump({"last_hash": None, "count": 0}, f)


def main():
    reset_all()

    logger.info("=" * 80)
    logger.info("TANTRA END-TO-END PROOF — REAL FLOW")
    logger.info("=" * 80)

    # === INPUT from Core ===
    trace_id = "core-trace-e2e-001"
    execution_id = "core-exec-e2e-001"
    payload = {
        "task": "production_validation",
        "source": "tantra-core",
        "data": {"value": 42, "verified": False},
    }

    logger.info(f"\n[INPUT] Core provides:")
    logger.info(f"  trace_id     = {trace_id}")
    logger.info(f"  execution_id = {execution_id}")
    logger.info(f"  payload      = {json.dumps(payload)}")

    # === SARATHI issues token ===
    logger.info(f"\n[SARATHI] Issuing authority token...")
    authority_token = sarathi_authority.issue_token(
        subject="tantra-core",
        audience="tantra-bridge",
        ttl_seconds=300,
        extra_claims={"trace_id": trace_id, "execution_id": execution_id},
    )
    token_preview = authority_token[:50] + "..."
    logger.info(f"  token = {token_preview}")
    logger.info(f"  algo  = RS256 (RSA-2048)")

    # === BRIDGE processes ===
    logger.info(f"\n[BRIDGE] Processing through execution gate...")
    result = tantra_bridge.process(
        trace_id=trace_id,
        execution_id=execution_id,
        authority_token=authority_token,
        payload=payload,
    )

    logger.info(f"\n[BRIDGE] Result:")
    logger.info(f"  status           = {result['status']}")
    logger.info(f"  reason           = {result['reason']}")
    logger.info(f"  trace_id         = {result['trace_id']}")
    logger.info(f"  execution_id     = {result['execution_id']}")

    if result["status"] == "FORWARDED":
        logger.info(f"  artifact_id      = {result['artifact_id']}")
        logger.info(f"  artifact_hash    = {result['artifact_hash']}")
        logger.info(f"  verified_write   = {result['verified_write']}")
        logger.info(f"  hash_match       = {result['hash_match']}")
        logger.info(f"  schema_valid     = {result['schema_valid']}")
        logger.info(f"  execution_dur_ms = {result['execution_duration_ms']}")
        logger.info(f"  result_hash      = {result['result_hash']}")

    # === BUCKET verification ===
    logger.info(f"\n[BUCKET] Read-after-write verification...")
    artifact = bucket_service.get_artifact_by_id(f"artifact-{execution_id}")

    if artifact:
        logger.info(f"  artifact found   = True")
        logger.info(f"  trace_id         = {artifact['trace_id']}")
        logger.info(f"  execution_id     = {artifact['execution_id']}")
        logger.info(f"  artifact_type    = {artifact['artifact_type']}")
        logger.info(f"  parent_hash      = {artifact['parent_hash']}")
        logger.info(f"  schema_version   = {artifact['schema_version']}")

        hash_valid = verify_artifact_hash(artifact)
        logger.info(f"  hash_verified    = {hash_valid}")

        exec_result_in_artifact = artifact.get("payload", {}).get("execution_result", {})
        logger.info(f"  exec_trace_id    = {exec_result_in_artifact.get('trace_id')}")
        logger.info(f"  exec_exec_id     = {exec_result_in_artifact.get('execution_id')}")

    # === TRACE CONTINUITY PROOF ===
    logger.info(f"\n[TRACE] Continuity check:")
    trace_match = (
        trace_id == result["trace_id"] == artifact["trace_id"] ==
        exec_result_in_artifact.get("trace_id")
    )
    exec_match = (
        execution_id == result["execution_id"] == artifact["execution_id"] ==
        exec_result_in_artifact.get("execution_id")
    )
    logger.info(f"  trace_id consistent     = {trace_match}")
    logger.info(f"  execution_id consistent = {exec_match}")

    # === FINAL VERDICT ===
    logger.info(f"\n{'=' * 80}")
    all_pass = (
        result["status"] == "FORWARDED"
        and result["trace_id"] == trace_id
        and result["execution_id"] == execution_id
        and result["verified_write"] is True
        and result["hash_match"] is True
        and result["schema_valid"] is True
        and hash_valid
        and trace_match
        and exec_match
    )
    if all_pass:
        logger.info("END-TO-END PROOF: ✅ ALL CHECKS PASSED")
    else:
        logger.info("END-TO-END PROOF: ❌ SOME CHECKS FAILED")
    logger.info(f"{'=' * 80}")

    if not all_pass:
        sys.exit(1)


if __name__ == "__main__":
    main()
