"""
Retry Handler — Exponential backoff for transient failures.

Rules:
- Retry MAX 2 times
- Exponential backoff: attempt 1 = base_delay_ms, attempt 2 = base_delay_ms * 2
- If still failing: log failure, DO NOT silently drop
"""
import time
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger("retry_handler")


class RetryHandler:
    def __init__(self, max_retries: int = 2, base_delay_ms: int = 100):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms

    def execute_with_retry(
        self,
        operation: Callable,
        operation_name: str = "operation",
        **kwargs
    ) -> Dict[str, Any]:
        last_exception = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(f"[RETRY] {operation_name} attempt={attempt}")
                result = operation(**kwargs)
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt,
                }
            except Exception as e:
                last_exception = e
                logger.error(f"[RETRY] {operation_name} attempt={attempt} failed: {e}")
                if attempt < self.max_retries:
                    delay_ms = self.base_delay_ms * (2 ** (attempt - 1))
                    delay_sec = delay_ms / 1000.0
                    logger.warning(f"[RETRY] waiting {delay_ms}ms")
                    time.sleep(delay_sec)

        logger.error(f"[RETRY] {operation_name} FAILED after {self.max_retries} retries")
        return {
            "success": False,
            "error": str(last_exception),
            "attempts": self.max_retries,
        }


retry_handler = RetryHandler(max_retries=2, base_delay_ms=100)
