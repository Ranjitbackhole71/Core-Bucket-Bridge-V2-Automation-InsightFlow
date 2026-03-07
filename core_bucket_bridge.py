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
from admission_layer import (
    RegistryValidator,
    CanonicalHasher,
    ImmutableAdmissionLogger,
    ContractValidator,
    SilentMutationAuditor,
    ReplayVerifier
)

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

# Set up telemetry logging for InsightFlow
telemetry_logger = logging.getLogger("telemetry_logger")
telemetry_logger.setLevel(logging.INFO)
telemetry_handler = RotatingFileHandler("logs/telemetry.jsonl", maxBytes=1000000, backupCount=5)
telemetry_formatter = logging.Formatter('%(message)s')
telemetry_handler.setFormatter(telemetry_formatter)
telemetry_logger.addHandler(telemetry_handler)

# Set up heartbeat logging
heartbeat_logger = logging.getLogger("heartbeat_logger")
heartbeat_logger.setLevel(logging.INFO)
heartbeat_handler = RotatingFileHandler("logs/heartbeat.log", maxBytes=1000000, backupCount=5)
heartbeat_formatter = logging.Formatter('%(asctime)s - %(message)s')
heartbeat_handler.setFormatter(heartbeat_formatter)
heartbeat_logger.addHandler(heartbeat_handler)

# Initialize admission layer components
registry_validator = RegistryValidator()
canonical_hasher = CanonicalHasher()
admission_logger = ImmutableAdmissionLogger()
contract_validator = ContractValidator(registry_validator)
mutation_auditor = SilentMutationAuditor()
replay_verifier = ReplayVerifier(admission_logger)

# Health monitoring variables
start_time = time.time()
error_count_24h = 0
pending_queue = 0
latencies = []  # Store latencies for averaging

# Security metrics tracking
rejected_signatures = 0
replay_attempts = 0
last_valid_signature_timestamps = {}  # {plugin_id: timestamp}
last_nonce = None  # Track the last nonce used

# Telemetry counters for InsightFlow
telemetry_counters = {
    "event_ingestion": 0,
    "accepted_count": 0,
    "rejected_count": 0,
    "decision_latencies": []
}

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

class HeartbeatPayload(BaseModel):
    module: str
    timestamp: str
    status: str
    metrics: Optional[Dict[str, Any]] = None

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

class SecurityMetrics(BaseModel):
    signature_rejects_24h: int
    replay_rejects_24h: int
    last_valid_signature_ts: Dict[str, str]
    last_nonce: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    uptime_s: float
    last_sync_ts: str
    pending_queue: int
    error_count_24h: int
    avg_latency_ms_24h: float
    security: SecurityMetrics
    structural_hardening: Optional[Dict[str, Any]] = None

class RejectionResponse(BaseModel):
    status: str
    reason: str

class ReplayVerificationResponse(BaseModel):
    verified: bool
    input_hash: str
    original_decision: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class AuditReportResponse(BaseModel):
    audit_trail: list
    total_audits: int

# Role-based access control
def verify_jwt_token_with_role(required_role: str = None):
    def verify_token(authorization: str = Header(None)):
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
            
            # Check role if required
            if required_role:
                if "roles" not in decoded or required_role not in decoded["roles"]:
                    security_logger.info(f"Insufficient privileges. Required role: {required_role}")
                    raise HTTPException(status_code=403, detail="Insufficient privileges")
                    
            return decoded
        except jwt.InvalidTokenError as e:
            security_logger.info(f"Invalid token: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid token")
    return verify_token

# Enhanced RBAC decorators as required

