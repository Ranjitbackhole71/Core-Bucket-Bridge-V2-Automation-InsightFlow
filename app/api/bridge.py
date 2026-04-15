"""
Bridge API - Strict Contract Enforcement

Endpoint: POST /validate_and_forward
Input: {execution_id, trace_id, authority_token, payload}
Output: {status: "FORWARDED|BLOCKED", reason, trace_id}
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict

from ..services.bridge_integration import bridge_service

router = APIRouter(prefix="/bridge", tags=["bridge"])


class BridgeRequest(BaseModel):
    execution_id: str
    trace_id: str
    authority_token: str
    payload: Dict[str, Any]


class BridgeResponse(BaseModel):
    status: str  # "FORWARDED" or "BLOCKED"
    reason: str
    trace_id: str
    artifact_id: str = None
    verified_write: bool = None


@router.post("/validate_and_forward", response_model=BridgeResponse)
async def validate_and_forward(request: BridgeRequest):
    """
    Validate authority token and forward payload to Bucket.
    
    STRICT CONSTRAINTS:
    - authority_token REQUIRED
    - execution_id + trace_id REQUIRED (NOT generated)
    - NO evaluation logic
    - NO ACCEPTED/REJECTED checks
    - Payload NOT inspected
    
    Args:
        request: BridgeRequest with execution_id, trace_id, authority_token, payload
        
    Returns:
        BridgeResponse with status, reason, trace_id
    """
    result = bridge_service.validate_and_forward(
        execution_id=request.execution_id,
        trace_id=request.trace_id,
        authority_token=request.authority_token,
        payload=request.payload
    )
    
    # Map result to response schema
    response = BridgeResponse(
        status=result["status"],
        reason=result["reason"],
        trace_id=result["trace_id"],
        artifact_id=result.get("artifact_id"),
        verified_write=result.get("verified_write")
    )
    
    return response
