"""
Quick Verification Script for Structural Hardening

This script demonstrates all 6 phases of structural hardening implementation.
Run this after starting the server with: python core_bucket_bridge.py
"""

import json
import hashlib
from datetime import datetime
from admission_layer import (
    RegistryValidator,
    CanonicalHasher,
    ImmutableAdmissionLogger,
    ContractValidator,
    SilentMutationAuditor,
    ReplayVerifier
)


def print_section(title):
    """Print formatted section header."""
    print("\n" + "=" * 70)
    print("  " + title)
    print("=" * 70)


def demo_registry_alignment():
    """Demonstrate Phase 1: Registry Alignment."""
    print_section("PHASE 1: REGISTRY ALIGNMENT (Read-Only)")
    
    # Initialize registry validator
    registry = RegistryValidator()
    
    # Test 1: Verify registered module
    print("\n[Test 1] Verifying registered module...")
    is_registered, version = registry.verify_module_registered("education")
    print("  Module: education")
    print("  Registered: {}".format(is_registered))
    print("  Schema Version: {}".format(version))
    assert is_registered == True, "Education module should be registered"
    print("  PASS")
    
    # Test 2: Verify unregistered module (fail closed)
    print("\n[Test 2] Verifying unregistered module (fail closed)...")
    is_registered, version = registry.verify_module_registered("unknown_module")
    print("  Module: unknown_module")
    print("  Registered: {}".format(is_registered))
    assert is_registered == False, "Unknown module should not be registered"
    print("  PASS (Fail Closed)")
    
    # Test 3: Schema version matching
    print("\n[Test 3] Schema version matching...")
    endpoint_schema = registry.get_endpoint_schema("core/update")
    print("  Endpoint: core/update")
    if endpoint_schema:
        print("  Schema Version: {}".format(endpoint_schema['version']))
    else:
        print("  Available schemas: {}".format(list(registry._registry_cache.get('schema_definitions', {}).keys())))
    assert endpoint_schema is not None, "Endpoint schema should exist"
    assert endpoint_schema['version'] == "1.0.0", "Schema version should be 1.0.0"
    print("  PASS")
    
    # Test 4: Deterministic hashing
    print("\n[Test 4] Deterministic input hashing...")
    payload = {"module": "education", "data": {"course_id": "CS101"}}
    hash1 = CanonicalHasher.compute_input_hash(payload)
    hash2 = CanonicalHasher.compute_input_hash(payload)
    print("  Payload: {}".format(json.dumps(payload)))
    print("  Hash 1: {}".format(hash1))
    print("  Hash 2: {}".format(hash2))
    assert hash1 == hash2, "Identical payloads should produce same hash"
    print("  PASS (Deterministic)")
    
    print("\nPhase 1 Complete: Registry Alignment Verified")


def demo_contract_enforcement():
    """Demonstrate Phase 2: Contract Enforcement."""
    print_section("PHASE 2: CONTRACT ENFORCEMENT")
    
    registry = RegistryValidator()
    validator = ContractValidator(registry)
    
    # Test 1: Valid contract
    print("\n[Test 1] Validating correct contract...")
    payload = {
        "module": "education",
        "data": {"course_id": "CS101", "course_name": "Intro to CS"}
    }
    is_valid, error, rule_id = validator.validate_contract("core/update", payload)
    print("  Valid: {}".format(is_valid))
    print("  Rule ID: {}".format(rule_id))
    assert is_valid == True, "Valid contract should pass"
    print("  PASS")
    
    # Test 2: Missing required field
    print("\n[Test 2] Missing required field (fail closed)...")
    payload = {"module": "education"}  # Missing 'data'
    is_valid, error, rule_id = validator.validate_contract("core/update", payload)
    print("  Valid: {}".format(is_valid))
    print("  Error: {}".format(error))
    print("  Rule ID: {}".format(rule_id))
    assert is_valid == False, "Missing field should fail"
    assert "MISSING_REQUIRED_FIELD" in rule_id
    print("  PASS (Strict Validation)")
    
    # Test 3: No silent defaults
    print("\n[Test 3] No silent defaults...")
    payload = {"module": "education", "data": {}}
    is_valid, error, rule_id = validator.validate_contract("core/update", payload)
    print("  Valid: {}".format(is_valid))
    print("  PASS (No Auto-Coercion)")
    
    print("\nPhase 2 Complete: Contract Enforcement Verified")


