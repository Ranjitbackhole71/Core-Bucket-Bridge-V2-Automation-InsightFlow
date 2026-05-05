"""
Bridge API — Strict Contract Enforcement

Endpoint: POST /bridge/validate_and_forward
Input: {execution_id, trace_id, authority_token, payload}
Output: {status: "FORWARDED|BLOCKED", reason, trace_id, execution_id, verified_write}
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator
from typing import Any, Dict, Optional

from ..services.bridge_integration import tantra_bridge

router = APIRouter(prefix="/bridge", tags=["bridge"])


class BridgeRequest(BaseModel):
    execution_id: str
    trace_id: str
    authority_token: str
    payload: Dict[str, Any] = {}

    @field_validator("execution_id")
    @classmethod
    def execution_id_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("execution_id must not be empty")
        return v

    @field_validator("trace_id")
    @classmethod
    def trace_id_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("trace_id must not be empty")
        return v

    @field_validator("authority_token")
    @classmethod
    def authority_token_not_empty(cls, v):
        if not v or v.strip() == "":
            raise ValueError("authority_token must not be empty")
        return v


class BridgeResponse(BaseModel):
    status: str
    reason: str
    trace_id: str
    execution_id: str
    artifact_id: Optional[str] = None
    artifact_hash: Optional[str] = None
    verified_write: bool = False
    code: Optional[str] = None


@router.post("/validate_and_forward", response_model=BridgeResponse)
async def validate_and_forward(request: BridgeRequest):
    result = tantra_bridge.process(
        trace_id=request.trace_id,
        execution_id=request.execution_id,
        authority_token=request.authority_token,
        payload=request.payload,
    )

    return BridgeResponse(
        status=result["status"],
        reason=result["reason"],
        trace_id=result.get("trace_id", ""),
        execution_id=result.get("execution_id", ""),
        artifact_id=result.get("artifact_id"),
        artifact_hash=result.get("artifact_hash"),
        verified_write=result.get("verified_write", False),
        code=result.get("code"),
    )
