#!/usr/bin/env python3
"""
Test script for Core-Bucket Bridge V3 plugins
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'automation', 'plugins'))

def test_heartbeat_plugin():
    """Test heartbeat plugin"""
    print("Testing heartbeat plugin...")
    try:
        import heartbeat
        result = heartbeat.run()
        print(f"✅ Heartbeat plugin executed successfully")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Heartbeat plugin failed: {e}")
        return False

def test_sync_test_plugin():
    """Test sync test plugin"""
    print("\nTesting sync test plugin...")
    try:
        import sync_test
        result = sync_test.run()
        print(f"✅ Sync test plugin executed successfully")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Sync test plugin failed: {e}")
        return False

def test_latency_probe_plugin():
    """Test latency probe plugin"""
    print("\nTesting latency probe plugin...")
    try:
        import latency_probe
        result = latency_probe.run()
        print(f"✅ Latency probe plugin executed successfully")
        print(f"Result: {result}")
        return True
    except Exception as e:
        print(f"❌ Latency probe plugin failed: {e}")
        return False

if __name__ == "__main__":
    print("Running Core-Bucket Bridge V3 Plugin Tests...\n")
    
    tests = [
        ("Heartbeat Plugin", test_heartbeat_plugin),
        ("Sync Test Plugin", test_sync_test_plugin),
        ("Latency Probe Plugin", test_latency_probe_plugin)
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
    
    print(f"\nPlugin tests completed: {passed}/{len(tests)} passed")
    
    if passed == len(tests):
        print("🎉 All plugin tests PASSED!")
    else:
        print("❌ Some plugin tests FAILED!")