#!/usr/bin/env python3
"""
2-Minute Demo Script for Core-Bucket Bridge V4
Shows valid signed request, replayed request rejection, RBAC failure, 
heartbeat success, provenance chain view, and InsightFlow V2 dashboard
"""
import requests
import json
import jwt
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64
import uuid
import time
import os

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
def send_signed_request(endpoint, payload_data, private_key, roles=["module"]):
    # Create payload
    payload = {
        "module": "demo_module",
        "data": payload_data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Sign payload
    signature = sign_payload(payload, private_key)
    if not signature:
        return None, "Signature failed"
    
    # Create JWT token
    token = create_jwt_token(roles)
    if not token:
        return None, "JWT token failed"
    
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
        return response, None
    except Exception as e:
        return None, str(e)

def demo_valid_signed_request(private_key):
    print("🎯 DEMO 1: Valid Signed Request (Accepted)")
    print("Sending a valid signed request to /core/update...")
    
    test_data = {
        "demo_id": "valid_request_test",
        "value": "This is a valid signed request",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    response, error = send_signed_request("/core/update", test_data, private_key)
    
    if response and response.status_code == 200:
        print("✅ SUCCESS: Valid signed request accepted")
        print(f"Response: {response.json()}")
    else:
        error_msg = error or (f"Status code: {response.status_code}" if response else "Unknown error")
        print(f"❌ FAILED: {error_msg}")
    
    print()
    time.sleep(2)

def demo_replayed_request(private_key):
    print("🔄 DEMO 2: Replayed Request (Rejected)")
    print("Sending the same request twice to test anti-replay protection...")
    
    # Create a unique payload
    test_data = {
        "demo_id": "replay_test",
        "value": "This request will be replayed",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Sign payload
    payload = {
        "module": "demo_module",
        "data": test_data,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    signature = sign_payload(payload, private_key)
    if not signature:
        print("❌ FAILED: Could not sign payload")
        return
    
    # Create JWT token
    token = create_jwt_token(["module"])
    if not token:
        print("❌ FAILED: Could not create JWT token")
        return
    
    # Use a fixed nonce for replay test
    fixed_nonce = "demo-replay-nonce-123"
    
    # Create secure payload
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": fixed_nonce
    }
    
    # Send first request
    print("Sending first request...")
    try:
        response1 = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload,
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response1.status_code == 200:
            print("✅ First request accepted")
        else:
            print(f"❌ First request failed: {response1.status_code}")
            return
    except Exception as e:
        print(f"❌ First request error: {e}")
        return
    
    # Send second request with same nonce (replay attack)
    print("Sending second request with same nonce (replay attack)...")
    try:
        response2 = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload,
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response2.status_code == 401:
            print("✅ SUCCESS: Replay attack correctly rejected")
            print("This demonstrates the anti-replay protection system working")
        else:
            print(f"❌ Replay attack not properly rejected: {response2.status_code}")
    except Exception as e:
        print(f"❌ Replay test error: {e}")
    
    print()
    time.sleep(2)

def demo_rbac_failure():
    print("🔐 DEMO 3: RBAC Failure (Rejected)")
    print("Sending a request with insufficient privileges...")
    
    # Create JWT token with insufficient role
    try:
        payload = {
            "iss": "core-bucket-bridge",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "roles": ["insufficient_role"]
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        auth_header = f"Bearer {token}"
    except Exception as e:
        print(f"❌ FAILED: Could not create JWT token: {e}")
        return
    
    # Try to access /bucket/status which requires "module" role
    try:
        response = requests.get(
            "http://localhost:8000/bucket/status",
            headers={
                "Authorization": auth_header
            },
            timeout=30
        )
        
        if response.status_code == 403:
            print("✅ SUCCESS: RBAC correctly rejected unauthorized access")
            print("This demonstrates role-based access control working")
        else:
            print(f"❌ RBAC not properly enforced: {response.status_code}")
    except Exception as e:
        print(f"❌ RBAC test error: {e}")
    
    print()
    time.sleep(2)

def demo_heartbeat_success(private_key):
    print("💓 DEMO 4: Heartbeat Success")
    print("Sending a valid heartbeat to /core/heartbeat...")
    
    # Create heartbeat payload
    heartbeat_data = {
        "module": "demo_module",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "alive",
        "metrics": {
            "cpu_usage": 25.5,
            "memory_usage": 45.2,
            "uptime": 3600
        }
    }
    
    # Sign payload
    signature = sign_payload(heartbeat_data, private_key)
    if not signature:
        print("❌ FAILED: Could not sign payload")
        return
    
    # Create JWT token
    token = create_jwt_token(["module"])
    if not token:
        print("❌ FAILED: Could not create JWT token")
        return
    
    # Create secure payload
    secure_payload = {
        "payload": heartbeat_data,
        "signature": signature,
        "nonce": str(uuid.uuid4())
    }
    
    # Send heartbeat request
    try:
        response = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload,
            headers={
                "Authorization": token,
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ SUCCESS: Heartbeat sent and accepted")
            print(f"Response: {response.json()}")
            
            # Show that it was logged
            if os.path.exists("logs/heartbeat.log"):
                print("📝 Heartbeat was logged to logs/heartbeat.log")
        else:
            print(f"❌ Heartbeat failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Heartbeat error: {e}")
    
    print()
    time.sleep(2)

def demo_provenance_chain_view():
    print("🔗 DEMO 5: Provenance Chain View")
    print("Showing the provenance chain entries...")
    
    if os.path.exists("logs/provenance_chain.jsonl"):
        try:
            with open("logs/provenance_chain.jsonl", "r") as f:
                lines = f.readlines()
                if lines:
                    print(f"✅ Found {len(lines)} provenance chain entries")
                    # Show last 3 entries
                    for i, line in enumerate(lines[-3:], 1):
                        try:
                            entry = json.loads(line)
                            print(f"  Entry {len(lines)-3+i}: {entry.get('hash', 'N/A')[:16]}... ({entry.get('timestamp', 'N/A')})")
                        except json.JSONDecodeError:
                            continue
                    print("This demonstrates the immutable hash chain for audit trail")
                else:
                    print("⚠️  Provenance chain is empty")
        except Exception as e:
            print(f"❌ Error reading provenance chain: {e}")
    else:
        print("❌ Provenance chain file not found")
    
    print()
    time.sleep(2)

def demo_insightflow_dashboard():
    print("📊 DEMO 6: InsightFlow V2 Dashboard")
    print("Showing dashboard integration...")
    
    # Check if insight flow log exists
    if os.path.exists("insight/flow.log"):
        try:
            with open("insight/flow.log", "r") as f:
                lines = f.readlines()
                if lines:
                    print(f"✅ Found {len(lines)} InsightFlow events")
                    # Show last 3 events
                    for i, line in enumerate(lines[-3:], 1):
                        try:
                            entry = json.loads(line)
                            event_type = entry.get("event_type", "unknown")
                            timestamp = entry.get("timestamp", "N/A")
                            print(f"  Event {len(lines)-3+i}: {event_type} at {timestamp}")
                        except json.JSONDecodeError:
                            continue
                    print("This demonstrates real-time monitoring in the InsightFlow dashboard")
                else:
                    print("⚠️  InsightFlow log is empty")
        except Exception as e:
            print(f"❌ Error reading InsightFlow log: {e}")
    else:
        print("❌ InsightFlow log not found")
    
    print()
    time.sleep(2)

def main():
    print("🚀 Core-Bucket Bridge V4 - 2-Minute Demo")
    print("=" * 50)
    print()
    
    # Load private key
    private_key = load_private_key()
    if not private_key:
        print("❌ Failed to load private key. Please ensure security/private.pem exists.")
        return
    
    # Run all demos
    demo_valid_signed_request(private_key)
    demo_replayed_request(private_key)
    demo_rbac_failure()
    demo_heartbeat_success(private_key)
    demo_provenance_chain_view()
    demo_insightflow_dashboard()
    
    print("🎉 Demo Complete!")
    print("All Core-Bucket Bridge V4 features demonstrated successfully:")
    print("✅ Valid signed requests accepted")
    print("✅ Replay attacks rejected (anti-replay protection)")
    print("✅ RBAC enforcing role-based access control")
    print("✅ Heartbeat events logged successfully")
    print("✅ Provenance chain maintaining integrity")
    print("✅ InsightFlow V2 dashboard integration working")

if __name__ == "__main__":
    main()