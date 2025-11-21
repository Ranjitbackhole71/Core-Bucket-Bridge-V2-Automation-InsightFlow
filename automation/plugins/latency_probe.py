"""
Latency probe plugin for automation engine
"""
import json
from datetime import datetime
import time

def run():
    """Run latency probe plugin"""
    start_time = time.time()
    
    # Simulate some work
    time.sleep(0.1)  # 100ms delay
    
    end_time = time.time()
    latency = (end_time - start_time) * 1000  # Convert to milliseconds
    
    probe_data = {
        "module": "latency_probe",
        "probe_id": "lat_001",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metrics": {
            "latency_ms": latency,
            "probe_target": "internal_processing",
            "status": "completed"
        }
    }
    
    # Log to engine log
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "plugin": "latency_probe",
        "event": "probe_completed",
        "data": probe_data
    }
    
    try:
        with open("automation/reports/engine.log", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print(f"Error logging latency probe: {e}")
    
    return probe_data