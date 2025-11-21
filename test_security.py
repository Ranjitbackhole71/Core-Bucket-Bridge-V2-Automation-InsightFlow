#!/usr/bin/env python3
"""
Test script for Core-Bucket Bridge V3 security features
"""

import requests
import json
import jwt
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from datetime import datetime, timedelta

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

def test_valid_request():
    """Test a valid signed request with valid JWT"""
    print("Testing valid request...")
    
    # Create payload
    payload = {
        "module": "test",
        "data": {"message": "Valid test request"},
        "session_id": "test_session_123"
    }
    
    # Sign payload
    signature = sign_payload(payload)
    
    # Create JWT token
    token = create_jwt_token()
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": "nonce_001"
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_signature():
    """Test request with invalid signature"""
    print("\nTesting invalid signature...")
    
    # Create payload
    payload = {
        "module": "test",
        "data": {"message": "Invalid signature test"},
        "session_id": "test_session_456"
    }
    
    # Use invalid signature
    signature = "invalid_signature_here"
    
    # Create JWT token
    token = create_jwt_token()
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": "nonce_002"
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200 and response.json().get("status") == "rejected"
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_invalid_token():
    """Test request with invalid JWT token"""
    print("\nTesting invalid token...")
    
    # Create payload
    payload = {
        "module": "test",
        "data": {"message": "Invalid token test"},
        "session_id": "test_session_789"
    }
    
    # Sign payload
    signature = sign_payload(payload)
    
    # Use invalid token
    token = "Bearer invalid_token_here"
    
    # Send request
    secure_payload = {
        "payload": payload,
        "signature": signature,
        "nonce": "nonce_003"
    }
    
    headers = {
        "Authorization": token
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload,
            headers=headers
        )
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return response.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_replay_attack():
    """Test replay attack with duplicate nonce"""
    print("\nTesting replay attack...")
    
    # First request with nonce
    payload1 = {
        "module": "test",
        "data": {"message": "First request"},
        "session_id": "test_session_111"
    }
    
    signature1 = sign_payload(payload1)
    token1 = create_jwt_token()
    
    secure_payload1 = {
        "payload": payload1,
        "signature": signature1,
        "nonce": "replay_nonce_001"
    }
    
    headers1 = {
        "Authorization": token1
    }
    
    try:
        # First request
        response1 = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload1,
            headers=headers1
        )
        print(f"First request - Status Code: {response1.status_code}")
        
        # Second request with same nonce (replay attack)
        response2 = requests.post(
            "http://localhost:8000/core/update",
            json=secure_payload1,
            headers=headers1
        )
        print(f"Replay request - Status Code: {response2.status_code}")
        print(f"Replay response: {response2.text}")
        
        return response2.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Running Core-Bucket Bridge V3 Security Tests...\n")
    
    # Start the server in the background
    print("Please ensure the Core-Bucket Bridge server is running on http://localhost:8000")
    input("Press Enter to continue...")
    
    tests = [
        ("Valid Request", test_valid_request),
        ("Invalid Signature", test_invalid_signature),
        ("Invalid Token", test_invalid_token),
        ("Replay Attack", test_replay_attack)
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
    
    print(f"\nSecurity tests completed: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All security tests PASSED!")
    else:
        print("❌ Some security tests FAILED!")