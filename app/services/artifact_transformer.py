"""
Artifact Transformer - TANTRA Integration
Converts evaluation output to Bridge artifact schema with deterministic hashing.

Rules:
- artifact_hash MUST be deterministic (SHA256 of canonical JSON)
- provenance_hash MUST chain: SHA256(previous_hash + artifact_hash)
- If no previous hash, use "GENESIS"
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional


class ArtifactTransformer:
    """Transforms evaluation output into Bridge-compatible artifact schema."""
    
    def __init__(self):
        self.previous_provenance_hash = "GENESIS"
    
    def transform(
        self,
        evaluation_result: Dict[str, Any],
        input_data: Dict[str, Any],
        rule_id: str = "EVALUATION_GATE"
    ) -> Dict[str, Any]:
        """
        Transform evaluation output to artifact schema.
        
        Args:
            evaluation_result: Output from evaluation pipeline (score, status, etc.)
            input_data: Original input submission data
            rule_id: Rule identifier for decision
            
        Returns:
            Artifact dict ready for Bridge forwarding
        """
        # Compute input_hash (deterministic)
        input_hash = self._compute_input_hash(input_data)
        
        # Determine decision
        status = evaluation_result.get("status", "fail").lower()
        decision = "ACCEPTED" if status in ["pass", "borderline"] else "REJECTED"
        
        # Build payload
        payload = {
            "score": evaluation_result.get("score", 0),
            "status": status,
            "readiness_percent": evaluation_result.get("readiness_percent", 0),
            "submission_id": evaluation_result.get("submission_id", ""),
            "evaluation_details": {
                k: v for k, v in evaluation_result.items()
                if k not in ["score", "status", "readiness_percent", "submission_id"]
            }
        }
        
        # Build artifact (without hashes first)
        timestamp = datetime.now(timezone.utc).isoformat()
        artifact = {
            "module": "evaluation",
            "input_hash": input_hash,
            "decision": decision,
            "rule_id": rule_id,
            "payload": payload,
            "timestamp": timestamp
        }
        
        # Compute artifact_hash (deterministic)
        artifact_hash = self._compute_artifact_hash(artifact)
        artifact["artifact_hash"] = artifact_hash
        
        # Compute provenance_hash (chain)
        provenance_hash = self._compute_provenance_hash(artifact_hash)
        artifact["provenance_hash"] = provenance_hash
        
        # Update previous hash for next artifact
        self.previous_provenance_hash = provenance_hash
        
        return artifact
    
    def _compute_input_hash(self, input_data: Dict[str, Any]) -> str:
        """Compute deterministic SHA256 hash of input data."""
        # Remove non-deterministic fields
        deterministic_input = {
            k: v for k, v in input_data.items()
            if k not in ["timestamp", "submission_id", "task_id"]
        }
        
        # Canonical JSON
        canonical_json = json.dumps(deterministic_input, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def _compute_artifact_hash(self, artifact: Dict[str, Any]) -> str:
        """Compute deterministic SHA256 hash of artifact (excluding hash fields)."""
        # Remove hash fields to avoid circular dependency
        artifact_copy = artifact.copy()
        artifact_copy.pop("artifact_hash", None)
        artifact_copy.pop("provenance_hash", None)
        
        # Canonical JSON
        canonical_json = json.dumps(artifact_copy, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
    def _compute_provenance_hash(self, artifact_hash: str) -> str:
        """Compute provenance hash chaining previous hash."""
        chain_input = self.previous_provenance_hash + artifact_hash
        return hashlib.sha256(chain_input.encode('utf-8')).hexdigest()
    
    def reset_chain(self):
        """Reset provenance chain to GENESIS."""
        self.previous_provenance_hash = "GENESIS"


# Singleton instance for Bridge integration
artifact_transformer = ArtifactTransformer()
