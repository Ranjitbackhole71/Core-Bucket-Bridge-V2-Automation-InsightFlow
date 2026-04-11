"""
Bridge Integration - TANTRA Evaluation Pipeline
Injects evaluation pipeline into Bridge flow: validate → evaluate → filter → forward

STRICT RULES:
- DO NOT create standalone execution
- DO NOT call Core directly
- DO NOT write to Bucket directly from evaluation logic
- ONLY integrate within Bridge flow
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from .artifact_transformer import artifact_transformer
from .retry_handler import retry_handler

logger = logging.getLogger("bridge_integration")


class BridgeIntegration:
    """
    Integrates evaluation pipeline into Bridge flow.
    
    Execution order:
    1. validate (Sarathi) - already done by ProductOrchestrator
    2. evaluate (FINAL CONVERGENCE) - already done
    3. filter (decision == ACCEPTED?)
    4. forward (to Bucket via existing client)
    """
    
    def __init__(self, bucket_client=None):
        """
        Initialize Bridge integration.
        
        Args:
            bucket_client: Existing bucket client (injected, NOT created)
        """
        self.bucket_client = bucket_client
        self.integration_enabled = True
    
    def process_evaluation_artifact(
        self,
        evaluation_result: Dict[str, Any],
        input_data: Dict[str, Any],
        rule_id: str = "EVALUATION_GATE"
    ) -> Dict[str, Any]:
        """
        Process evaluation result through Bridge pipeline.
        
        Flow:
        1. Log validation acceptance
        2. Transform to artifact schema
        3. Log evaluation decision
        4. Filter: ONLY forward if ACCEPTED
        5. Forward to Bucket with retry logic
        6. Return result
        
        Args:
            evaluation_result: Output from evaluation pipeline
            input_data: Original input submission
            rule_id: Rule identifier
            
        Returns:
            Dict with artifact, forwarding status, and bucket response
        """
        # Step 1: Log validation acceptance
        logger.info("[VALIDATION] input accepted")
        
        # Step 2: Transform evaluation output → artifact
        artifact = artifact_transformer.transform(
            evaluation_result=evaluation_result,
            input_data=input_data,
            rule_id=rule_id
        )
        
        # Step 3: Log evaluation decision
        decision = artifact.get("decision", "REJECTED")
        logger.info(f"[EVALUATION] decision={decision}")
        
        # Step 4: Filter - ONLY forward if ACCEPTED
        if decision != "ACCEPTED":
            logger.warning(f"[FILTER] REJECTED artifact not forwarded to Bucket")
            return {
                "artifact": artifact,
                "forwarded": False,
                "reason": "decision=REJECTED",
                "bucket_response": None
            }
        
        # Step 5: Forward to Bucket (via existing client with retry)
        if not self.bucket_client:
            logger.error("[BUCKET] No bucket client configured - artifact dropped")
            return {
                "artifact": artifact,
                "forwarded": False,
                "reason": "no_bucket_client",
                "bucket_response": None
            }
        
        # Forward with retry logic
        def forward_operation():
            """Wrapper for bucket client call."""
            result = self.bucket_client.store_artifact(artifact)
            return {
                "artifact_id": result,
                "status": "ACCEPTED"
            }
        
        retry_result = retry_handler.execute_with_retry(
            operation=forward_operation,
            operation_name="bucket_forward"
        )
        
        # Step 6: Return complete result
        return {
            "artifact": artifact,
            "forwarded": retry_result.get("success", False),
            "bucket_response": retry_result,
            "provenance_hash": artifact.get("provenance_hash")
        }


# Singleton instance for Bridge integration
# NOTE: bucket_client must be injected before use
bridge_integration = BridgeIntegration()
