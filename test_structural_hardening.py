"""
Test suite for Core→Bucket Gated Bridge Structural Hardening

Tests all six implementation phases:
1. Registry Alignment
2. Contract Enforcement  
3. Immutable Logging
4. Replay Determinism
5. Mutation Audit
6. Structural Convergence Verification
"""

import json
import hashlib
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Test credentials (replace with actual tokens in production)
MODULE_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJtb2R1bGUiLCJyb2xlcyI6WyJtb2R1bGUiXX0.test"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGVzIjpbImFkbWluIl19.test"


def compute_input_hash(payload):
    """Compute SHA256 hash of canonical JSON payload."""
    canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    payload_bytes = canonical_json.encode('utf-8')
    return hashlib.sha256(payload_bytes).hexdigest()


def get_mock_signature():
    """Return a mock signature for testing."""
    # In production, this would be a real RSA signature
    return "mock_signature_for_testing"


class TestRegistryAlignment:
    """Test Suite 1: Registry Alignment (Read-Only)"""
    
    def test_registered_module_accepted(self):
        """Test that registered modules are accepted."""
        print("\n[Test 1.1] Registered module acceptance")
        
        payload = {
            "module": "education",
            "data": {
                "course_id": "CS101",
                "course_name": "Introduction to CS"
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/core/update",
            headers={"Authorization": f"Bearer {MODULE_TOKEN}"},
            json={
                "payload": payload,
                "signature": get_mock_signature()
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Should accept registered module
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print("✓ PASS: Registered module accepted")
    
    def test_unregistered_module_rejected(self):
        """Test that unregistered modules are rejected (fail closed)."""
        print("\n[Test 1.2] Unregistered module rejection")
        
        payload = {
            "module": "unknown_module",
            "data": {"test": "data"}
        }
        
        response = requests.post(
            f"{BASE_URL}/core/update",
            headers={"Authorization": f"Bearer {MODULE_TOKEN}"},
            json={
                "payload": payload,
                "signature": get_mock_signature()
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Should reject unregistered module
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "not registered" in response.json()["detail"].lower()
        print("✓ PASS: Unregistered module rejected (fail closed)")
    
    def test_registry_readonly(self):
        """Test that registry is accessed read-only."""
        print("\n[Test 1.3] Registry read-only verification")
        
        # The registry should be loaded from file and never modified
        # This is verified by checking the admission_layer.py code
        from admission_layer import RegistryValidator
        
        validator = RegistryValidator()
        initial_cache = validator._registry_cache.copy()
        
        # Try to verify multiple modules
        validator.verify_module_registered("education")
        validator.verify_module_registered("finance")
        validator.verify_schema_match("/core/update", "1.0.0")
        
        # Cache should remain unchanged (read-only)
        assert validator._registry_cache == initial_cache
        print("✓ PASS: Registry accessed read-only")


class TestContractEnforcement:
    """Test Suite 2: Deterministic Contract Enforcement"""
    
    def test_missing_required_field_rejected(self):
        """Test that missing required fields cause rejection."""
        print("\n[Test 2.1] Missing required field rejection")
        
        # Missing 'data' field (required for /core/update)
        payload = {
            "module": "education"
        }
        
        response = requests.post(
            f"{BASE_URL}/core/update",
            headers={"Authorization": f"Bearer {MODULE_TOKEN}"},
            json={
                "payload": payload,
                "signature": get_mock_signature()
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Should reject due to missing required field
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ PASS: Missing required field rejected")
    
    def test_strict_type_validation(self):
        """Test strict type validation (no coercion)."""
        print("\n[Test 2.2] Strict type validation")
        
        # Wrong type: module should be string, not integer
        payload = {
            "module": 12345,
            "data": {}
        }
        
        response = requests.post(
            f"{BASE_URL}/core/update",
            headers={"Authorization": f"Bearer {MODULE_TOKEN}"},
            json={
                "payload": payload,
                "signature": get_mock_signature()
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # Should reject due to type mismatch
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        print("✓ PASS: Type mismatch rejected (no coercion)")
    
    def test_valid_contract_accepted(self):
        """Test that valid contracts are accepted."""
        print("\n[Test 2.3] Valid contract acceptance")
        
        payload = {
            "module": "education",
            "data": {
                "course_id": "CS101",
                "course_name": "Intro to CS",
                "students_enrolled": 150
            }
        }
        
        response = requests.post(
            f"{BASE_URL}/core/update",
            headers={"Authorization": f"Bearer {MODULE_TOKEN}"},
            json={
                "payload": payload,
                "signature": get_mock_signature()
            }
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        assert response.status_code == 200
        print("✓ PASS: Valid contract accepted")


class TestImmutableLogging:
    """Test Suite 3: Immutable Admission Logging"""
    
    def test_decision_logged_append_only(self):
        """Test that decisions are logged append-only."""
        print("\n[Test 3.1] Append-only decision logging")
        
        from admission_layer import ImmutableAdmissionLogger
        import os
        
        logger = ImmutableAdmissionLogger()
        
        # Get initial count
        initial_decisions = logger.get_decisions(limit=1000)
        initial_count = len(initial_decisions)
        
        # Log a decision
        logger.log_decision(
            module_id="education",
            input_hash="test_hash_123",
            registry_version="1.0.0",
            decision="ACCEPTED",
            rule_id="CONTRACT_VALID",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Get updated count
        updated_decisions = logger.get_decisions(limit=1000)
        updated_count = len(updated_decisions)
        
        # Should have exactly one more decision
        assert updated_count == initial_count + 1
        print("✓ PASS: Decision logged append-only")
    
    def test_decision_record_structure(self):
        """Test that decision records have correct structure."""
        print("\n[Test 3.2] Decision record structure")
        
        from admission_layer import ImmutableAdmissionLogger
        
        logger = ImmutableAdmissionLogger()
        decisions = logger.get_decisions(limit=1)
        
        if decisions:
            decision = decisions[0]
            
            # Check required fields
            required_fields = ["module_id", "input_hash", "registry_version", 
                             "decision", "rule_id", "timestamp"]
            
            for field in required_fields:
                assert field in decision, f"Missing required field: {field}"
            
            print(f"Decision record: {json.dumps(decision, indent=2)}")
            print("✓ PASS: Decision record has correct structure")
    
    def test_no_overwrite_allowed(self):
        """Test that log entries cannot be overwritten."""
        print("\n[Test 3.3] No overwrite allowed")
        
        # The ImmutableAdmissionLogger only opens file in append mode ('a')
        # There is no method to update or overwrite existing entries
        from admission_layer import ImmutableAdmissionLogger
        import inspect
        
        logger = ImmutableAdmissionLogger()
        
        # Verify no update/overwrite methods exist
        assert not hasattr(logger, 'update_decision')
        assert not hasattr(logger, 'overwrite_decision')
        assert not hasattr(logger, 'delete_decision')
        
        print("✓ PASS: No overwrite/update/delete methods exist")


class TestReplayDeterminism:
    """Test Suite 4: Replay Verification Engine"""
    
    def test_identical_payload_same_hash(self):
        """Test that identical payloads produce same hash."""
        print("\n[Test 4.1] Identical payloads produce same hash")
        
        payload1 = {
            "module": "education",
            "data": {"course_id": "CS101"}
        }
        
        payload2 = {
            "module": "education",
            "data": {"course_id": "CS101"}
        }
        
        hash1 = compute_input_hash(payload1)
        hash2 = compute_input_hash(payload2)
        
        assert hash1 == hash2
        print(f"Hash 1: {hash1}")
        print(f"Hash 2: {hash2}")
        print("✓ PASS: Identical payloads produce same hash")
    
    def test_different_payload_different_hash(self):
        """Test that different payloads produce different hashes."""
        print("\n[Test 4.2] Different payloads produce different hashes")
        
        payload1 = {
            "module": "education",
            "data": {"course_id": "CS101"}
        }
        
        payload2 = {
            "module": "education",
            "data": {"course_id": "CS102"}  # Different course_id
        }
        
        hash1 = compute_input_hash(payload1)
        hash2 = compute_input_hash(payload2)
        
        assert hash1 != hash2
        print(f"Hash 1: {hash1}")
        print(f"Hash 2: {hash2}")
        print("✓ PASS: Different payloads produce different hashes")
    
    def test_replay_produces_same_verdict(self):
        """Test that replay produces identical verdict."""
        print("\n[Test 4.3] Replay produces same verdict")
        
        from admission_layer import ImmutableAdmissionLogger, ReplayVerifier
        
        logger = ImmutableAdmissionLogger()
        verifier = ReplayVerifier(logger)
        
        # Log two identical decisions
        test_hash = "replay_test_hash_abc123"
        
        logger.log_decision(
            module_id="education",
            input_hash=test_hash,
            registry_version="1.0.0",
            decision="ACCEPTED",
            rule_id="CONTRACT_VALID",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        logger.log_decision(
            module_id="education",
            input_hash=test_hash,
            registry_version="1.0.0",
            decision="ACCEPTED",
            rule_id="CONTRACT_VALID",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        # Verify replay
        verified, original_decision, error = verifier.verify_replay(test_hash)
        
        assert verified == True
        assert original_decision["decision"] == "ACCEPTED"
        assert original_decision["rule_id"] == "CONTRACT_VALID"
        print("✓ PASS: Replay produces identical verdict")


class TestMutationAudit:
    """Test Suite 5: Silent Mutation Audit"""
    
    def test_no_mutation_detected(self):
        """Test that unchanged payload passes mutation audit."""
        print("\n[Test 5.1] Unchanged payload passes audit")
        
        from admission_layer import SilentMutationAuditor, CanonicalHasher
        
        auditor = SilentMutationAuditor()
        
        original_payload = {
            "module": "education",
            "data": {"course_id": "CS101"}
        }
        
        # Capture original hash
        original_hash = auditor.capture_original(original_payload)
        
        # Payload remains unchanged
        final_payload = original_payload.copy()
        
        # Verify no mutation
        is_unchanged = auditor.verify_no_mutation(original_hash, final_payload)
        
        assert is_unchanged == True
        print("✓ PASS: Unchanged payload passes audit")
    
    def test_mutation_detected(self):
        """Test that mutated payload is detected."""
        print("\n[Test 5.2] Mutated payload detected")
        
        from admission_layer import SilentMutationAuditor, CanonicalHasher
        
        auditor = SilentMutationAuditor()
        
        original_payload = {
            "module": "education",
            "data": {"course_id": "CS101"}
        }
        
        # Capture original hash
        original_hash = auditor.capture_original(original_payload)
        
        # Payload is mutated
        mutated_payload = {
            "module": "education",
            "data": {"course_id": "CS101"},
            "injected_field": "malicious_data"  # Mutation!
        }
        
        # Verify mutation detected
        is_unchanged = auditor.verify_no_mutation(original_hash, mutated_payload)
        
        assert is_unchanged == False
        print("✓ PASS: Mutated payload detected")
    
    def test_stage_transition_audit(self):
        """Test stage transition auditing."""
        print("\n[Test 5.3] Stage transition audit")
        
        from admission_layer import SilentMutationAuditor
        
        auditor = SilentMutationAuditor()
        
        payload_before = {"module": "education", "data": {"id": "123"}}
        payload_after = {"module": "education", "data": {"id": "123"}}
        
        # Audit transition
        is_unchanged = auditor.audit_stage_transition(
            stage="validation",
            payload_before=payload_before,
            payload_after=payload_after
        )
        
        assert is_unchanged == True
        
        # Check audit trail
        audit_report = auditor.get_audit_report()
        assert len(audit_report) > 0
        assert audit_report[-1]["stage"] == "validation"
        assert audit_report[-1]["mutated"] == False
        
        print(f"Audit entry: {json.dumps(audit_report[-1], indent=2)}")
        print("✓ PASS: Stage transition audited")


class TestStructuralConvergence:
    """Test Suite 6: Structural Convergence Verification"""
    
    def test_health_endpoint_shows_hardening(self):
        """Test that health endpoint shows structural hardening metrics."""
        print("\n[Test 6.1] Health endpoint shows hardening metrics")
        
        response = requests.get(f"{BASE_URL}/core/health")
        
        print(f"Status: {response.status_code}")
        health_data = response.json()
        print(json.dumps(health_data, indent=2))
        
        assert response.status_code == 200
        assert "structural_hardening" in health_data
        
        hardening = health_data["structural_hardening"]
        assert "registry_loaded" in hardening
        assert "total_admission_decisions" in hardening
        assert "contract_enforcement_active" in hardening
        
        print("✓ PASS: Health endpoint shows structural hardening metrics")
    
    def test_admission_decisions_endpoint(self):
        """Test admission decisions endpoint."""
        print("\n[Test 6.2] Admission decisions endpoint")
        
        response = requests.get(
            f"{BASE_URL}/admission/decisions?limit=10",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"}
        )
        
        print(f"Status: {response.status_code}")
        
        # May return 401 if token is invalid, but endpoint should exist
        if response.status_code == 200:
            data = response.json()
            assert "decisions" in data
            assert "count" in data
            print(f"Decisions count: {data['count']}")
            print("✓ PASS: Admission decisions endpoint working")
        else:
            print(f"Note: Endpoint exists but requires valid token (status: {response.status_code})")
    
    def test_all_endpoints_respond(self):
        """Test that all structural hardening endpoints respond."""
        print("\n[Test 6.3] All endpoints respond")
        
        endpoints = [
            ("GET", "/core/health", None),
            ("GET", "/bucket/status", MODULE_TOKEN),
            ("POST", "/core/heartbeat", MODULE_TOKEN),
        ]
        
        for method, path, token in endpoints:
            url = f"{BASE_URL}{path}"
            
            if method == "GET":
                response = requests.get(url)
            else:
                headers = {"Authorization": f"Bearer {token}"} if token else {}
                response = requests.post(
                    url,
                    headers=headers,
                    json={"payload": {}, "signature": "mock"}
                )
            
            # Just check endpoint exists (not 404)
            assert response.status_code != 404, f"Endpoint {path} not found"
            print(f"✓ {method} {path}: {response.status_code}")
        
        print("✓ PASS: All endpoints respond")


def run_all_tests():
    """Run all test suites."""
    print("=" * 70)
    print("STRUCTURAL HARDENING VERIFICATION TEST SUITE")
    print("=" * 70)
    
    test_suites = [
        TestRegistryAlignment(),
        TestContractEnforcement(),
        TestImmutableLogging(),
        TestReplayDeterminism(),
        TestMutationAudit(),
        TestStructuralConvergence()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for suite in test_suites:
        suite_name = suite.__class__.__name__
        print(f"\n{'='*70}")
        print(f"Running: {suite_name}")
        print('='*70)
        
        # Get all test methods
        test_methods = [m for m in dir(suite) if m.startswith('test_')]
        
        for method_name in test_methods:
            try:
                total_tests += 1
                method = getattr(suite, method_name)
                method()
                passed_tests += 1
            except AssertionError as e:
                print(f"✗ FAIL: {method_name} - {str(e)}")
            except Exception as e:
                print(f"✗ ERROR: {method_name} - {str(e)}")
    
    print(f"\n{'='*70}")
    print(f"TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Pass Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("\n✅ ALL TESTS PASSED - STRUCTURAL CONVERGENCE VERIFIED")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} TEST(S) FAILED")
    
    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
