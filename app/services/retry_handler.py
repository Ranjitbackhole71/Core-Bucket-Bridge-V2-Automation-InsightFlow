"""
Retry Handler - TANTRA Integration
Handles retry logic with exponential backoff for Bucket forwarding failures.

Rules:
- Retry MAX 2 times
- Exponential backoff: attempt 1 = 500ms, attempt 2 = 1000ms
- If still failing: log failure, DO NOT silently drop
"""
import time
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger("retry_handler")


class RetryHandler:
    """Handles retry logic with exponential backoff."""
    
    def __init__(self, max_retries: int = 2, base_delay_ms: int = 500):
        """
        Initialize retry handler.
        
        Args:
            max_retries: Maximum number of retry attempts (default: 2)
            base_delay_ms: Base delay in milliseconds (default: 500ms)
        """
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
    
    def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "bucket_forward",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute operation with retry logic.
        
        Args:
            operation: Callable to execute (must return dict with artifact_id)
            operation_name: Name for logging purposes
            **kwargs: Arguments to pass to operation
            
        Returns:
            Dict with artifact_id and status on success
            
        Raises:
            Exception: Final exception after all retries exhausted
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[FORWARDING] sending to bucket (attempt {attempt})")
                
                # Execute operation
                result = operation(**kwargs)
                
                # Success
                artifact_id = result.get("artifact_id", "unknown")
                status = result.get("status", "ACCEPTED")
                logger.info(f"[BUCKET_RESPONSE] artifact_id={artifact_id}, status={status}")
                
                return {
                    "success": True,
                    "artifact_id": artifact_id,
                    "status": status,
                    "attempts": attempt
                }
                
            except Exception as e:
                last_exception = e
                logger.error(f"[RETRY] attempt {attempt} failed: {str(e)}")
                
                # If not last attempt, wait with exponential backoff
                if attempt < self.max_retries:
                    delay_ms = self.base_delay_ms * (2 ** (attempt - 1))
                    delay_sec = delay_ms / 1000.0
                    logger.warning(f"[RETRY] waiting {delay_ms}ms before next attempt")
                    time.sleep(delay_sec)
        
        # All retries exhausted
        logger.error(f"[FAILURE] final failure after {self.max_retries} retries: {str(last_exception)}")
        
        return {
            "success": False,
            "error": str(last_exception),
            "attempts": self.max_retries
        }


# Singleton instance for Bridge integration
retry_handler = RetryHandler(max_retries=2, base_delay_ms=500)