def requires_role(role: str):
    """
    Decorator for role-based access control
    """
    def role_checker(authorization: str = Header(None)):
        if not authorization:
            security_logger.info(f"Missing authorization header for role: {role}")
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        try:
            token = authorization.split(" ")[1]  # Bearer <token>
            decoded = jwt.decode(token, "secret", algorithms=["HS256"])  # In production, use proper secret
            
            # Check expiry
            if "exp" in decoded and decoded["exp"] < datetime.utcnow().timestamp():
                security_logger.info(f"Expired token for role: {role}")
                raise HTTPException(status_code=401, detail="Expired token")
            
            # Check role
            if "roles" not in decoded or role not in decoded["roles"]:
                security_logger.info(f"Insufficient privileges. Required role: {role}")
                raise HTTPException(status_code=403, detail="Insufficient privileges")
                
            return decoded
        except jwt.InvalidTokenError as e:
            security_logger.info(f"Invalid token for role {role}: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid token")
    return role_checker

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
        global rejected_signatures
        rejected_signatures += 1
        
        # Add InsightFlow hook for signature rejections
        insight_hook_entry = {
            "event_type": "signature_rejection",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }
        
        with open("insight/flow.log", "a") as f:
            f.write(json.dumps(insight_hook_entry) + "\n")
        
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
            global replay_attempts
            replay_attempts += 1
                    
            # Add InsightFlow hook for replay rejections
            insight_hook_entry = {
                "event_type": "replay_rejection",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "nonce": nonce
            }
                    
            with open("insight/flow.log", "a") as f:
                f.write(json.dumps(insight_hook_entry) + "\n")
                    
            return False
        
        # Add nonce to cache
        nonce_cache["nonces"].append(nonce)
        
        # Keep only last 5000 nonces
        if len(nonce_cache["nonces"]) > 5000:
            nonce_cache["nonces"] = nonce_cache["nonces"][-5000:]
        
        # Save nonce cache
        with open("security/nonce_cache.json", "w") as f:
            json.dump(nonce_cache, f)
        
        # Track last nonce used
        global last_nonce
        last_nonce = nonce
        
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
            
        # Add InsightFlow hook for provenance chain entries
        insight_hook_entry = {
            "event_type": "provenance_chain",
            "timestamp": timestamp,
            "hash": new_hash,
            "previous_hash": last_hash
        }
        
        with open("insight/flow.log", "a") as f:
            f.write(json.dumps(insight_hook_entry) + "\n")
            
        return new_hash
    except Exception as e:
        security_logger.info(f"Error adding to provenance chain: {str(e)}")
        return None

