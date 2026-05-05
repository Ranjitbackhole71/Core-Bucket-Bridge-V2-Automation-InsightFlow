"""
Bridge Gateway — HTTP Entry Point

Receives Core requests, delegates to TantraBridge.
All authority validation, execution, and persistence happen in the bridge layer.
"""
import logging
from fastapi import APIRouter
from typing import Dict, Any

from ..services.bridge_integration import tantra_bridge

logger = logging.getLogger("bridge_gateway")

router = APIRouter()


@router.post("/validate_and_forward")
def validate_and_forward(request: Dict[str, Any]) -> Dict[str, Any]:
    execution_id = request.get("execution_id")
    trace_id = request.get("trace_id")
    authority_token = request.get("authority_token")
    payload = request.get("payload")

    result = tantra_bridge.process(
        trace_id=trace_id,
        execution_id=execution_id,
        authority_token=authority_token,
        payload=payload or {},
    )

    return result
