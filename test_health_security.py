#!/usr/bin/env python3
"""
Test script for Core-Bucket Bridge V3 health endpoint security metrics
"""

import requests
import json

def test_health_security_metrics():
    """Test that health endpoint returns security metrics"""
    print("Testing health endpoint security metrics...")
    
    try:
        response = requests.get("http://localhost:8000/core/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health endpoint returned status code 200")
            print(f"Response: {json.dumps(data, indent=2)}")
            
            # Check if security metrics are present
            if "security" in data:
                security = data["security"]
                print(f"✅ Security metrics present in response")
                
                # Check required security fields
                required_fields = ["rejected_signatures", "replay_attempts", "last_valid_signature_timestamps"]
                missing_fields = [field for field in required_fields if field not in security]
                
                if not missing_fields:
                    print(f"✅ All required security fields present")
                    print(f"   Rejected signatures: {security['rejected_signatures']}")
                    print(f"   Replay attempts: {security['replay_attempts']}")
                    print(f"   Last valid signature timestamps: {security['last_valid_signature_timestamps']}")
                    return True
                else:
                    print(f"❌ Missing security fields: {missing_fields}")
                    return False
            else:
                print(f"❌ Security metrics missing from response")
                return False
        else:
            print(f"❌ Health endpoint returned status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error testing health endpoint: {e}")
        return False

if __name__ == "__main__":
    print("Running Core-Bucket Bridge V3 Health Security Metrics Test...\n")
    
    print("Please ensure the Core-Bucket Bridge server is running on http://localhost:8000")
    input("Press Enter to continue...")
    
    if test_health_security_metrics():
        print("\n🎉 Health security metrics test PASSED!")
    else:
        print("\n❌ Health security metrics test FAILED!")