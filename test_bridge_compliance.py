"""
Bridge Service Compliance Test
Verifies strict architectural constraints after refactoring.
"""
import json
import logging
import sys
from unittest.mock import MagicMock, Mock
from datetime import datetime, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger("bridge_compliance_test")

# Import Bridge service
sys.path.insert(0, r"c:\Users\Ranjit\OneDrive\Desktop\Core-Bucket-Bridge-V2-Automation-InsightFlow\app")
from services.bridge_integration import bridge_service


class MockBucketClient:
    """Mock bucket client with read-back verification support."""
    
    def __init__(self):
        self.storage = {}
        self.latest_artifact = None
    
    def store_artifact(self, artifact):
        """Store artifact and return ID."""
        artifact_id = artifact["artifact_id"]
        self.storage[artifact_id] = artifact.copy()
        self.latest_artifact = artifact.copy()
        return artifact_id
    
    def get_artifact(self, artifact_id):
        """Retrieve artifact by ID."""
        return self.storage.get(artifact_id)
    
    def get_latest_artifact(self):
        """Get latest artifact for provenance chain."""
        return self.latest_artifact


def test_blocked_missing_authority_token():
    """TEST 1: Missing authority_token → BLOCKED"""
    logger.info("=" * 80)
    logger.info("TEST 1: Missing Authority Token → BLOCKED")
    logger.info("=" * 80)
    
    result = bridge_service.validate_and_forward(
        execution_id="exec-001",
        trace_id="trace-001",
        authority_token="",  # MISSING
        payload={"test": "data"}
    )
    
    logger.info(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "missing_authority_token"
    assert result["trace_id"] == "trace-001"
    
    logger.info("✅ TEST 1 PASSED\n")


def test_blocked_invalid_authority_token():
    """TEST 2: Invalid authority_token → BLOCKED"""
    logger.info("=" * 80)
    logger.info("TEST 2: Invalid Authority Token → BLOCKED")
    logger.info("=" * 80)
    
    result = bridge_service.validate_and_forward(
        execution_id="exec-002",
        trace_id="trace-002",
        authority_token="short",  # INVALID (too short)
        payload={"test": "data"}
    )
    
    logger.info(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "invalid_authority_token"
    assert result["trace_id"] == "trace-002"
    
    logger.info("✅ TEST 2 PASSED\n")


def test_blocked_missing_trace_ids():
    """TEST 3: Missing trace IDs → BLOCKED"""
    logger.info("=" * 80)
    logger.info("TEST 3: Missing Trace IDs → BLOCKED")
    logger.info("=" * 80)
    
    result = bridge_service.validate_and_forward(
        execution_id="",  # MISSING
        trace_id="",      # MISSING
        authority_token="valid-token-12345",
        payload={"test": "data"}
    )
    
    logger.info(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["status"] == "BLOCKED"
    assert result["reason"] == "missing_trace_ids"
    
    logger.info("✅ TEST 3 PASSED\n")


def test_forwarded_success_with_verification():
    """TEST 4: Valid request → FORWARDED with read-back verification"""
    logger.info("=" * 80)
    logger.info("TEST 4: Valid Request → FORWARDED with Verification")
    logger.info("=" * 80)
    
    # Setup mock bucket client
    mock_bucket = MockBucketClient()
    bridge_service.bucket_client = mock_bucket
    
    result = bridge_service.validate_and_forward(
        execution_id="exec-004",
        trace_id="trace-004",
        authority_token="valid-authority-token-12345",
        payload={
            "score": 75,
            "status": "pass",
            "submission_id": "sub-004"
        }
    )
    
    logger.info(f"Result: {json.dumps(result, indent=2)}")
    
    assert result["status"] == "FORWARDED"
    assert result["reason"] == "artifact_stored_verified"
    assert result["trace_id"] == "trace-004"
    assert result["artifact_id"] is not None
    assert result["verified_write"] == True
    
    # Verify artifact in bucket
    artifact = mock_bucket.get_artifact(result["artifact_id"])
    assert artifact is not None
    assert artifact["execution_id"] == "exec-004"  # UNCHANGED
    assert artifact["trace_id"] == "trace-004"      # UNCHANGED
    assert artifact["artifact_hash"] is not None
    assert artifact["parent_hash"] == "GENESIS"     # First artifact
    
    # Verify schema compliance
    required_fields = [
        "artifact_id", "timestamp_utc", "schema_version",
        "source_module_id", "artifact_type", "parent_hash",
        "payload", "artifact_hash"
    ]
    for field in required_fields:
        assert field in artifact, f"Missing field: {field}"
    
    logger.info("✅ TEST 4 PASSED\n")
    return result["artifact_id"]


def test_provenance_chain_with_bucket():
    """TEST 5: Provenance chain fetches from Bucket (NOT local)"""
    logger.info("=" * 80)
    logger.info("TEST 5: Provenance Chain from Bucket (NOT Local)")
    logger.info("=" * 80)
    
    # Setup mock bucket client with existing artifact
    mock_bucket = MockBucketClient()
    bridge_service.bucket_client = mock_bucket
    
    # Create first artifact
    first_artifact_id = bridge_service.validate_and_forward(
        execution_id="exec-005a",
        trace_id="trace-005a",
        authority_token="valid-authority-token-12345",
        payload={"score": 75, "status": "pass"}
    )
    
    # Get first artifact hash
    first_artifact = mock_bucket.get_artifact(first_artifact_id["artifact_id"])
    first_hash = first_artifact["artifact_hash"]
    logger.info(f"First artifact hash: {first_hash}")
    
    # Create second artifact (should chain from first)
    second_result = bridge_service.validate_and_forward(
        execution_id="exec-005b",
        trace_id="trace-005b",
        authority_token="valid-authority-token-12345",
        payload={"score": 85, "status": "pass"}
    )
    
    second_artifact = mock_bucket.get_artifact(second_result["artifact_id"])
    logger.info(f"Second artifact parent_hash: {second_artifact['parent_hash']}")
    
    # Verify chain: second.parent_hash == first.artifact_hash
    assert second_artifact["parent_hash"] == first_hash, \
        f"Chain broken: expected {first_hash}, got {second_artifact['parent_hash']}"
    
    logger.info("✅ TEST 5 PASSED\n")


def test_trace_ids_unchanged():
    """TEST 6: Trace IDs forwarded UNCHANGED (NOT generated/modified)"""
    logger.info("=" * 80)
    logger.info("TEST 6: Trace IDs Forwarded UNCHANGED")
    logger.info("=" * 80)
    
    mock_bucket = MockBucketClient()
    bridge_service.bucket_client = mock_bucket
    
    execution_id = "exec-006-ORIGINAL"
    trace_id = "trace-006-ORIGINAL"
    
    result = bridge_service.validate_and_forward(
        execution_id=execution_id,
        trace_id=trace_id,
        authority_token="valid-authority-token-12345",
        payload={"test": "data"}
    )
    
    # Retrieve artifact from bucket
    artifact = mock_bucket.get_artifact(result["artifact_id"])
    
    # Verify trace IDs are EXACTLY as provided
    assert artifact["execution_id"] == execution_id, \
        f"execution_id modified: expected {execution_id}, got {artifact['execution_id']}"
    assert artifact["trace_id"] == trace_id, \
        f"trace_id modified: expected {trace_id}, got {artifact['trace_id']}"
    
    logger.info(f"execution_id: {artifact['execution_id']} ✅")
    logger.info(f"trace_id: {artifact['trace_id']} ✅")
    
    logger.info("✅ TEST 6 PASSED\n")


def test_no_evaluation_logic():
    """TEST 7: Bridge does NOT contain evaluation logic"""
    logger.info("=" * 80)
    logger.info("TEST 7: No Evaluation Logic in Bridge")
    logger.info("=" * 80)
    
    # Verify bridge service has NO evaluation methods
    assert not hasattr(bridge_service, 'evaluate'), "Bridge has evaluate method!"
    assert not hasattr(bridge_service, 'check_decision'), "Bridge has check_decision method!"
    assert not hasattr(bridge_service, 'score_payload'), "Bridge has score_payload method!"
    
    # Verify bridge accepts ANY payload (no inspection)
    mock_bucket = MockBucketClient()
    bridge_service.bucket_client = mock_bucket
    
    # Send payload with "REJECTED" status (should still forward)
    result = bridge_service.validate_and_forward(
        execution_id="exec-007",
        trace_id="trace-007",
        authority_token="valid-authority-token-12345",
        payload={
            "score": 30,
            "status": "fail",  # REJECTED status
            "decision": "REJECTED"
        }
    )
    
    # Bridge should FORWARD regardless of payload content
    assert result["status"] == "FORWARDED", \
        f"Bridge inspected payload and blocked! Status: {result['status']}"
    
    logger.info("✅ Bridge forwards ALL payloads (no evaluation)")
    logger.info("✅ TEST 7 PASSED\n")


if __name__ == "__main__":
    logger.info("\n" + "=" * 80)
    logger.info("BRIDGE SERVICE COMPLIANCE TEST SUITE")
    logger.info("=" * 80 + "\n")
    
    try:
        # Run all tests
        test_blocked_missing_authority_token()
        test_blocked_invalid_authority_token()
        test_blocked_missing_trace_ids()
        test_forwarded_success_with_verification()
        test_provenance_chain_with_bucket()
        test_trace_ids_unchanged()
        test_no_evaluation_logic()
        
        logger.info("=" * 80)
        logger.info("ALL COMPLIANCE TESTS PASSED ✅")
        logger.info("=" * 80)
        
    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}", exc_info=True)
        sys.exit(1)
