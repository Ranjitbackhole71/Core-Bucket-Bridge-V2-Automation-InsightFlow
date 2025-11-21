import time
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime
import uuid
import logging
from logging.handlers import RotatingFileHandler
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64
import hashlib

# Initialize FastAPI app
app = FastAPI(title="Core-Bucket Data Bridge", 
              description="API for synchronizing module data from Core to Bucket with InsightFlow monitoring")

# Create logs directory if it doesn't exist
os.makedirs("logs", exist_ok=True)

# Set up logging for sync activities
sync_logger = logging.getLogger("sync_logger")
sync_logger.setLevel(logging.INFO)
sync_handler = RotatingFileHandler("logs/core_sync.log", maxBytes=1000000, backupCount=5)
sync_formatter = logging.Formatter('%(asctime)s - %(message)s')
sync_handler.setFormatter(sync_formatter)
sync_logger.addHandler(sync_handler)

# Set up metrics logging
metrics_logger = logging.getLogger("metrics_logger")
metrics_logger.setLevel(logging.INFO)
metrics_handler = RotatingFileHandler("logs/metrics.jsonl", maxBytes=1000000, backupCount=5)
metrics_formatter = logging.Formatter('%(message)s')
metrics_handler.setFormatter(metrics_formatter)
metrics_logger.addHandler(metrics_handler)

# Set up security rejection logging
security_logger = logging.getLogger("security_logger")
security_logger.setLevel(logging.INFO)
security_handler = RotatingFileHandler("logs/security_rejects.log", maxBytes=1000000, backupCount=5)
security_formatter = logging.Formatter('%(asctime)s - %(message)s')
security_handler.setFormatter(security_formatter)
security_logger.addHandler(security_handler)

# Health monitoring variables
start_time = time.time()
error_count_24h = 0
pending_queue = 0
latencies = []  # Store latencies for averaging

# In-memory storage for sync summary (in production, use a database)
sync_summary = {
    "last_sync_time": None,
    "total_sync_count": 0,
    "module_sync_counts": {}
}

# Load public key for signature verification
def load_public_key():
    try:
        with open("security/public.pem", "rb") as key_file:
            public_key = serialization.load_pem_public_key(key_file.read())
        return public_key
    except Exception as e:
        print(f"Error loading public key: {e}")
        return None

public_key = load_public_key()

# Pydantic models for secure requests
class SecurePayload(BaseModel):
    payload: Dict[str, Any]
    signature: str
    nonce: Optional[str] = None

class CoreUpdatePayload(BaseModel):
    module: str
    data: Dict[str, Any]
    session_id: Optional[str] = None

# Pydantic model for the response
class CoreUpdateResponse(BaseModel):
    status: str
    timestamp: str
    session_id: str
    message: str

class BucketStatusResponse(BaseModel):
    last_sync_time: str
    total_sync_count: int
    module_sync_counts: Dict[str, int]

class HealthResponse(BaseModel):
    status: str
    uptime_s: float
    last_sync_ts: str
    pending_queue: int
    error_count_24h: int
    avg_latency_ms_24h: float

class RejectionResponse(BaseModel):
    status: str
    reason: str

