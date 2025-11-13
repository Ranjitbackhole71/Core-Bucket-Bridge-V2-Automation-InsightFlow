#!/usr/bin/env python3
"""
Simple test script to verify the health endpoint is working
"""

import requests
import time

def test_health_endpoint():
    """Test the /core/health endpoint"""
    try:
        # Wait a moment for server to start
        time.sleep(2)
        
        # Test health endpoint
        response = requests.get("http://localhost:8000/core/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Health endpoint test PASSED")
            print(f"   Status: {data.get('status')}")
            print(f"   Uptime: {data.get('uptime_s', 0):.2f} seconds")
            print(f"   Last sync: {data.get('last_sync_ts', 'N/A')}")
            print(f"   Pending queue: {data.get('pending_queue', 0)}")
            print(f"   Errors (24h): {data.get('error_count_24h', 0)}")
            print(f"   Avg latency (24h): {data.get('avg_latency_ms_24h', 0):.2f} ms")
            return True
        else:
            print(f"❌ Health endpoint test FAILED with status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Health endpoint test FAILED - Could not connect to server")
        print("   Make sure the server is running on http://localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Health endpoint test FAILED with exception: {e}")
        return False

def test_core_update():
    """Test the /core/update endpoint"""
    try:
        # Test data
        payload = {
            "module": "test",
            "data": {"message": "Health check test"}
        }
        
        response = requests.post("http://localhost:8000/core/update", json=payload, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Core update endpoint test PASSED")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            return True
        else:
            print(f"❌ Core update endpoint test FAILED with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Core update endpoint test FAILED with exception: {e}")
        return False

def test_bucket_status():
    """Test the /bucket/status endpoint"""
    try:
        response = requests.get("http://localhost:8000/bucket/status", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Bucket status endpoint test PASSED")
            print(f"   Last sync time: {data.get('last_sync_time', 'N/A')}")
            print(f"   Total sync count: {data.get('total_sync_count', 0)}")
            return True
        else:
            print(f"❌ Bucket status endpoint test FAILED with status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Bucket status endpoint test FAILED with exception: {e}")
        return False

if __name__ == "__main__":
    print("Running health endpoint tests...\n")
    
    # Test all endpoints
    tests = [
        test_health_endpoint,
        test_core_update,
        test_bucket_status
    ]
    
    passed = 0
    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing
    
    print(f"Tests completed: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All tests PASSED!")
        exit(0)
    else:
        print("❌ Some tests FAILED!")
        exit(1)