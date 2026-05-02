"""
Bridge Service - Logic-Neutral Gateway

STRICT CONSTRAINTS:
- ZERO intelligence (no evaluation, no scoring, no inference)
- NO ACCEPTED/REJECTED checks
- NO payload interpretation
- Authority token REQUIRED
- Trace IDs REQUIRED and forwarded UNCHANGED
- Read-back verification REQUIRED
"""
import logging
from typing import Dict, Any
import hashlib
import json

from .retry_handler import retry_handler

logger = logging.getLogger("bridge_service")


class BridgeService:
    """
    Logic-neutral gateway between Core and Bucket.
    
    Responsibilities:
    1. Validate authority_token (presence + basic structure)
    2. Enforce trace_id + execution_id (presence + immutability)
    3. Forward payload to Bucket (no inspection)
    4. Verify write (read-back + hash match + schema check)
    5. Compute provenance_hash (fetch previous from Bucket, NOT local)
    
    NOT Allowed:
    - Evaluation logic
    - ACCEPTED/REJECTED checks
    - Scoring or inference
    - Payload interpretation
    - Local state storage
    """
    
    def __init__(self, bucket_client=None):
        """
        Initialize Bridge service.
        
        Args:
            bucket_client: Existing bucket client (injected, NOT created)
        """
        self.bucket_client = bucket_client
    
    def validate_and_forward(
        self,
        execution_id: str,
        trace_id: str,
        authority_token: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate request and forward to Bucket.
        
        Flow:
        1. Validate authority_token (REQUIRED)
        2. Validate trace IDs (REQUIRED, NOT generated)
        3. Fetch previous_hash from Bucket (NOT local)
        4. Compute artifact_hash + provenance_hash
        5. Forward to Bucket with retry
        6. Read-back verification
        7. Return status
        
        Args:
            execution_id: Execution identifier (REQUIRED, NOT generated)
            trace_id: Trace identifier (REQUIRED, NOT modified)
            authority_token: Authority token (REQUIRED, validated)
            payload: Artifact payload (NOT inspected)
            
        Returns:
            {"status": "FORWARDED|BLOCKED", "reason": "...", "trace_id": "..."}
        """
        # === PHASE 1: AUTHORITY ENFORCEMENT ===
        
        # Check authority_token presence
        if not authority_token:
            logger.error(f"[BLOCKED] missing authority_token trace_id={trace_id}")
            return {
                "status": "BLOCKED",
                "reason": "missing_authority_token",
                "trace_id": trace_id
            }
        
        # Validate token structure (basic check)
        if not self._validate_authority_token(authority_token):
            logger.error(f"[BLOCKED] invalid authority_token trace_id={trace_id}")
            return {
                "status": "BLOCKED",
                "reason": "invalid_authority_token",
                "trace_id": trace_id
            }
        
        logger.info(f"[AUTHORITY] token validated trace_id={trace_id}")
        
        # === PHASE 2: TRACE ENFORCEMENT ===
        
        # Check trace IDs presence
        if not execution_id or not trace_id:
            logger.error(f"[BLOCKED] missing trace identifiers execution_id={execution_id} trace_id={trace_id}")
            return {
                "status": "BLOCKED",
                "reason": "missing_trace_ids",
                "trace_id": trace_id
            }
        
        # Trace IDs forwarded UNCHANGED (NOT generated, NOT modified)
        logger.info(f"[TRACE] execution_id={execution_id} trace_id={trace_id}")
        
        # === PHASE 3: PROVENANCE (Fetch from Bucket, NOT Local) ===
        
        # Fetch previous_hash from Bucket
        previous_hash = self._fetch_previous_hash_from_bucket()
        logger.info(f"[PROVENANCE] previous_hash={previous_hash[:16]}...")
        
        # Build artifact (schema-compliant)
        artifact = self._build_artifact(
            execution_id=execution_id,
            trace_id=trace_id,
            payload=payload,
            previous_hash=previous_hash
        )
        
        # === PHASE 4: FORWARD TO BUCKET ===
        
        if not self.bucket_client:
            logger.error(f"[BLOCKED] no bucket client configured trace_id={trace_id}")
            return {
                "status": "BLOCKED",
                "reason": "no_bucket_client",
                "trace_id": trace_id
            }
        
        # Forward with retry logic
        def forward_operation():
            """Write to Bucket with read-back verification."""
            # Write
            artifact_id = self.bucket_client.store_artifact(artifact)
            logger.info(f"[WRITE] artifact_id={artifact_id}")
            
            # Read-back
            stored_artifact = self.bucket_client.get_artifact(artifact_id)
            
            # Verify existence
            if not stored_artifact:
                raise Exception(f"Artifact {artifact_id} not found after write")
            
            # Verify hash match
            if stored_artifact.get("artifact_hash") != artifact["artifact_hash"]:
                raise Exception(
                    f"Hash mismatch: expected {artifact['artifact_hash']}, "
                    f"got {stored_artifact.get('artifact_hash')}"
                )
            
            # Verify schema (required fields)
            required_fields = [
                "artifact_id", "timestamp_utc", "schema_version",
                "source_module_id", "artifact_type", "parent_hash",
                "payload", "artifact_hash"
            ]
            for field in required_fields:
                if field not in stored_artifact:
                    raise Exception(f"Missing required field: {field}")
            
            # Log verified_write
            logger.info(f"[VERIFIED_WRITE] artifact_id={artifact_id} hash_match=True schema_valid=True")
            
            return {
                "artifact_id": artifact_id,
                "status": "FORWARDED",
                "verified_write": True
            }
        
        retry_result = retry_handler.execute_with_retry(
            operation=forward_operation,
            operation_name="bucket_forward"
        )
        
        # === PHASE 5: RETURN RESULT ===
        
        if retry_result.get("success"):
            logger.info(f"[FORWARDED] trace_id={trace_id} artifact_id={retry_result['artifact_id']}")
            return {
                "status": "FORWARDED",
                "reason": "artifact_stored_verified",
                "trace_id": trace_id,
                "artifact_id": retry_result["artifact_id"],
                "verified_write": True
            }
        else:
            logger.error(f"[FAILURE] trace_id={trace_id} error={retry_result.get('error')}")
            return {
                "status": "BLOCKED",
                "reason": f"bucket_write_failed: {retry_result.get('error')}",
                "trace_id": trace_id
            }
    
    def _validate_authority_token(self, token: str) -> bool:
        """
        Validate authority token structure.
        
        Basic validation: non-empty string, minimum length.
        NO cryptographic verification (handled by Core).
        
        Args:
            token: Authority token string
            
        Returns:
            True if valid structure, False otherwise
        """
        if not isinstance(token, str):
            return False
        if len(token) < 10:  # Minimum length check
            return False
        return True
    
    def _fetch_previous_hash_from_bucket(self) -> str:
        """
        Fetch previous artifact hash from Bucket.
        
        NO local state. NO memory cache.
        Always fetches from Bucket.
        
        Returns:
            Previous artifact hash, or "GENESIS" if none exists
        """
        try:
            latest = self.bucket_client.get_latest_artifact()
            if latest:
                return latest.get("artifact_hash", "GENESIS")
        except Exception as e:
            logger.warning(f"[PROVENANCE] failed to fetch previous hash: {e}")
        
        return "GENESIS"
    
    def _build_artifact(
        self,
        execution_id: str,
        trace_id: str,
        payload: Dict[str, Any],
        previous_hash: str
    ) -> Dict[str, Any]:
        """
        Build artifact with schema compliance.
        
        Schema:
        {
            "artifact_id": "<uuid>",
            "timestamp_utc": "<iso8601>",
            "schema_version": "1.0.0",
            "source_module_id": "<module>",
            "artifact_type": "telemetry_record",
            "parent_hash": "<previous_hash>",
            "payload": {...},
            "artifact_hash": "<sha256>"
        }
        
        Args:
            execution_id: Execution identifier (forwarded unchanged)
            trace_id: Trace identifier (forwarded unchanged)
            payload: Payload (NOT inspected)
            previous_hash: Previous artifact hash from Bucket
            
        Returns:
            Complete artifact dict
        """
        from datetime import datetime, timezone
        import uuid
        
        # Build artifact WITHOUT hash fields first
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
        
        Excludes self-referential fields (artifact_hash).
        Uses canonical JSON (sorted keys, no whitespace).
        
        Args:
            artifact: Artifact dict (without artifact_hash field)
            
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
# NOTE: bucket_client must be injected before use
bridge_service = BridgeService()
