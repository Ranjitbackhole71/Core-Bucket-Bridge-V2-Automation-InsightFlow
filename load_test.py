#!/usr/bin/env python3
"""
Load Test for Core-Bucket Bridge V4
Performs 1000 signed requests and records average latency and error rate
"""
import requests
import time
import json
import jwt
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import uuid
import statistics

# Load private key for signing
def load_private_key():
    try:
        with open("security/private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(key_file.read(), password=None)
        return private_key
    except Exception as e:
        print(f"Error loading private key: {e}")
        return None

# Sign payload
def sign_payload(payload, private_key):
    try:
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = private_key.sign(
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"Error signing payload: {e}")
        return None

# Create JWT token
def create_jwt_token(roles=["module"]):
    try:
        payload = {
            "iss": "core-bucket-bridge",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "roles": roles
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        return f"Bearer {token}"
    except Exception as e:
        print(f"Error creating JWT token: {e}")
        return None

# Send signed request
def send_signed_request(endpoint, payload_data, private_key):
    start_time = time.time()
    
    # Create payload
    payload = {
        "module": "load_test",
        "data": payload_data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Sign payload
    signature = sign_payload(payload, private_key)
    if not signature:
        return None, time.time() - start_time, "Signature failed"
    
    # Create JWT token
    token = create_jwt_token(["module"])
    if not token:
        return None, time.time() - start_time, "JWT token failed"
    
    # Create secure payload
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": str(uuid.uuid4())
    }
    
    # Send request
    try:
        response = requests.post(
            f"http://localhost:8000{endpoint}",
            json=secure_payload,
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            },
            timeout=30
        )
        latency = time.time() - start_time
        return response, latency, None
    except Exception as e:
        latency = time.time() - start_time
        return None, latency, str(e)

def main():
    print("🚀 Starting Load Test for Core-Bucket Bridge V4")
    print("This will send 1000 signed requests to /core/update")
    
    # Load private key
    private_key = load_private_key()
    if not private_key:
        print("❌ Failed to load private key")
        return
    
    # Test configuration
    total_requests = 1000
    endpoint = "/core/update"
    
    print(f"Total requests: {total_requests}")
    print(f"Endpoint: {endpoint}")
    
    # Initialize counters
    successful_requests = 0
    failed_requests = 0
    latencies = []
    errors = []
    
    # Send requests
    for i in range(total_requests):
        # Create test data
        test_data = {
            "test_id": f"load_test_{i}",
            "value": i,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        # Send request
        response, latency, error = send_signed_request(endpoint, test_data, private_key)
        latencies.append(latency)
        
        if response and response.status_code == 200:
            successful_requests += 1
            if i % 100 == 0:  # Print progress every 100 requests
                print(f"✅ Request {i+1}/{total_requests} succeeded (latency: {latency:.3f}s)")
        else:
            failed_requests += 1
            error_msg = error or (f"Status code: {response.status_code}" if response else "Unknown error")
            errors.append(error_msg)
            if i % 100 == 0:  # Print progress every 100 requests
                print(f"❌ Request {i+1}/{total_requests} failed: {error_msg}")
    
    # Calculate metrics
    total_requests_made = successful_requests + failed_requests
    success_rate = (successful_requests / total_requests_made) * 100 if total_requests_made > 0 else 0
    error_rate = (failed_requests / total_requests_made) * 100 if total_requests_made > 0 else 0
    avg_latency = statistics.mean(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    
    # Print results
    print("\n📊 Load Test Results:")
    print(f"   Total Requests: {total_requests_made}")
    print(f"   Successful: {successful_requests} ({success_rate:.2f}%)")
    print(f"   Failed: {failed_requests} ({error_rate:.2f}%)")
    print(f"   Average Latency: {avg_latency:.3f}s")
    print(f"   Min Latency: {min_latency:.3f}s")
    print(f"   Max Latency: {max_latency:.3f}s")
    
    # Check requirements
    print("\n📋 Requirements Check:")
    if error_rate < 0.1:
        print("✅ Error rate < 0.1%: PASSED")
    else:
        print(f"❌ Error rate < 0.1%: FAILED (current: {error_rate:.2f}%)")
    
    # Create summary report
    load_test_report = {
        "test_type": "Load Test",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_requests": total_requests_made,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "success_rate_percent": round(success_rate, 2),
        "error_rate_percent": round(error_rate, 2),
        "average_latency_seconds": round(avg_latency, 3),
        "min_latency_seconds": round(min_latency, 3),
        "max_latency_seconds": round(max_latency, 3),
        "latency_data": {
            "mean": round(avg_latency, 3),
            "median": round(statistics.median(latencies) if latencies else 0, 3),
            "stdev": round(statistics.stdev(latencies) if len(latencies) > 1 else 0, 3)
        },
        "top_errors": errors[:10]  # Show first 10 errors
    }
    
    # Save report
    try:
        with open("reports/load_test_report.json", "w") as f:
            json.dump(load_test_report, f, indent=2)
        print(f"✅ Load test report saved to reports/load_test_report.json")
    except Exception as e:
        print(f"❌ Failed to save load test report: {e}")
    
    # Final verdict
    if error_rate < 0.1:
        print("\n🎉 Load Test Result: PASSED - System meets performance requirements!")
    else:
        print(f"\n❌ Load Test Result: FAILED - Error rate too high ({error_rate:.2f}%)")

if __name__ == "__main__":
    main()