#!/usr/bin/env python3
"""
Test script for replay attack simulation in go-live testing.
Verifies that the system detects and rejects duplicate requests using nonce protection.
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import jwt


def test_replay_attack():
    """Test that the system detects and rejects replay attacks."""
    print("Testing replay attack simulation...")
    
    # Load private key for signing
    try:
        with open("security/private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    except FileNotFoundError:
        print("ERROR: security/private.pem not found")
        return False
    
    # Prepare payload
    payload = {
        "module": "education",
        "data": {
            "student_id": f"STU{uuid.uuid4().hex[:6].upper()}",
            "course_id": "CS101",
            "course_name": "Introduction to Computer Science",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "session_id": str(uuid.uuid4())
    }
    
    # Sign the payload
    try:
        payload_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        signature = private_key.sign(
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        print(f"ERROR: Failed to sign payload: {e}")
        return False
    
    # Use the SAME nonce for both requests to simulate replay attack
    shared_nonce = str(uuid.uuid4())
    
    # Create secure payload with shared nonce
    secure_payload = {
        "payload": payload,
        "signature": signature_b64,
        "nonce": shared_nonce
    }
    
    # Create JWT token using the hardcoded "secret" as used in core service
    # Use a longer expiration time to avoid precision issues
    try:
        token_payload = {
            "sub": "test-client",
            "exp": (datetime.utcnow() + timedelta(hours=24)).timestamp(),  # 24 hours to be sure
            "roles": ["module"],
            "iat": datetime.utcnow().timestamp()
        }
        # Use the hardcoded "secret" as in the core service
        token = jwt.encode(token_payload, "secret", algorithm="HS256")
        auth_header = f"Bearer {token}"
    except Exception as e:
        print(f"ERROR: Failed to create JWT token: {e}")
        return False
    
    # Send first request (should succeed)
    url = "http://localhost:8000/core/update"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    
    try:
        print("Sending first request (should succeed)...")
        response1 = requests.post(url, json=secure_payload, headers=headers, timeout=30)
        
        if response1.status_code == 200:
            print(f"[SUCCESS] First request succeeded (Status: {response1.status_code})")
        else:
            print(f"[FAILED] First request failed unexpectedly (Status: {response1.status_code})")
            print(f"   Response: {response1.text}")
            return False
        
        # Send second request with same nonce (should be rejected as replay attack)
        print("Sending second request with same nonce (should be rejected as replay attack)...")
        response2 = requests.post(url, json=secure_payload, headers=headers, timeout=30)
        
        # Check if the system properly rejected the replay attempt
        if response2.status_code == 401 or "replay" in response2.text.lower() or "duplicate" in response2.text.lower():
            print(f"[SUCCESS] Replay attack test PASSED - Second request properly rejected (Status: {response2.status_code})")
            
            # Check security logs for replay detection
            try:
                with open("logs/security_rejects.log", "r") as f:
                    lines = f.readlines()
                    replay_detected = False
                    for line in reversed(lines[-10:]):  # Check last 10 lines
                        if "Replay attack detected" in line or "replay" in line.lower():
                            print(f"[SUCCESS] Replay attack detected in security logs: {line.strip()[:100]}...")
                            replay_detected = True
                            break
                    
                    if not replay_detected:
                        print("[WARNING] Could not confirm replay detection in security logs")
                        
            except FileNotFoundError:
                print("[WARNING] security_rejects.log not found - may not be running yet")
            
            return True
        else:
            print(f"[FAILED] Replay attack test FAILED - Second request was accepted when it should have been rejected (Status: {response2.status_code})")
            print(f"   Response: {response2.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection error - is the core service running on http://localhost:8000?")
        print("   To run the service: python core_bucket_bridge.py")
        return False
    except Exception as e:
        print(f"[FAILED] Replay attack test FAILED with exception: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("CORE-BUCKET BRIDGE V5 - REPLAY ATTACK SIMULATION TEST")
    print("="*60)
    
    success = test_replay_attack()
    
    print("="*60)
    if success:
        print("REPLAY ATTACK SIMULATION: [PASSED]")
    else:
        print("REPLAY ATTACK SIMULATION: [FAILED]")
    print("="*60)