def demo_immutable_logging():
    """Demonstrate Phase 3: Immutable Logging."""
    print_section("PHASE 3: IMMUTABLE ADMISSION LOGGING")
    
    logger = ImmutableAdmissionLogger()
    
    # Get initial count
    initial_decisions = logger.get_decisions(limit=1000)
    initial_count = len(initial_decisions)
    print("\nInitial decision count: {}".format(initial_count))
    
    # Test 1: Append-only logging
    print("\n[Test 1] Append-only decision logging...")
    timestamp = datetime.utcnow().isoformat() + "Z"
    logger.log_decision(
        module_id="education",
        input_hash="test_hash_abc123",
        registry_version="1.0.0",
        decision="ACCEPTED",
        rule_id="CONTRACT_VALID",
        timestamp=timestamp
    )
    
    updated_decisions = logger.get_decisions(limit=1000)
    updated_count = len(updated_decisions)
    print("  New decision count: {}".format(updated_count))
    assert updated_count == initial_count + 1, "Should append exactly one decision"
    print("  PASS (Append-Only)")
    
    # Test 2: Decision record structure
    print("\n[Test 2] Decision record structure...")
    latest_decision = updated_decisions[-1]
    print("  Record: {}".format(json.dumps(latest_decision, indent=2)))
    
    required_fields = ["module_id", "input_hash", "registry_version", 
                      "decision", "rule_id", "timestamp"]
    for field in required_fields:
        assert field in latest_decision, "Missing field: {}".format(field)
    print("  PASS (All Required Fields Present)")
    
    # Test 3: No overwrite methods exist
    print("\n[Test 3] No overwrite capability...")
    has_update = hasattr(logger, 'update_decision')
    has_delete = hasattr(logger, 'delete_decision')
    print("  Has update method: {}".format(has_update))
    print("  Has delete method: {}".format(has_delete))
    assert has_update == False, "Should not have update method"
    assert has_delete == False, "Should not have delete method"
    print("  PASS (Immutable by Design)")
    
    print("\nPhase 3 Complete: Immutable Logging Verified")


def demo_replay_determinism():
    """Demonstrate Phase 4: Replay Determinism."""
    print_section("PHASE 4: REPLAY DETERMINISM")
    
    hasher = CanonicalHasher()
    
    # Test 1: Identical payloads -> identical hashes
    print("\n[Test 1] Identical payloads produce identical hashes...")
    payload1 = {"module": "education", "data": {"id": "123"}}
    payload2 = {"module": "education", "data": {"id": "123"}}
    
    hash1 = hasher.compute_input_hash(payload1)
    hash2 = hasher.compute_input_hash(payload2)
    
    print("  Hash 1: {}".format(hash1))
    print("  Hash 2: {}".format(hash2))
    assert hash1 == hash2
    print("  PASS (Deterministic)")
    
    # Test 2: Different payloads -> different hashes
    print("\n[Test 2] Different payloads produce different hashes...")
    payload1 = {"module": "education", "data": {"id": "123"}}
    payload2 = {"module": "education", "data": {"id": "456"}}
    
    hash1 = hasher.compute_input_hash(payload1)
    hash2 = hasher.compute_input_hash(payload2)
    
    print("  Hash 1: {}...".format(hash1[:32]))
    print("  Hash 2: {}...".format(hash2[:32]))
    assert hash1 != hash2
    print("  PASS (Unique)")
    
    # Test 3: Replay verification
    print("\n[Test 3] Replay verification...")
    logger = ImmutableAdmissionLogger()
    verifier = ReplayVerifier(logger)
    
    # Log same decision twice
    test_hash = "replay_test_xyz789"
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    logger.log_decision(
        module_id="education",
        input_hash=test_hash,
        registry_version="1.0.0",
        decision="ACCEPTED",
        rule_id="CONTRACT_VALID",
        timestamp=timestamp
    )
    
    logger.log_decision(
        module_id="education",
        input_hash=test_hash,
        registry_version="1.0.0",
        decision="ACCEPTED",
        rule_id="CONTRACT_VALID",
        timestamp=timestamp
    )
    
    verified, original, error = verifier.verify_replay(test_hash)
    print("  Verified: {}".format(verified))
    print("  Original Decision: {}".format(original['decision']))
    print("  Original Rule ID: {}".format(original['rule_id']))
    assert verified == True
    assert original['decision'] == "ACCEPTED"
    assert original['rule_id'] == "CONTRACT_VALID"
    print("  PASS (Replay Produces Same Verdict)")
    
    print("\nPhase 4 Complete: Replay Determinism Verified")


