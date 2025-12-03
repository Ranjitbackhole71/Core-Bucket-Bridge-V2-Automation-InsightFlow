"""
Full Sync Test Plugin for Core-Bucket Bridge V4
Tests the complete flow: signed /core/update -> /bucket/status -> /core/health -> provenance chain
"""
import json
import requests
from datetime import datetime
import os
import sys

# Add parent directory to path to import runner utilities
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def run():
    """Run full sync test plugin"""
    try:
        # Import the automation runner to use its utilities
        from automation.runner import AutomationRunner
        
        # Create a runner instance to use its utilities
        runner = AutomationRunner()
        
        print("🧪 Starting Full Sync Test...")
        
        # 1. Send a signed /core/update
        print("1. Sending signed /core/update...")
        update_data = {
            "module": "full_sync_test",
            "data": {
                "test_id": "full_sync_001",
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "test_data": "Full sync test data"
            }
        }
        
        update_response = runner.send_secure_request("/core/update", update_data, ["module"])
        if not update_response:
            print("❌ Failed to send /core/update")
            return {"status": "failed", "step": "core_update", "error": "Failed to send update"}
        
        print(f"✅ /core/update sent successfully: {update_response}")
        
        # 2. Poll /bucket/status
        print("2. Polling /bucket/status...")
        status_token = runner.create_jwt_token(["module"])
        if not status_token:
            print("❌ Failed to create JWT token for /bucket/status")
            return {"status": "failed", "step": "bucket_status", "error": "Failed to create JWT token"}
        
        status_headers = {"Authorization": status_token}
        status_response = requests.get("http://localhost:8000/bucket/status", headers=status_headers, timeout=30)
        
        if status_response.status_code != 200:
            print(f"❌ Failed to get /bucket/status: {status_response.status_code}")
            return {"status": "failed", "step": "bucket_status", "error": f"Status code: {status_response.status_code}"}
        
        status_data = status_response.json()
        print(f"✅ /bucket/status retrieved successfully: {status_data}")
        
        # 3. Call /core/health
        print("3. Calling /core/health...")
        health_response = requests.get("http://localhost:8000/core/health", timeout=30)
        
        if health_response.status_code != 200:
            print(f"❌ Failed to get /core/health: {health_response.status_code}")
            return {"status": "failed", "step": "core_health", "error": f"Status code: {health_response.status_code}"}
        
        health_data = health_response.json()
        print(f"✅ /core/health retrieved successfully: {health_data}")
        
        # 4. Read latest provenance from /logs/provenance_chain.jsonl
        print("4. Reading latest provenance chain entry...")
        provenance_data = None
        if os.path.exists("logs/provenance_chain.jsonl"):
            try:
                with open("logs/provenance_chain.jsonl", "r") as f:
                    lines = f.readlines()
                    if lines:
                        provenance_data = json.loads(lines[-1])
                        print(f"✅ Latest provenance entry retrieved: {provenance_data.get('hash', 'N/A')}")
                    else:
                        print("⚠️  Provenance chain is empty")
            except Exception as e:
                print(f"⚠️  Error reading provenance chain: {e}")
        else:
            print("⚠️  Provenance chain file not found")
        
        # 5. Compile results
        result = {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "steps": {
                "core_update": {
                    "status": "success",
                    "response": update_response
                },
                "bucket_status": {
                    "status": "success",
                    "response": status_data
                },
                "core_health": {
                    "status": "success",
                    "response": health_data
                },
                "provenance_chain": {
                    "status": "success" if provenance_data else "warning",
                    "data": provenance_data
                }
            },
            "security_metrics": {
                "signature_rejects_24h": health_data.get("security", {}).get("signature_rejects_24h", 0),
                "replay_rejects_24h": health_data.get("security", {}).get("replay_rejects_24h", 0)
            }
        }
        
        # Log results
        log_entry = {
            "timestamp": result["timestamp"],
            "plugin": "full_sync_test",
            "event": "full_sync_test_completed",
            "result": result
        }
        
        # Write to engine log
        engine_log_path = "automation/reports/engine.log"
        with open(engine_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print("✅ Full Sync Test completed successfully!")
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }
        
        # Log error
        log_entry = {
            "timestamp": error_result["timestamp"],
            "plugin": "full_sync_test",
            "event": "full_sync_test_error",
            "result": error_result
        }
        
        # Write to engine log
        engine_log_path = "automation/reports/engine.log"
        with open(engine_log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        print(f"❌ Full Sync Test failed with error: {e}")
        return error_result

if __name__ == "__main__":
    result = run()
    print(json.dumps(result, indent=2))