import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from datetime import datetime
import uuid
import logging
from logging.handlers import RotatingFileHandler

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

# Pydantic model for the data payload
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

@app.post("/core/update", response_model=CoreUpdateResponse)
async def core_update(payload: CoreUpdatePayload):
    """
    Receives JSON data from Core and logs it with timestamp, session_id, and module name.
    """
    global pending_queue, latencies
    try:
        pending_queue += 1
        # Generate session ID if not provided
        session_id = payload.session_id or str(uuid.uuid4())
        
        # Get current timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"
        
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
async def bucket_status():
    """
    Returns current sync summary (last sync time, total sync count).
    """
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