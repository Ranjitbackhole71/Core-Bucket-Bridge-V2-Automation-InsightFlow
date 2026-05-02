"""
Non-bypass tests for bridge_gateway.py

Rules:
  no token      → BLOCK
  invalid token → BLOCK
  tampered token → BLOCK
  valid token   → FORWARD
"""

import sys
import os

# Ensure app/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.bridge_gateway import validate_and_forward

_VALID_TOKEN = "valid_authority_bridge_key_2026"

def _req(token=None, trace_id="t-1", execution_id="e-1", payload=None):
    return {
        "authority_token": token,
        "trace_id": trace_id,
        "execution_id": execution_id,
        "payload": payload or {"test": True},
    }


def test_no_token_blocks():
    r = validate_and_forward(_req(token=None))
    assert r["status"] == "BLOCKED", f"Expected BLOCKED, got {r['status']}"
    assert "Missing" in r["reason"], f"Wrong reason: {r['reason']}"
    assert "execution_id" in r, "Missing execution_id in log"
    print("  PASS: no token -> BLOCK")


def test_empty_token_blocks():
    r = validate_and_forward(_req(token=""))
    assert r["status"] == "BLOCKED"
    assert "Missing" in r["reason"]
    print("  PASS: empty token -> BLOCK")


def test_invalid_token_blocks():
    r = validate_and_forward(_req(token="garbage"))
    assert r["status"] == "BLOCKED"
    assert "Invalid" in r["reason"], f"Wrong reason: {r['reason']}"
    print("  PASS: invalid token -> BLOCK")


def test_tampered_token_blocks():
    r = validate_and_forward(_req(token="valid_authority_bridge_key_0000"))
    assert r["status"] == "BLOCKED"
    assert "Tampered" in r["reason"], f"Expected Tampered, got: {r['reason']}"
    print("  PASS: tampered token -> BLOCK")


def test_valid_token_forwards():
    r = validate_and_forward(_req(token=_VALID_TOKEN))
    assert r["status"] == "FORWARDED", f"Expected FORWARDED, got {r['status']}"
    assert r["verified_write"] is True, "verified_write should be True"
    print("  PASS: valid token -> FORWARD")


def test_trace_unchanged():
    r = validate_and_forward(_req(token=_VALID_TOKEN, trace_id="t-999", execution_id="e-999"))
    assert r["trace_id"] == "t-999", f"trace_id mutated: {r['trace_id']}"
    assert r["execution_id"] == "e-999", f"execution_id mutated: {r['execution_id']}"
    print("  PASS: trace_id + execution_id unchanged")


def test_log_contract_blocked():
    """Every BLOCK response must have: status, reason, trace_id, execution_id."""
    r = validate_and_forward(_req(token=None, trace_id="t-x", execution_id="e-x"))
    for key in ("status", "reason", "trace_id", "execution_id"):
        assert key in r, f"Missing '{key}' in BLOCK log: {r}"
    print("  PASS: log contract on BLOCK")


def test_log_contract_forwarded():
    """Every FORWARD response must have: status, reason, trace_id, execution_id, verified_write."""
    r = validate_and_forward(_req(token=_VALID_TOKEN, trace_id="t-y", execution_id="e-y"))
    for key in ("status", "reason", "trace_id", "execution_id", "verified_write"):
        assert key in r, f"Missing '{key}' in FORWARD log: {r}"
    print("  PASS: log contract on FORWARD")


if __name__ == "__main__":
    print("=== Bridge Non-Bypass Tests ===\n")
    test_no_token_blocks()
    test_empty_token_blocks()
    test_invalid_token_blocks()
    test_tampered_token_blocks()
    test_valid_token_forwards()
    test_trace_unchanged()
    test_log_contract_blocked()
    test_log_contract_forwarded()
    print("\n=== ALL TESTS PASSED ===")
