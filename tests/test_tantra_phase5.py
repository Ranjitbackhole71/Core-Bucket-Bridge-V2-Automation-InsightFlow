"""
TANTRA Phase 5 — Security & Adversarial Test Suite

Tests:
  AUTHORITY: missing, invalid, tampered, expired, replayed tokens
  TRACE: missing trace_id, modified trace_id
  SYSTEM: concurrent requests, race conditions, retry scenarios

All tests use REAL cryptographic validation (no mocks).
"""
import sys
import os
import json
import time
import hashlib
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.sarathi.authority import sarathi_authority, SarathiValidationError
from app.sarathi.key_manager import sarathi_keys
from app.sarathi.replay_detector import replay_detector
from app.execution.system import execution_system, ExecutionError
from app.services.bridge_integration import tantra_bridge
from app.services.bucket_service import bucket_service

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("tantra_security_tests")

RESULTS = {"passed": 0, "failed": 0, "tests": []}


def record(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    RESULTS["tests"].append({"name": name, "status": status, "detail": detail})
    if passed:
        RESULTS["passed"] += 1
        logger.info(f"  PASS: {name}")
    else:
        RESULTS["failed"] += 1
        logger.error(f"  FAIL: {name} — {detail}")


def reset_state():
    replay_detector.clear()
    bucket_data_path = os.path.join(BASE_DIR, "data", "bucket_artifacts.json")
    chain_data_path = os.path.join(BASE_DIR, "data", "chain_state.json")
    os.makedirs(os.path.dirname(bucket_data_path), exist_ok=True)
    if os.path.exists(bucket_data_path):
        with open(bucket_data_path, "w") as f:
            json.dump([], f)
    if os.path.exists(chain_data_path):
        with open(chain_data_path, "w") as f:
            json.dump({"last_hash": None, "count": 0}, f)
    execution_system._execution_count = 0


# ============================================================
# AUTHORITY TESTS
# ============================================================

def test_missing_token():
    reset_state()
    result = tantra_bridge.process(
        trace_id="t-1", execution_id="e-1",
        authority_token="", payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "MISSING_TOKEN" in result.get("code", "")
    record("missing_token → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_none_token():
    reset_state()
    result = tantra_bridge.process(
        trace_id="t-2", execution_id="e-2",
        authority_token=None, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED"
    record("None token → BLOCKED", passed, f"status={result['status']}")


def test_garbage_token():
    reset_state()
    result = tantra_bridge.process(
        trace_id="t-3", execution_id="e-3",
        authority_token="not_a_jwt_garbage_string", payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "INVALID_TOKEN" in result.get("code", "")
    record("garbage token → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_tampered_token():
    reset_state()
    valid_token = sarathi_authority.issue_token(ttl_seconds=300)
    tampered = valid_token[:-5] + "XXXXX"
    result = tantra_bridge.process(
        trace_id="t-4", execution_id="e-4",
        authority_token=tampered, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "INVALID_SIGNATURE" in result.get("code", "")
    record("tampered token → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_expired_token():
    reset_state()
    import jwt
    from app.sarathi.authority import SARATHI_ISSUER, SARATHI_ALGORITHM, SARATHI_AUDIENCE
    now = int(time.time())
    expired_payload = {
        "iss": SARATHI_ISSUER,
        "sub": "tantra-core",
        "aud": SARATHI_AUDIENCE,
        "iat": now - 600,
        "exp": now - 300,
        "jti": str(uuid.uuid4()),
    }
    private_key = sarathi_keys.get_private_key()
    expired_token = jwt.encode(expired_payload, private_key, algorithm=SARATHI_ALGORITHM)
    result = tantra_bridge.process(
        trace_id="t-5", execution_id="e-5",
        authority_token=expired_token, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "EXPIRED_TOKEN" in result.get("code", "")
    record("expired token → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_replay_attack():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    result1 = tantra_bridge.process(
        trace_id="t-6", execution_id="e-6",
        authority_token=token, payload={"test": True}
    )
    result2 = tantra_bridge.process(
        trace_id="t-6b", execution_id="e-6b",
        authority_token=token, payload={"test": True}
    )
    passed = (
        result1["status"] == "FORWARDED"
        and result2["status"] == "BLOCKED"
        and "REPLAY_ATTACK" in result2.get("code", "")
    )
    record("replay attack → BLOCKED (second use)", passed,
           f"first={result1['status']} second={result2['status']} code={result2.get('code')}")


def test_wrong_issuer_token():
    reset_state()
    import jwt
    from app.sarathi.authority import SARATHI_ALGORITHM, SARATHI_AUDIENCE
    now = int(time.time())
    payload = {
        "iss": "attacker-not-sarathi",
        "sub": "attacker",
        "aud": SARATHI_AUDIENCE,
        "iat": now,
        "exp": now + 300,
        "jti": str(uuid.uuid4()),
    }
    private_key = sarathi_keys.get_private_key()
    attacker_token = jwt.encode(payload, private_key, algorithm=SARATHI_ALGORITHM)
    result = tantra_bridge.process(
        trace_id="t-7", execution_id="e-7",
        authority_token=attacker_token, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "INVALID_ISSUER" in result.get("code", "")
    record("wrong issuer → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


# ============================================================
# TRACE TESTS
# ============================================================

def test_missing_trace_id():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    result = tantra_bridge.process(
        trace_id="", execution_id="e-8",
        authority_token=token, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "MISSING_TRACE_ID" in result.get("code", "")
    record("missing trace_id → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_missing_execution_id():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    result = tantra_bridge.process(
        trace_id="t-9", execution_id="",
        authority_token=token, payload={"test": True}
    )
    passed = result["status"] == "BLOCKED" and "MISSING_EXECUTION_ID" in result.get("code", "")
    record("missing execution_id → BLOCKED", passed, f"status={result['status']} code={result.get('code')}")


def test_trace_id_unchanged():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    orig_trace = "trace-immutable-xyz-123"
    orig_exec = "exec-immutable-abc-456"
    result = tantra_bridge.process(
        trace_id=orig_trace, execution_id=orig_exec,
        authority_token=token, payload={"data": "test"}
    )
    passed = (
        result["status"] == "FORWARDED"
        and result["trace_id"] == orig_trace
        and result["execution_id"] == orig_exec
    )
    record("trace_id + execution_id unchanged", passed,
           f"trace={result['trace_id']} exec={result['execution_id']}")


def test_artifact_preserves_trace():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    orig_trace = "trace-persist-check"
    orig_exec = "exec-persist-check"
    result = tantra_bridge.process(
        trace_id=orig_trace, execution_id=orig_exec,
        authority_token=token, payload={"data": "verify"}
    )
    artifact = bucket_service.get_artifact_by_id(f"artifact-{orig_exec}")
    passed = (
        artifact is not None
        and artifact.get("trace_id") == orig_trace
        and artifact.get("execution_id") == orig_exec
    )
    record("artifact preserves trace_id + execution_id", passed,
           f"artifact_trace={artifact.get('trace_id') if artifact else 'None'}")


# ============================================================
# SYSTEM TESTS
# ============================================================

def test_concurrent_requests():
    reset_state()
    tokens = [sarathi_authority.issue_token(ttl_seconds=300) for _ in range(10)]
    results = []

    def run_one(idx):
        return tantra_bridge.process(
            trace_id=f"t-concurrent-{idx}",
            execution_id=f"e-concurrent-{idx}",
            authority_token=tokens[idx],
            payload={"concurrent": True, "index": idx},
        )

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(run_one, i) for i in range(10)]
        for f in as_completed(futures):
            results.append(f.result())

    forwarded = sum(1 for r in results if r["status"] == "FORWARDED")
    blocked = sum(1 for r in results if r["status"] == "BLOCKED")
    no_corruption = all(
        "chain" not in r.get("reason", "").lower() or r["status"] == "BLOCKED"
        for r in results
    )
    passed = (
        forwarded >= 1
        and forwarded + blocked == 10
        and no_corruption
        and all(r["trace_id"].startswith("t-concurrent-") for r in results)
    )
    record("concurrent requests (10 parallel)", passed,
           f"forwarded={forwarded} blocked={blocked} no_corruption={no_corruption}")


def test_race_condition_bucket():
    reset_state()
    tokens = [sarathi_authority.issue_token(ttl_seconds=300) for _ in range(5)]
    results = []

    def run_one(idx):
        return tantra_bridge.process(
            trace_id=f"t-race-{idx}",
            execution_id=f"e-race-{idx}",
            authority_token=tokens[idx],
            payload={"race_test": True, "index": idx},
        )

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(run_one, i) for i in range(5)]
        for f in as_completed(futures):
            results.append(f.result())

    artifacts = bucket_service.get_all_artifacts()
    unique_traces = set(a["trace_id"] for a in artifacts)
    chain_valid = True
    for i, artifact in enumerate(artifacts):
        if i == 0:
            if artifact.get("parent_hash") not in (None, "GENESIS"):
                chain_valid = False
        else:
            prev_hash = artifacts[i - 1]["artifact_hash"]
            if artifact.get("parent_hash") != prev_hash:
                chain_valid = False
    passed = (
        len(artifacts) >= 1
        and len(unique_traces) == len(artifacts)
        and chain_valid
    )
    record("race condition bucket writes (chain integrity preserved)", passed,
           f"artifacts={len(artifacts)} unique={len(unique_traces)} chain_valid={chain_valid}")


def test_retry_on_invalid_then_valid():
    reset_state()
    valid_token = sarathi_authority.issue_token(ttl_seconds=300)
    result1 = tantra_bridge.process(
        trace_id="t-retry-1", execution_id="e-retry-1",
        authority_token="invalid_token", payload={"test": True}
    )
    result2 = tantra_bridge.process(
        trace_id="t-retry-2", execution_id="e-retry-2",
        authority_token=valid_token, payload={"test": True}
    )
    passed = (
        result1["status"] == "BLOCKED"
        and result2["status"] == "FORWARDED"
    )
    record("invalid then valid (retry scenario)", passed,
           f"first={result1['status']} second={result2['status']}")


def test_bridge_never_bypassed():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    result = tantra_bridge.process(
        trace_id="t-bypass", execution_id="e-bypass",
        authority_token=token, payload={"bypass_check": True}
    )
    artifact = bucket_service.get_artifact_by_id("artifact-e-bypass")
    passed = (
        result["status"] == "FORWARDED"
        and artifact is not None
        and "result_hash" in artifact.get("payload", {})
    )
    record("bridge not bypassed — execution result in artifact", passed,
           f"has_result_hash={'result_hash' in artifact.get('payload', {}) if artifact else False}")


def test_valid_token_forwards():
    reset_state()
    token = sarathi_authority.issue_token(ttl_seconds=300)
    result = tantra_bridge.process(
        trace_id="t-valid", execution_id="e-valid",
        authority_token=token, payload={"test": "forward"}
    )
    passed = (
        result["status"] == "FORWARDED"
        and result["verified_write"] is True
        and result["hash_match"] is True
        and result["schema_valid"] is True
    )
    record("valid token → FORWARDED with full verification", passed,
           f"verified={result['verified_write']} hash={result['hash_match']} schema={result['schema_valid']}")


# ============================================================
# RUN ALL
# ============================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("TANTRA PHASE 5 — SECURITY & ADVERSARIAL TESTS")
    logger.info("=" * 80)

    logger.info("\n--- AUTHORITY TESTS ---")
    test_missing_token()
    test_none_token()
    test_garbage_token()
    test_tampered_token()
    test_expired_token()
    test_replay_attack()
    test_wrong_issuer_token()

    logger.info("\n--- TRACE TESTS ---")
    test_missing_trace_id()
    test_missing_execution_id()
    test_trace_id_unchanged()
    test_artifact_preserves_trace()

    logger.info("\n--- SYSTEM TESTS ---")
    test_concurrent_requests()
    test_race_condition_bucket()
    test_retry_on_invalid_then_valid()
    test_bridge_never_bypassed()
    test_valid_token_forwards()

    logger.info("\n" + "=" * 80)
    logger.info(f"RESULTS: {RESULTS['passed']} passed, {RESULTS['failed']} failed, {len(RESULTS['tests'])} total")
    logger.info("=" * 80)

    for t in RESULTS["tests"]:
        logger.info(f"  [{t['status']}] {t['name']}")

    if RESULTS["failed"] > 0:
        sys.exit(1)
    logger.info("\nALL TESTS PASSED")