@app.post("/core/heartbeat", response_model=CoreUpdateResponse)
async def core_heartbeat(secure_payload: SecurePayload, token_data: dict = Depends(requires_role("module"))):
    """
    Receives heartbeat from modules/plugins with signature verification, JWT authentication, and anti-replay protection.
    Implements structural hardening with registry alignment, contract enforcement, and immutable logging.
    """
    global pending_queue, latencies, last_valid_signature_timestamps
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        # Capture original payload for mutation audit
        original_hash = mutation_auditor.capture_original(secure_payload.payload)
        
        # Check nonce for anti-replay protection
        if secure_payload.nonce and not check_nonce(secure_payload.nonce):
            security_logger.info("Replay attack detected in heartbeat")
            # Log rejection to admission logger
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=secure_payload.payload.get("module", "unknown"),
                input_hash=input_hash,
                registry_version="1.0.0",
                decision="REJECTED",
                rule_id="REPLAY_PROTECTION",
                timestamp=timestamp
            )
            raise HTTPException(status_code=401, detail="Replay attack detected")
        
        # Verify signature
        if not verify_signature(secure_payload.payload, secure_payload.signature):
            security_logger.info("Invalid signature for /core/heartbeat")
            # Log rejection to admission logger
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=secure_payload.payload.get("module", "unknown"),
                input_hash=input_hash,
                registry_version="1.0.0",
                decision="REJECTED",
                rule_id="SIGNATURE_VERIFICATION",
                timestamp=timestamp
            )
            return RejectionResponse(status="rejected", reason="invalid_signature")
        
        # Extract payload data
        payload = HeartbeatPayload(**secure_payload.payload)
        
        # STEP 1: Registry Alignment
        is_registered, schema_version = registry_validator.verify_module_registered(payload.module)
        if not is_registered:
            security_logger.info(f"Module not registered: {payload.module}")
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version="N/A",
                decision="REJECTED",
                rule_id="MODULE_NOT_REGISTERED",
                timestamp=timestamp
            )
            raise HTTPException(status_code=400, detail=f"Module not registered: {payload.module}")
        
        # STEP 2: Contract Enforcement - Strict schema validation
        is_valid, error_msg, rule_id = contract_validator.validate_contract("core/heartbeat", secure_payload.payload)
        if not is_valid:
            security_logger.info(f"Contract validation failed: {error_msg}")
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version=schema_version,
                decision="REJECTED",
                rule_id=rule_id,
                timestamp=timestamp
            )
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Compute input hash for accepted request
        input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
        
        # Add to provenance chain
        provenance_hash = add_to_provenance_chain(secure_payload.payload, timestamp)
        
        # Update last valid signature timestamp for this module
        last_valid_signature_timestamps[payload.module] = timestamp
        
        # STEP 3: Immutable Admission Logging - Log acceptance decision
        admission_logger.log_decision(
            module_id=payload.module,
            input_hash=input_hash,
            registry_version=schema_version,
            decision="ACCEPTED",
            rule_id=rule_id,
            timestamp=timestamp
        )
        
        # STEP 5: Silent Mutation Audit - Verify no mutation during processing
        if not mutation_auditor.verify_no_mutation(original_hash, secure_payload.payload):
            security_logger.info("Payload mutation detected in heartbeat processing")
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version=schema_version,
                decision="REJECTED",
                rule_id="PAYLOAD_MUTATION_DETECTED",
                timestamp=timestamp
            )
            raise HTTPException(status_code=500, detail="Payload integrity violation")
        
        # Log the heartbeat to both sync logger and dedicated heartbeat logger
        log_entry = {
            "module": payload.module,
            "timestamp": timestamp,
            "status": payload.status,
            "metrics": payload.metrics
        }
        
        sync_logger.info(json.dumps(log_entry))
        heartbeat_logger.info(json.dumps(log_entry))
        
        # Add InsightFlow hook for heartbeat events
        insight_hook_entry = {
            "event_type": "heartbeat",
            "module": payload.module,
            "timestamp": timestamp,
            "status": payload.status,
            "metrics": payload.metrics
        }
        
        with open("insight/flow.log", "a") as f:
            f.write(json.dumps(insight_hook_entry) + "\n")
        
        # Log metrics
        metrics_entry = {
            "timestamp": timestamp,
            "endpoint": "/core/heartbeat",
            "module": payload.module,
            "status": "success",
            "provenance_hash": provenance_hash,
            "input_hash": input_hash,
            "registry_version": schema_version
        }
        metrics_logger.info(json.dumps(metrics_entry))
        
        return CoreUpdateResponse(
            status="success",
            timestamp=timestamp,
            session_id=f"heartbeat-{uuid.uuid4()}",
            message=f"Heartbeat received and logged for module {payload.module}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        global error_count_24h
        error_count_24h += 1
        raise HTTPException(status_code=500, detail=f"Error processing heartbeat: {str(e)}")

@app.post("/core/update", response_model=CoreUpdateResponse)
async def core_update(secure_payload: SecurePayload, token_data: dict = Depends(requires_role("module"))):
    """
    Receives JSON data from Core with signature verification, JWT authentication, and anti-replay protection.
    Implements structural hardening with registry alignment, contract enforcement, and immutable logging.
    """
    global pending_queue, latencies
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        # Capture original payload for mutation audit
        original_hash = mutation_auditor.capture_original(secure_payload.payload)
        
        # Check nonce for anti-replay protection
        if secure_payload.nonce and not check_nonce(secure_payload.nonce):
            security_logger.info("Replay attack detected")
            # Log rejection to admission logger
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=secure_payload.payload.get("module", "unknown"),
                input_hash=input_hash,
                registry_version="1.0.0",
                decision="REJECTED",
                rule_id="REPLAY_PROTECTION",
                timestamp=timestamp
            )
            raise HTTPException(status_code=401, detail="Replay attack detected")
        
        # Verify signature
        if not verify_signature(secure_payload.payload, secure_payload.signature):
            security_logger.info("Invalid signature for /core/update")
            # Log rejection to admission logger
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=secure_payload.payload.get("module", "unknown"),
                input_hash=input_hash,
                registry_version="1.0.0",
                decision="REJECTED",
                rule_id="SIGNATURE_VERIFICATION",
                timestamp=timestamp
            )
            return RejectionResponse(status="rejected", reason="invalid_signature")
        
        # Extract payload data
        payload = CoreUpdatePayload(**secure_payload.payload)
        
        # STEP 1: Registry Alignment
        is_registered, schema_version = registry_validator.verify_module_registered(payload.module)
        if not is_registered:
            security_logger.info(f"Module not registered: {payload.module}")
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version="N/A",
                decision="REJECTED",
                rule_id="MODULE_NOT_REGISTERED",
                timestamp=timestamp
            )
            raise HTTPException(status_code=400, detail=f"Module not registered: {payload.module}")
        
        # STEP 2: Contract Enforcement - Strict schema validation
        is_valid, error_msg, rule_id = contract_validator.validate_contract("core/update", secure_payload.payload)
        if not is_valid:
            security_logger.info(f"Contract validation failed: {error_msg}")
            input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version=schema_version,
                decision="REJECTED",
                rule_id=rule_id,
                timestamp=timestamp
            )
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Compute input hash for accepted request
        input_hash = canonical_hasher.compute_input_hash(secure_payload.payload)
        
        # Add to provenance chain
        add_to_provenance_chain(secure_payload.payload, timestamp)
        
        pending_queue += 1
        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        
        # STEP 3: Immutable Admission Logging - Log acceptance decision
        admission_logger.log_decision(
            module_id=payload.module,
            input_hash=input_hash,
            registry_version=schema_version,
            decision="ACCEPTED",
            rule_id=rule_id,
            timestamp=timestamp
        )
        
        # STEP 5: Silent Mutation Audit - Verify no mutation during processing
        if not mutation_auditor.verify_no_mutation(original_hash, secure_payload.payload):
            security_logger.info("Payload mutation detected in update processing")
            admission_logger.log_decision(
                module_id=payload.module,
                input_hash=input_hash,
                registry_version=schema_version,
                decision="REJECTED",
                rule_id="PAYLOAD_MUTATION_DETECTED",
                timestamp=timestamp
            )
            pending_queue -= 1
            raise HTTPException(status_code=500, detail="Payload integrity violation")
        
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
        
        # Add InsightFlow hook for core update events
        insight_hook_entry = {
            "event_type": "core_update",
            "module": payload.module,
            "timestamp": timestamp,
            "latency_ms": latency,
            "status": "success"
        }
        
        with open("insight/flow.log", "a") as f:
            f.write(json.dumps(insight_hook_entry) + "\n")
            
        # Log metrics with structural hardening info
        metrics_entry = {
            "timestamp": timestamp,
            "endpoint": "/core/update",
            "module": payload.module,
            "status": "success",
            "latency_ms": latency,
            "pending_queue": pending_queue,
            "input_hash": input_hash,
            "registry_version": schema_version
        }
        metrics_logger.info(json.dumps(metrics_entry))
        
        pending_queue -= 1
        
        return CoreUpdateResponse(
            status="success",
            timestamp=timestamp,
            session_id=session_id,
            message=f"Data received and logged for module {payload.module}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        global error_count_24h
        error_count_24h += 1
        pending_queue -= 1
        raise HTTPException(status_code=500, detail=f"Error processing update: {str(e)}")

@app.get("/bucket/status", response_model=BucketStatusResponse)
async def bucket_status(token_data: dict = Depends(requires_role("module"))):
    """
    Returns current sync summary (last sync time, total sync count) with JWT authentication.
    """
    return BucketStatusResponse(
        last_sync_time=sync_summary["last_sync_time"] or "",
        total_sync_count=sync_summary["total_sync_count"],
        module_sync_counts=sync_summary["module_sync_counts"]
    )

@app.get("/core/health", response_model=HealthResponse)
async def core_health():
    """
    Returns health metrics for the Core-Bucket bridge including security metrics and structural hardening status.
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
    
    # Get admission decision statistics
    recent_decisions = admission_logger.get_decisions(limit=100)
    accepted_count = sum(1 for d in recent_decisions if d.get("decision") == "ACCEPTED")
    rejected_count = sum(1 for d in recent_decisions if d.get("decision") == "REJECTED")
    
    # Get mutation audit statistics
    audit_trail = mutation_auditor.get_audit_report()
    mutation_violations = sum(1 for a in audit_trail if a.get("mutated") == True)
    
    return HealthResponse(
        status="ok",
        uptime_s=uptime,
        last_sync_ts=sync_summary["last_sync_time"] or "",
        pending_queue=pending_queue,
        error_count_24h=error_count_24h,
        avg_latency_ms_24h=avg_latency,
        security=SecurityMetrics(
            signature_rejects_24h=rejected_signatures,
            replay_rejects_24h=replay_attempts,
            last_valid_signature_ts=last_valid_signature_timestamps,
            last_nonce=last_nonce
        ),
        structural_hardening={
            "registry_loaded": registry_validator._registry_cache is not None,
            "total_admission_decisions": len(recent_decisions),
            "accepted_decisions": accepted_count,
            "rejected_decisions": rejected_count,
            "mutation_audits_performed": len(audit_trail),
            "mutation_violations": mutation_violations,
            "contract_enforcement_active": True
        }
    )

# Create insight directory if it doesn't exist
os.makedirs("insight", exist_ok=True)

# Create initial empty flow.log if it doesn't exist
flow_log_path = "insight/flow.log"
if not os.path.exists(flow_log_path):
    with open(flow_log_path, "w") as f:
        pass  # Create empty file

@app.post("/verify/replay", response_model=ReplayVerificationResponse)
async def verify_replay(input_hash: str, token_data: dict = Depends(requires_role("module"))):
    """
    STEP 4: Replay Verification Engine
    
    Verifies that replay produces identical verdict.
    
    Verification rules:
    - input_hash identical
    - decision identical
    - rule_id identical
    """
    verified, original_decision, error_message = replay_verifier.verify_replay(input_hash)
    
    return ReplayVerificationResponse(
        verified=verified,
        input_hash=input_hash,
        original_decision=original_decision,
        error_message=error_message
    )

@app.get("/audit/report", response_model=AuditReportResponse)
async def get_audit_report(token_data: dict = Depends(requires_role("admin"))):
    """
    STEP 5: Silent Mutation Audit Report
    
    Returns complete audit trail for payload mutation detection.
    """
    audit_trail = mutation_auditor.get_audit_report()
    
    return AuditReportResponse(
        audit_trail=audit_trail,
        total_audits=len(audit_trail)
    )

@app.get("/admission/decisions")
async def get_admission_decisions(limit: int = 100, token_data: dict = Depends(requires_role("admin"))):
    """
    Get recent admission decisions (read-only).
    """
    decisions = admission_logger.get_decisions(limit=limit)
    return {"decisions": decisions, "count": len(decisions)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)