"""
TANTRA Integration Test - Full Pipeline Proof
Simulates: Input → Bridge → Evaluation → Forward → Bucket

Tests:
1. Full pipeline with ACCEPTED decision
2. REJECTED decision (not forwarded)
3. Bucket failure with retry logic
4. Provenance chain (2 artifacts)
"""
import json
import logging
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("integration_test")

# Import integration components
sys.path.insert(0, r"c:\Users\Ranjit\OneDrive\Desktop\Core-Bucket-Bridge-V2-Automation-InsightFlow\app")
from services.artifact_transformer import artifact_transformer
from services.retry_handler import retry_handler
from services.bridge_integration import bridge_integration


class MockBucketClient:
    """Mock bucket client for testing."""
    
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.call_count = 0
        self.stored_artifacts = []
    
    def store_artifact(self, artifact):
        """Simulate bucket storage."""
        self.call_count += 1
        
        if self.should_fail:
            raise Exception("Bucket service unavailable")
        
        # Simulate successful storage
        artifact_id = f"artifact-{self.call_count:04d}"
        self.stored_artifacts.append({
            "artifact_id": artifact_id,
            "artifact": artifact,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return artifact_id


def test_full_pipeline_accepted():
    """Test 1: Full pipeline with ACCEPTED decision."""
    logger.info("=" * 80)
    logger.info("TEST 1: Full Pipeline - ACCEPTED Decision")
    logger.info("=" * 80)
    
    # Reset transformer
    artifact_transformer.reset_chain()
    
    # Setup mock bucket client
    mock_bucket = MockBucketClient(should_fail=False)
    bridge_integration.bucket_client = mock_bucket
    
    # Sample input
    input_data = {
        "task_title": "AI Resume Screening System",
        "task_description": "ML system to analyze resumes",
        "submitted_by": "student",
        "module_id": "task-review-agent",
        "schema_version": "v1.0"
    }
    
    # Sample evaluation result
    evaluation_result = {
        "submission_id": "sub-001",
        "score": 75,
        "status": "pass",
        "readiness_percent": 85,
        "next_task_id": "next-001",
        "task_type": "enhancement"
    }
    
    # Process through Bridge
    result = bridge_integration.process_evaluation_artifact(
        evaluation_result=evaluation_result,
        input_data=input_data,
        rule_id="EVALUATION_GATE"
    )
    
    # Print results
    logger.info(f"\n📦 ARTIFACT GENERATED:")
    logger.info(json.dumps(result["artifact"], indent=2))
    
    logger.info(f"\n✅ BUCKET RESPONSE:")
    logger.info(json.dumps(result["bucket_response"], indent=2))
    
    logger.info(f"\n📊 SUMMARY:")
    logger.info(f"  - Decision: {result['artifact']['decision']}")
    logger.info(f"  - Forwarded: {result['forwarded']}")
    logger.info(f"  - Artifact ID: {result['bucket_response']['artifact_id']}")
    logger.info(f"  - Provenance Hash: {result['provenance_hash']}")
    
    assert result["forwarded"] == True
    assert result["artifact"]["decision"] == "ACCEPTED"
    assert result["bucket_response"]["artifact_id"] == "artifact-0001"
    
    logger.info("\n✅ TEST 1 PASSED\n")
    return result["artifact"]


def test_rejected_not_forwarded():
    """Test 2: REJECTED decision should NOT be forwarded."""
    logger.info("=" * 80)
    logger.info("TEST 2: REJECTED Decision - Not Forwarded")
    logger.info("=" * 80)
    
    # Reset transformer
    artifact_transformer.reset_chain()
    
    # Setup mock bucket client
    mock_bucket = MockBucketClient(should_fail=False)
    bridge_integration.bucket_client = mock_bucket
    
    # Sample input
    input_data = {
        "task_title": "Incomplete Project",
        "task_description": "Missing core features",
        "submitted_by": "student",
        "module_id": "task-review-agent",
        "schema_version": "v1.0"
    }
    
    # Sample evaluation result (FAIL)
    evaluation_result = {
        "submission_id": "sub-002",
        "score": 30,
        "status": "fail",
        "readiness_percent": 25,
        "next_task_id": "next-002",
        "task_type": "correction"
    }
    
    # Process through Bridge
    result = bridge_integration.process_evaluation_artifact(
        evaluation_result=evaluation_result,
        input_data=input_data,
        rule_id="EVALUATION_GATE"
    )
    
    # Print results
    logger.info(f"\n📦 ARTIFACT GENERATED:")
    logger.info(json.dumps(result["artifact"], indent=2))
    
    logger.info(f"\n🚫 FORWARDING BLOCKED:")
    logger.info(f"  - Forwarded: {result['forwarded']}")
    logger.info(f"  - Reason: {result['reason']}")
    
    assert result["forwarded"] == False
    assert result["artifact"]["decision"] == "REJECTED"
    assert mock_bucket.call_count == 0  # Bucket NOT called
    
    logger.info("\n✅ TEST 2 PASSED\n")
    return result["artifact"]


def test_bucket_failure_with_retry():
    """Test 3: Bucket failure triggers retry logic."""
    logger.info("=" * 80)
    logger.info("TEST 3: Bucket Failure - Retry Logic")
    logger.info("=" * 80)
    
    # Reset transformer
    artifact_transformer.reset_chain()
    
    # Setup mock bucket client (WILL FAIL)
    mock_bucket = MockBucketClient(should_fail=True)
    bridge_integration.bucket_client = mock_bucket
    
    # Sample input
    input_data = {
        "task_title": "Test Project",
        "task_description": "Testing retry logic",
        "submitted_by": "student",
        "module_id": "task-review-agent",
        "schema_version": "v1.0"
    }
    
    # Sample evaluation result (PASS)
    evaluation_result = {
        "submission_id": "sub-003",
        "score": 80,
        "status": "pass",
        "readiness_percent": 90,
        "next_task_id": "next-003",
        "task_type": "enhancement"
    }
    
    # Process through Bridge
    result = bridge_integration.process_evaluation_artifact(
        evaluation_result=evaluation_result,
        input_data=input_data,
        rule_id="EVALUATION_GATE"
    )
    
    # Print results
    logger.info(f"\n📦 ARTIFACT GENERATED:")
    logger.info(json.dumps(result["artifact"], indent=2))
    
    logger.info(f"\n❌ BUCKET FAILURE:")
    logger.info(json.dumps(result["bucket_response"], indent=2))
    
    assert result["forwarded"] == False
    assert result["bucket_response"]["attempts"] == 2
    assert "Bucket service unavailable" in result["bucket_response"]["error"]
    assert mock_bucket.call_count == 2  # Retried 2 times
    
    logger.info("\n✅ TEST 3 PASSED\n")


def test_provenance_chain():
    """Test 4: Provenance chain with 2 artifacts."""
    logger.info("=" * 80)
    logger.info("TEST 4: Provenance Chain - 2 Artifacts")
    logger.info("=" * 80)
    
    # Reset transformer
    artifact_transformer.reset_chain()
    
    logger.info(f"\n🔗 Initial provenance hash: {artifact_transformer.previous_provenance_hash}")
    
    # Artifact 1
    artifact_1 = artifact_transformer.transform(
        evaluation_result={"score": 75, "status": "pass", "submission_id": "sub-004"},
        input_data={"task_title": "First Task", "submitted_by": "student"},
        rule_id="EVALUATION_GATE"
    )
    
    logger.info(f"\n📦 ARTIFACT 1:")
    logger.info(f"  - artifact_hash: {artifact_1['artifact_hash']}")
    logger.info(f"  - provenance_hash: {artifact_1['provenance_hash']}")
    
    # Artifact 2 (should chain from artifact 1)
    artifact_2 = artifact_transformer.transform(
        evaluation_result={"score": 85, "status": "pass", "submission_id": "sub-005"},
        input_data={"task_title": "Second Task", "submitted_by": "student"},
        rule_id="EVALUATION_GATE"
    )
    
    logger.info(f"\n📦 ARTIFACT 2:")
    logger.info(f"  - artifact_hash: {artifact_2['artifact_hash']}")
    logger.info(f"  - provenance_hash: {artifact_2['provenance_hash']}")
    
    # Verify chaining
    import hashlib
    expected_chain_input = artifact_1['provenance_hash'] + artifact_2['artifact_hash']
    expected_provenance = hashlib.sha256(expected_chain_input.encode('utf-8')).hexdigest()
    
    logger.info(f"\n🔗 CHAIN VERIFICATION:")
    logger.info(f"  - Expected: {expected_provenance}")
    logger.info(f"  - Actual:   {artifact_2['provenance_hash']}")
    logger.info(f"  - Match: {expected_provenance == artifact_2['provenance_hash']}")
    
    assert artifact_2['provenance_hash'] == expected_provenance
    
    logger.info("\n✅ TEST 4 PASSED\n")


if __name__ == "__main__":
    logger.info("\n" + "=" * 80)
    logger.info("TANTRA INTEGRATION TEST SUITE")
    logger.info("=" * 80 + "\n")
    
    try:
        # Run all tests
        artifact_1 = test_full_pipeline_accepted()
        artifact_2 = test_rejected_not_forwarded()
        test_bucket_failure_with_retry()
        test_provenance_chain()
        
        logger.info("=" * 80)
        logger.info("ALL TESTS PASSED ✅")
        logger.info("=" * 80)
        
    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}", exc_info=True)
        sys.exit(1)
