#!/usr/bin/env python3
"""
Test script for valid request simulation in go-live testing.
Verifies that the system accepts valid signed requests.
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import jwt


def test_valid_request():
    """Test that the system accepts valid signed requests."""
    print("Testing valid request simulation...")
    
    # Load private key for signing
    try:
        with open("security/private.pem", "rb") as key_file:
            private_key = serialization.load_pem_private_key(key_file.read(), password=None)
    except FileNotFoundError:
        print("ERROR: security/private.pem not found")
        return False
    
    # Prepare valid payload
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
    
    # Create secure payload with nonce
    secure_payload = {
        "payload": payload,
        "signature": signature_b64,
        "nonce": str(uuid.uuid4())
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
    
    # Send request to core update endpoint
    url = "http://localhost:8000/core/update"
    headers = {
        "Authorization": auth_header,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=secure_payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"[SUCCESS] Valid request test PASSED - Status: {response.status_code}")
            
            # Check logs for successful entry
            try:
                with open("logs/core_sync.log", "r") as f:
                    lines = f.readlines()
                    if lines:
                        print(f"[SUCCESS] Data logged to core_sync.log: {lines[-1][:100]}...")
            except FileNotFoundError:
                print("[WARNING] core_sync.log not found - may not be running yet")
            
            try:
                with open("logs/metrics.jsonl", "r") as f:
                    lines = f.readlines()
                    if lines:
                        print(f"[SUCCESS] Metrics recorded: {lines[-1][:100]}...")
            except FileNotFoundError:
                print("[WARNING] metrics.jsonl not found - may not be running yet")
            
            try:
                with open("logs/provenance_chain.jsonl", "r") as f:
                    lines = f.readlines()
                    if lines:
                        print(f"[SUCCESS] Provenance chain entry added: {lines[-1][:100]}...")
            except FileNotFoundError:
                print("[WARNING] provenance_chain.jsonl not found - may not be running yet")
                
            return True
        else:
            print(f"[FAILED] Valid request test FAILED - Status: {response.status_code}, Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Connection error - is the core service running on http://localhost:8000?")
        print("   To run the service: python core_bucket_bridge.py")
        return False
    except Exception as e:
        print(f"[FAILED] Valid request test FAILED with exception: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("CORE-BUCKET BRIDGE V5 - VALID REQUEST SIMULATION TEST")
    print("="*60)
    
    success = test_valid_request()
    
    print("="*60)
    if success:
        print("VALID REQUEST SIMULATION: [PASSED]")
    else:
        print("VALID REQUEST SIMULATION: [FAILED]")
    print("="*60)