# JWT verification function
def verify_jwt_token(authorization: str = Header(None)):
    if not authorization:
        security_logger.info("Missing authorization header")
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        token = authorization.split(" ")[1]  # Bearer <token>
        decoded = jwt.decode(token, "secret", algorithms=["HS256"])  # In production, use proper secret
        
        # Check expiry
        if "exp" in decoded and decoded["exp"] < datetime.utcnow().timestamp():
            security_logger.info("Expired token")
            raise HTTPException(status_code=401, detail="Expired token")
            
        return decoded
    except jwt.InvalidTokenError as e:
        security_logger.info(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

# Signature verification function
def verify_signature(payload: Dict[str, Any], signature: str) -> bool:
    if not public_key:
        security_logger.info("Public key not loaded")
        return False
        
    try:
        # Convert payload to bytes
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        
        # Decode signature from base64
        signature_bytes = base64.b64decode(signature)
        
        # Verify signature
        public_key.verify(
            signature_bytes,
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception as e:
        security_logger.info(f"Signature verification failed: {str(e)}")
        return False

# Nonce tracking function
def check_nonce(nonce: str) -> bool:
    if not nonce:
        return True  # No nonce checking if not provided
    
    try:
        # Load nonce cache
        if os.path.exists("security/nonce_cache.json"):
            with open("security/nonce_cache.json", "r") as f:
                nonce_cache = json.load(f)
        else:
            nonce_cache = {"nonces": []}
        
        # Check if nonce exists
        if nonce in nonce_cache["nonces"]:
            security_logger.info(f"Replay attack detected with nonce: {nonce}")
            return False
        
        # Add nonce to cache
        nonce_cache["nonces"].append(nonce)
        
        # Keep only last 5000 nonces
        if len(nonce_cache["nonces"]) > 5000:
            nonce_cache["nonces"] = nonce_cache["nonces"][-5000:]
        
        # Save nonce cache
        with open("security/nonce_cache.json", "w") as f:
            json.dump(nonce_cache, f)
        
        return True
    except Exception as e:
        security_logger.info(f"Error checking nonce: {str(e)}")
        return False

# Provenance chain function
def add_to_provenance_chain(payload: Dict[str, Any], timestamp: str):
    try:
        # Get the last hash from the chain
        last_hash = ""
        if os.path.exists("logs/provenance_chain.jsonl"):
            with open("logs/provenance_chain.jsonl", "rb") as f:
                f.seek(0, 2)  # Go to end of file
                file_size = f.tell()
                if file_size > 0:
                    f.seek(max(0, file_size - 200))  # Read last 200 bytes to find last entry
                    lines = f.readlines()
                    if lines:
                        try:
                            last_entry = json.loads(lines[-1])
                            last_hash = last_entry.get("hash", "")
                        except:
                            pass
        
        # Create new hash
        data_to_hash = f"{last_hash}{json.dumps(payload, sort_keys=True)}{timestamp}"
        new_hash = hashlib.sha256(data_to_hash.encode('utf-8')).hexdigest()
        
        # Add to chain
        chain_entry = {
            "hash": new_hash,
            "previous_hash": last_hash,
            "payload": payload,
            "timestamp": timestamp
        }
        
        with open("logs/provenance_chain.jsonl", "a") as f:
            f.write(json.dumps(chain_entry) + "\n")
            
        return new_hash
    except Exception as e:
        security_logger.info(f"Error adding to provenance chain: {str(e)}")
        return None

@app.post("/core/update", response_model=CoreUpdateResponse)
async def core_update(secure_payload: SecurePayload, token_data: dict = Depends(verify_jwt_token)):
    """
    Receives JSON data from Core with signature verification, JWT authentication, and anti-replay protection.
    """
    global pending_queue, latencies
    try:
        # Check nonce for anti-replay protection
        if secure_payload.nonce and not check_nonce(secure_payload.nonce):
            security_logger.info("Replay attack detected")
            raise HTTPException(status_code=401, detail="Replay attack detected")
        
        # Verify signature
        if not verify_signature(secure_payload.payload, secure_payload.signature):
            security_logger.info("Invalid signature for /core/update")
            return RejectionResponse(status="rejected", reason="invalid_signature")
        
        # Extract payload data
        payload = CoreUpdatePayload(**secure_payload.payload)
        
        # Get current timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Add to provenance chain
        add_to_provenance_chain(secure_payload.payload, timestamp)
        
        pending_queue += 1
        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        
        # Log the data
        log_entry = {
            "module": payload.module,
            "session_id": session_id,
            "timestamp": timestamp,
            "data": payload.data
        }
        
        sync_logger.info(json.dumps(log_entry))
        
        # Update sync summary
        sync_summary["last_sync_time"] = timestamp
        sync_summary["total_sync_count"] += 1
        
        if payload.module in sync_summary["module_sync_counts"]:
            sync_summary["module_sync_counts"][payload.module] += 1
        else:
            sync_summary["module_sync_counts"][payload.module] = 1
            
        # Also log to insight flow
        latency = 50  # Mock latency
        latencies.append(latency)
        insight_entry = {
            "module": payload.module,
            "status": "synced",
            "timestamp": timestamp,
            "latency_ms": latency
        }
        
        # Create insight directory if it doesn't exist
        os.makedirs("insight", exist_ok=True)
        
        # Write to insight flow log
        with open("insight/flow.log", "a") as f:
            f.write(json.dumps(insight_entry) + "\n")
            
        # Log metrics
        metrics_entry = {
            "timestamp": timestamp,
            "endpoint": "/core/update",
            "module": payload.module,
            "status": "success",
            "latency_ms": latency,
            "pending_queue": pending_queue
        }
        metrics_logger.info(json.dumps(metrics_entry))
        
        pending_queue -= 1
        
        return CoreUpdateResponse(
            status="success",
            timestamp=timestamp,
            session_id=session_id,
            message=f"Data received and logged for module {payload.module}"
        )
        
    except Exception as e:
        global error_count_24h
        error_count_24h += 1
        pending_queue -= 1
        raise HTTPException(status_code=500, detail=f"Error processing update: {str(e)}")

@app.get("/bucket/status", response_model=BucketStatusResponse)
async def bucket_status(token_data: dict = Depends(verify_jwt_token)):
    """
    Returns current sync summary (last sync time, total sync count) with JWT authentication.
    """
    # Verify token has required role
    if "roles" not in token_data or "module" not in token_data["roles"]:
        security_logger.info("Insufficient privileges for /bucket/status")
        raise HTTPException(status_code=403, detail="Insufficient privileges")
        
    return BucketStatusResponse(
        last_sync_time=sync_summary["last_sync_time"] or "",
        total_sync_count=sync_summary["total_sync_count"],
        module_sync_counts=sync_summary["module_sync_counts"]
    )

@app.get("/core/health", response_model=HealthResponse)
async def core_health():
    """
    Returns health metrics for the Core-Bucket bridge.
    """
    uptime = time.time() - start_time
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    
    # Log health metrics
    timestamp = datetime.utcnow().isoformat() + "Z"
    metrics_entry = {
        "timestamp": timestamp,
        "endpoint": "/core/health",
        "status": "success",
        "uptime_s": uptime,
        "pending_queue": pending_queue,
        "error_count_24h": error_count_24h,
        "avg_latency_ms_24h": avg_latency
    }
    metrics_logger.info(json.dumps(metrics_entry))
    
    return HealthResponse(
        status="ok",
        uptime_s=uptime,
        last_sync_ts=sync_summary["last_sync_time"] or "",
        pending_queue=pending_queue,
        error_count_24h=error_count_24h,
        avg_latency_ms_24h=avg_latency
    )

# Create insight directory if it doesn't exist
os.makedirs("insight", exist_ok=True)

# Create initial empty flow.log if it doesn't exist
flow_log_path = "insight/flow.log"
if not os.path.exists(flow_log_path):
    with open(flow_log_path, "w") as f:
        pass  # Create empty file

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)