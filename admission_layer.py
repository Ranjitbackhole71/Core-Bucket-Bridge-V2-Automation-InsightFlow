import json
import hashlib
import os
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

class RegistryValidator:
    """Read-only registry validator for module and schema verification."""
    
    def __init__(self, registry_path: str = "registry.json"):
        self.registry_path = registry_path
        self._registry_cache = None
        self._load_registry()
    
    def _load_registry(self):
        """Load registry from file (read-only operation)."""
        try:
            if os.path.exists(self.registry_path):
                with open(self.registry_path, 'r', encoding='utf-8') as f:
                    self._registry_cache = json.load(f)
            else:
                self._registry_cache = {"modules": {}, "schema_definitions": {}}
        except Exception as e:
            raise RuntimeError(f"Failed to load registry: {str(e)}")
    
    def verify_module_registered(self, module_id: str) -> Tuple[bool, Optional[str]]:
        """
        Verify if module exists in registry.
        Returns (is_registered, schema_version).
        Fail closed if module not found.
        """
        modules = self._registry_cache.get("modules", {})
        if module_id not in modules:
            return False, None
        
        schema_version = modules[module_id].get("schema_version")
        return True, schema_version
    
    def verify_schema_match(self, endpoint: str, payload_schema_version: str) -> bool:
        """
        Verify if payload schema version matches registry.
        Returns True if versions match, False otherwise.
        """
        schema_defs = self._registry_cache.get("schema_definitions", {})
        if endpoint not in schema_defs:
            return False
        
        registry_version = schema_defs[endpoint].get("version")
        return registry_version == payload_schema_version
    
    def get_endpoint_schema(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Get schema definition for endpoint (read-only)."""
        schema_defs = self._registry_cache.get("schema_definitions", {})
        return schema_defs.get(endpoint)
    
    def get_module_config(self, module_id: str) -> Optional[Dict[str, Any]]:
        """Get module configuration from registry (read-only)."""
        modules = self._registry_cache.get("modules", {})
        return modules.get(module_id)


class CanonicalHasher:
    """Deterministic hasher using canonical JSON representation."""
    
    @staticmethod
    def compute_input_hash(payload: Dict[str, Any]) -> str:
        """
        Compute SHA256 hash of canonical JSON payload.
        
        Canonical rules:
        - JSON sorted keys
        - UTF-8 encoding
        - No whitespace mutation
        """
        # Sort keys and remove whitespace
        canonical_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        
        # Encode to UTF-8
        payload_bytes = canonical_json.encode('utf-8')
        
        # Compute SHA256
        input_hash = hashlib.sha256(payload_bytes).hexdigest()
        
        return input_hash


class ImmutableAdmissionLogger:
    """Append-only admission decision logger."""
    
    def __init__(self, log_path: str = "logs/admission_decisions.jsonl"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        # Create empty log file if it doesn't exist
        if not os.path.exists(log_path):
            with open(log_path, 'w', encoding='utf-8') as f:
                pass  # Create empty file
    
    def log_decision(self, 
                     module_id: str,
                     input_hash: str,
                     registry_version: str,
                     decision: str,
                     rule_id: str,
                     timestamp: str):
        """
        Append admission decision to log (immutable, append-only).
        
        Rules:
        - Logs are append-only
        - No overwrite allowed
        - No update allowed
        - Each decision stored as new entry
        """
        decision_record = {
            "module_id": module_id,
            "input_hash": input_hash,
            "registry_version": registry_version,
            "decision": decision,
            "rule_id": rule_id,
            "timestamp": timestamp
        }
        
        # Append-only write
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(decision_record, sort_keys=True) + '\n')
    
    def get_decisions(self, limit: int = 100) -> list:
        """Read last N decisions (for verification/replay)."""
        decisions = []
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Return last N entries
                for line in lines[-limit:]:
                    if line.strip():
                        decisions.append(json.loads(line))
        except FileNotFoundError:
            pass
        return decisions


class ContractValidator:
    """Strict JSON schema contract enforcer."""
    
    def __init__(self, registry_validator: RegistryValidator):
        self.registry_validator = registry_validator
    
    def validate_contract(self, endpoint: str, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate payload against strict JSON schema.
        
        Returns: (is_valid, error_message, rule_id)
        
        Rules:
        - strict validation
        - no silent defaults
        - no auto-coercion
        - no missing fields allowed
        """
        schema = self.registry_validator.get_endpoint_schema(endpoint)
        if not schema:
            return False, f"No schema defined for endpoint: {endpoint}", "SCHEMA_NOT_FOUND"
        
        required_fields = schema.get("required_fields", [])
        field_types = schema.get("field_types", {})
        
        # Check required fields
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}", "MISSING_REQUIRED_FIELD"
        
        # Check field types (strict, no coercion)
        for field, expected_type in field_types.items():
            if field in payload:
                value = payload[field]
                if not self._check_type(value, expected_type):
                    return False, f"Field '{field}' must be of type {expected_type}", "TYPE_MISMATCH"
        
        return True, None, "CONTRACT_VALID"
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check value type strictly (no coercion)."""
        type_map = {
            "string": str,
            "object": dict,
            "array": list,
            "number": (int, float),
            "integer": int,
            "boolean": bool
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type is None:
            return True  # Unknown type, allow
        
        return isinstance(value, expected_python_type)


class SilentMutationAuditor:
    """Audit trail for detecting payload mutations."""
    
    def __init__(self):
        self.audit_log = []
    
    def capture_original(self, payload: Dict[str, Any]) -> str:
        """Capture original payload hash for comparison."""
        return CanonicalHasher.compute_input_hash(payload)
    
    def verify_no_mutation(self, original_hash: str, final_payload: Dict[str, Any]) -> bool:
        """Verify payload was not mutated during processing."""
        final_hash = CanonicalHasher.compute_input_hash(final_payload)
        return original_hash == final_hash
    
    def audit_stage_transition(self, stage: str, payload_before: Dict[str, Any], 
                               payload_after: Dict[str, Any]) -> bool:
        """
        Audit transition between processing stages.
        
        Check path: request → validation → admission → logging
        
        Returns True if no mutation detected.
        """
        hash_before = CanonicalHasher.compute_input_hash(payload_before)
        hash_after = CanonicalHasher.compute_input_hash(payload_after)
        
        audit_entry = {
            "stage": stage,
            "hash_before": hash_before,
            "hash_after": hash_after,
            "mutated": hash_before != hash_after,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.audit_log.append(audit_entry)
        return hash_before == hash_after
    
    def get_audit_report(self) -> list:
        """Return complete audit trail."""
        return self.audit_log.copy()


class ReplayVerifier:
    """Deterministic replay verification engine."""
    
    def __init__(self, admission_logger: ImmutableAdmissionLogger):
        self.admission_logger = admission_logger
        self.replay_cache = {}  # input_hash -> first_decision
    
    def verify_replay(self, input_hash: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Verify replay produces identical verdict.
        
        Verification rules:
        - input_hash identical
        - decision identical
        - rule_id identical
        
        Returns: (replay_verified, original_decision, error_message)
        """
        # Get all decisions with this input_hash
        decisions = self.admission_logger.get_decisions(limit=1000)
        matching_decisions = [d for d in decisions if d.get("input_hash") == input_hash]
        
        if len(matching_decisions) == 0:
            return False, None, "No previous decisions found for this input_hash"
        
        if len(matching_decisions) == 1:
            # First occurrence, cache it
            self.replay_cache[input_hash] = matching_decisions[0]
            return True, matching_decisions[0], None
        
        # Multiple occurrences - verify they're all identical
        first_decision = matching_decisions[0]
        for decision in matching_decisions[1:]:
            if (decision.get("decision") != first_decision.get("decision") or
                decision.get("rule_id") != first_decision.get("rule_id")):
                return False, first_decision, "Replay produced different verdict"
        
        return True, first_decision, None
    
    def get_replay_history(self, input_hash: str) -> list:
        """Get all replay instances for a given input_hash."""
        decisions = self.admission_logger.get_decisions(limit=1000)
        return [d for d in decisions if d.get("input_hash") == input_hash]
