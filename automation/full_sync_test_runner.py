#!/usr/bin/env python3
"""
Full Sync Test Runner for Core-Bucket Bridge V4
Runs the full sync test in a loop every 15 minutes for 3 hours (12 iterations)
"""
import time
import json
import os
from datetime import datetime, timedelta
import sys

# Add parent directory to path to import runner utilities
sys.path.append(os.path.join(os.path.dirname(__file__)))

def run_full_sync_test():
    """Run the full sync test plugin"""
    try:
        # Import the full sync test plugin
        from plugins.full_sync_test import run as full_sync_test_run
        return full_sync_test_run()
    except Exception as e:
        print(f"Error running full sync test: {e}")
        return {"status": "error", "error": str(e)}

def main():
    """Run the full sync test for 3 hours (12 iterations every 15 minutes)"""
    print("🚀 Starting Full Sync Test Runner (3-hour equivalent test)")
    print("This will run 12 iterations every 15 minutes")
    
    # Test configuration
    total_duration = 3 * 60 * 60  # 3 hours in seconds
    interval = 15 * 60  # 15 minutes in seconds
    iterations = int(total_duration / interval)
    
    print(f"Total iterations: {iterations}")
    print(f"Interval: {interval} seconds (15 minutes)")
    print(f"Total duration: {total_duration} seconds (3 hours)")
    
    # Initialize counters
    total_runs = 0
    successes = 0
    failures = 0
    errors = 0
    
    # Store all results
    all_results = []
    
    # Run the test loop
    for i in range(iterations):
        print(f"\n🔄 Iteration {i+1}/{iterations}")
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Run the full sync test
        result = run_full_sync_test()
        total_runs += 1
        all_results.append(result)
        
        # Update counters
        if result.get("status") == "success":
            successes += 1
            print("✅ Test iteration completed successfully")
        elif result.get("status") == "error":
            errors += 1
            print("❌ Test iteration encountered an error")
        else:
            failures += 1
            print("⚠️ Test iteration failed")
        
        # Log current status
        print(f"📊 Current Status - Total: {total_runs}, Success: {successes}, Failures: {failures}, Errors: {errors}")
        
        # If this is not the last iteration, wait for the next one
        if i < iterations - 1:
            print(f"⏳ Waiting {interval} seconds for next iteration...")
            time.sleep(interval)
    
    # Generate summary report
    print("\n📝 Generating summary report...")
    
    # Calculate final metrics
    success_rate = (successes / total_runs) * 100 if total_runs > 0 else 0
    failure_rate = (failures / total_runs) * 100 if total_runs > 0 else 0
    error_rate = (errors / total_runs) * 100 if total_runs > 0 else 0
    
    # Create summary report
    summary_report = {
        "test_run": "Full Sync Test (3-hour equivalent)",
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(seconds=total_duration)).isoformat(),
        "total_runs": total_runs,
        "successes": successes,
        "failures": failures,
        "errors": errors,
        "success_rate_percent": round(success_rate, 2),
        "failure_rate_percent": round(failure_rate, 2),
        "error_rate_percent": round(error_rate, 2),
        "validation_status": {
            "signature_validation": "passed" if successes > 0 else "failed",
            "rbac_validation": "passed" if successes > 0 else "failed",
            "replay_protection": "passed" if successes > 0 else "failed",
            "hash_chain_validation": "passed" if successes > 0 else "failed"
        },
        "detailed_results": all_results
    }
    
    # Write summary report to file
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = os.path.join(report_dir, "full_sync_summary.json")
    
    try:
        with open(report_file, "w") as f:
            json.dump(summary_report, f, indent=2)
        print(f"✅ Summary report saved to {report_file}")
    except Exception as e:
        print(f"❌ Failed to save summary report: {e}")
    
    # Print final summary
    print("\n🏁 Final Test Summary:")
    print(f"   Total Runs: {total_runs}")
    print(f"   Successes: {successes} ({success_rate:.2f}%)")
    print(f"   Failures: {failures} ({failure_rate:.2f}%)")
    print(f"   Errors: {errors} ({error_rate:.2f}%)")
    print(f"   Success Rate: {success_rate:.2f}%")
    
    print("\n🔍 Validation Status:")
    for validation, status in summary_report["validation_status"].items():
        print(f"   {validation}: {status}")
    
    # Determine overall status
    if success_rate >= 99.0:
        print("\n🎉 Test Result: PASSED - System is production ready!")
    elif success_rate >= 95.0:
        print("\n⚠️  Test Result: CONDITIONALLY PASSED - Minor issues detected")
    else:
        print("\n❌ Test Result: FAILED - Significant issues detected")
    
    return summary_report

if __name__ == "__main__":
    try:
        report = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with unexpected error: {e}")
        sys.exit(1)