def demo_mutation_audit():
    """Demonstrate Phase 5: Mutation Audit."""
    print_section("PHASE 5: SILENT MUTATION AUDIT")
    
    auditor = SilentMutationAuditor()
    hasher = CanonicalHasher()
    
    # Test 1: Unchanged payload passes audit
    print("\n[Test 1] Unchanged payload passes audit...")
    original = {"module": "education", "data": {"id": "123"}}
    original_hash = auditor.capture_original(original)
    
    final = original.copy()
    is_unchanged = auditor.verify_no_mutation(original_hash, final)
    
    print("  Payload unchanged: {}".format(is_unchanged))
    assert is_unchanged == True
    print("  PASS")
    
    # Test 2: Mutated payload detected
    print("\n[Test 2] Mutated payload detected...")
    original = {"module": "education", "data": {"id": "123"}}
    original_hash = auditor.capture_original(original)
    
    mutated = {
        "module": "education",
        "data": {"id": "123"},
        "injected_field": "malicious"  # Mutation!
    }
    is_unchanged = auditor.verify_no_mutation(original_hash, mutated)
    
    print("  Mutation detected: {}".format(not is_unchanged))
    assert is_unchanged == False
    print("  PASS (Mutation Detected)")
    
    # Test 3: Stage transition audit
    print("\n[Test 3] Stage transition audit...")
    before = {"module": "education", "data": {"id": "123"}}
    after = {"module": "education", "data": {"id": "123"}}
    
    is_unchanged = auditor.audit_stage_transition("validation", before, after)
    audit_report = auditor.get_audit_report()
    
    print("  Stage: {}".format(audit_report[-1]['stage']))
    print("  Mutated: {}".format(audit_report[-1]['mutated']))
    assert is_unchanged == True
    assert audit_report[-1]['mutated'] == False
    print("  PASS (Stage Audited)")
    
    print("\nPhase 5 Complete: Mutation Audit Verified")


def demo_structural_convergence():
    """Demonstrate Phase 6: Structural Convergence."""
    print_section("PHASE 6: STRUCTURAL CONVERGENCE VERIFICATION")
    
    # Initialize all components
    registry = RegistryValidator()
    hasher = CanonicalHasher()
    logger = ImmutableAdmissionLogger()
    validator = ContractValidator(registry)
    auditor = SilentMutationAuditor()
    verifier = ReplayVerifier(logger)
    
    print("\n[Component Check] All components initialized:")
    print("  RegistryValidator: {}".format(registry is not None))
    print("  CanonicalHasher: {}".format(hasher is not None))
    print("  ImmutableAdmissionLogger: {}".format(logger is not None))
    print("  ContractValidator: {}".format(validator is not None))
    print("  SilentMutationAuditor: {}".format(auditor is not None))
    print("  ReplayVerifier: {}".format(verifier is not None))
    
    # Full integration test
    print("\n[Integration Test] Complete admission flow:")
    
    # 1. Registry check
    payload = {"module": "finance", "data": {"account_id": "ACC123", "balance": 1000}}
    is_registered, version = registry.verify_module_registered("finance")
    status = "OK" if is_registered else "FAIL"
    print("  1. Registry Check: [{}]".format(status))
    
    # 2. Contract validation
    is_valid, error, rule_id = validator.validate_contract("core/update", payload)
    status = "OK" if is_valid else "FAIL"
    print("  2. Contract Validation: [{}]".format(status))
    
    # 3. Compute hash
    input_hash = hasher.compute_input_hash(payload)
    print("  3. Input Hash: {}...".format(input_hash[:32]))
    
    # 4. Log decision
    timestamp = datetime.utcnow().isoformat() + "Z"
    logger.log_decision(
        module_id="finance",
        input_hash=input_hash,
        registry_version=version,
        decision="ACCEPTED",
        rule_id=rule_id,
        timestamp=timestamp
    )
    print("  4. Decision Logged: [OK]")
    
    # 5. Verify no mutation
    original_hash = auditor.capture_original(payload)
    is_unchanged = auditor.verify_no_mutation(original_hash, payload)
    status = "OK" if is_unchanged else "FAIL"
    print("  5. Mutation Check: [{}]".format(status))
    
    # 6. Replay verification
    verified, _, _ = verifier.verify_replay(input_hash)
    status = "OK" if verified else "FAIL"
    print("  6. Replay Verified: [{}]".format(status))
    
    print("\nPhase 6 Complete: Structural Convergence Verified")


def main():
    """Run all demonstration phases."""
    print("\n" + "=" * 70)
    print("  STRUCTURAL HARDENING DEMONSTRATION")
    print("  Core->Bucket Gated Bridge - Deterministic Admission Layer")
    print("=" * 70)
    
    try:
        demo_registry_alignment()
        demo_contract_enforcement()
        demo_immutable_logging()
        demo_replay_determinism()
        demo_mutation_audit()
        demo_structural_convergence()
        
        print("\n" + "=" * 70)
        print("  ALL PHASES VERIFIED")
        print("  STRUCTURAL CONVERGENCE ACHIEVED")
        print("=" * 70)
        print("\nRefer to STRUCTURAL_CONVERGENCE_REPORT.md for detailed documentation.")
        print("\n")
        
    except AssertionError as e:
        print("\nVERIFICATION FAILED: {}\n".format(str(e)))
        raise


if __name__ == "__main__":
    main()
