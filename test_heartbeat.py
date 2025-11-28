#!/usr/bin/env python3
"""
Test script for Core-Bucket Bridge V3 heartbeat endpoint
"""

import requests
import json
import jwt
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime, timedelta
import uuid

# Load private key for signing
with open("security/private.pem", "rb") as key_file:
    private_key = serialization.load_pem_private_key(key_file.read(), password=None)

def create_jwt_token(roles=["module"]):
    """Create a JWT token for testing"""
    payload = {
        "iss": "core-bucket-bridge",
        "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
        "roles": roles
    }
    token = jwt.encode(payload, "secret", algorithm="HS256")
    return f"Bearer {token}"

def sign_payload(payload):
    """Sign a payload with RSA private key"""
    payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def test_valid_heartbeat():
    """Test a valid heartbeat request"""
    print("Testing valid heartbeat...")
    
    # Create payload
    payload = {
        "module": "test_module",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "alive",
        "metrics": {"cpu": 25.5, "memory": 45.2}
    }
    
    # Sign payload
    signature = sign_payload(payload)
    
    # Create JWT token
    token = create_jwt_token()
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": str(uuid.uuid4())
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_signature_heartbeat():
    """Test heartbeat with invalid signature"""
    print("\nTesting invalid signature heartbeat...")
    
    # Create payload
    payload = {
        "module": "test_module",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "alive",
        "metrics": {"cpu": 25.5, "memory": 45.2}
    }
    
    # Use invalid signature
    signature = "invalid_signature_here"
    
    # Create JWT token
    token = create_jwt_token()
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": str(uuid.uuid4())
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200 and response.json().get("status") == "rejected"
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_replay_attack_heartbeat():
    """Test replay attack with duplicate nonce"""
    print("\nTesting replay attack heartbeat...")
    
    # Create payload
    payload = {
        "module": "test_module",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "alive",
        "metrics": {"cpu": 30.1, "memory": 50.7}
    }
    
    # Sign payload
    signature = sign_payload(payload)
    
    # Create JWT token
    token = create_jwt_token()
    
    # Use same nonce for both requests
    nonce = str(uuid.uuid4())
    
    # Send first request
    secure_payload1 = {
        "payload": payload,
        "signature": signature,
        "nonce": nonce
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        # First request
        response1 = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload1,
            headers=headers
        )
        print(f"First request - Status Code: {response1.status_code}")
        
        # Second request with same nonce (replay attack)
        response2 = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload1,
            headers=headers
        )
        print(f"Replay request - Status Code: {response2.status_code}")
        print(f"Replay response: {response2.text}")
        
        return response2.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_heartbeat_without_required_role():
    """Test heartbeat with token missing required role"""
    print("\nTesting heartbeat without required role...")
    
    # Create payload
    payload = {
        "module": "test_module",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": "alive",
        "metrics": {"cpu": 25.5, "memory": 45.2}
    }
    
    # Sign payload
    signature = sign_payload(payload)
    
    # Create JWT token WITHOUT module role
    token = create_jwt_token(["admin"])  # Admin can access, but let's test a role that can't
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": str(uuid.uuid4())
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/heartbeat",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        # Module role should be required, so this should fail
        return response.status_code == 403
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Running Core-Bucket Bridge V3 Heartbeat Tests...\n")
    
    # Start the server in the background
    print("Please ensure the Core-Bucket Bridge server is running on http://localhost:8000")
    input("Press Enter to continue...")
    
    tests = [
        ("Valid Heartbeat", test_valid_heartbeat),
        ("Invalid Signature", test_invalid_signature_heartbeat),
        ("Replay Attack", test_replay_attack_heartbeat),
        ("Role Verification", test_heartbeat_without_required_role)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} PASSED")
                passed += 1
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\nHeartbeat tests completed: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All heartbeat tests PASSED!")
    else:
        print("❌ Some heartbeat tests FAILED!")