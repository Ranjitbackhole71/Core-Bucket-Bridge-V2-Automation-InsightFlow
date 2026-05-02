"""
Artifact Transformer - Schema-Only (NO Intelligence)

STRICT CONSTRAINTS:
- NO evaluation logic
- NO ACCEPTED/REJECTED checks
- NO scoring or inference
- NO payload interpretation
- NO local state storage
- Schema transformation ONLY
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Any


class ArtifactTransformer:
    """
    Schema-only transformer.
    
    Responsibilities:
    1. Build artifact dict from payload (NO inspection)
    2. Compute artifact_hash (deterministic)
    
    NOT Allowed:
    - Decision logic (ACCEPTED/REJECTED)
    - Status mapping
    - Payload interpretation
    - Local chain state
    """
    
    def __init__(self):
        # NO local state for chain
        pass
    
    def transform(
        self,
        payload: Dict[str, Any],
        execution_id: str,
        trace_id: str,
        previous_hash: str = "GENESIS"
    ) -> Dict[str, Any]:
        """
        Transform payload to artifact schema.
        
        NO evaluation. NO decision logic. Schema ONLY.
        
        Args:
            payload: Raw payload (NOT inspected)
            execution_id: Execution identifier (forwarded UNCHANGED)
            trace_id: Trace identifier (forwarded UNCHANGED)
            previous_hash: Previous artifact hash from Bucket
            
        Returns:
            Artifact dict (schema-compliant)
        """
        import uuid
        
        # Build artifact WITHOUT hash field
        artifact = {
            "artifact_id": str(uuid.uuid4()),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "schema_version": "1.0.0",
            "source_module_id": "evaluation",
            "artifact_type": "telemetry_record",
            "parent_hash": previous_hash,
            "execution_id": execution_id,  # Forwarded UNCHANGED
            "trace_id": trace_id,          # Forwarded UNCHANGED
            "payload": payload             # NOT inspected
        }
        
        # Compute artifact_hash (deterministic)
        artifact_hash = self._compute_artifact_hash(artifact)
        artifact["artifact_hash"] = artifact_hash
        
        return artifact
    
    def _compute_artifact_hash(self, artifact: Dict[str, Any]) -> str:
        """
        Compute deterministic SHA256 hash of artifact.
        
        Excludes self-referential fields.
        Uses canonical JSON.
        
        Args:
            artifact: Artifact dict (without artifact_hash)
            
        Returns:
            SHA256 hex digest
        """
        # Remove hash field to avoid circular dependency
        artifact_copy = artifact.copy()
        artifact_copy.pop("artifact_hash", None)
        
        # Canonical JSON (sorted keys, no whitespace)
        canonical_json = json.dumps(artifact_copy, sort_keys=True, separators=(',', ':'))
        
        # SHA256 hash
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()


# Singleton instance
artifact_transformer = ArtifactTransformer()
