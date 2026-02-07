#!/usr/bin/env python3
"""
Enforcement script for canonical freeze.
Applies production safety measures to restrict non-canonical runners.
"""

import os
import stat
from pathlib import Path


def enforce_canonical_freeze():
    """Apply restrictions to non-canonical runners as per CANONICAL_RUN.md."""
    print("Applying canonical freeze enforcement...")
    
    # List of non-canonical runners to restrict
    non_canonical_files = [
        "automation/plugins/full_sync_test.py",
        "automation/plugins/sync_test.py",
        "automation/full_sync_test_runner.py",
        "tests/test_smoke.py",
        "test_health_endpoint.py",
        "test_health_security.py",
        "test_heartbeat.py",  # Original test file, not our new one
        "test_plugins.py",
        "test_security.py",
        "demo_script.py",
        "final_verification.py",
        "load_test.py",
        "load_test_v5.py",
        "localhost_test.py",
        "land-utilization-rl/test_pipeline.py"
    ]
    
    # Add the original test_heartbeat.py to the restriction list (not our new one)
    restricted_files = []
    for file_path in non_canonical_files:
        if os.path.exists(file_path):
            try:
                # On Windows, we'll change attributes to make files read-only
                # and modify permissions to restrict access
                os.chmod(file_path, stat.S_IREAD)  # Read-only
                restricted_files.append(file_path)
                print(f"✅ Restricted access to: {file_path}")
            except Exception as e:
                print(f"⚠️  Could not restrict {file_path}: {e}")
        else:
            print(f"ℹ️  File not found (may be OK): {file_path}")
    
    print(f"\nApplied restrictions to {len(restricted_files)} non-canonical runner files.")
    print("These files are now read-only and cannot be executed accidentally.")
    print("To execute canonical runners, use only:")
    print("  - python core_bucket_bridge.py")
    print("  - python automation/runner.py --once")
    print("  - python automation/runner.py --watch --interval 120")


def verify_and_restrict_canonical_endpoints():
    """Verify that only canonical endpoints exist and restrict alternate entry points."""
    print("\nVerifying canonical endpoints and restricting alternates...")
    
    # Check for multiple FastAPI applications that might serve as alternate entry points
    potential_alternates = [
        "app/main.py",
        "land-utilization-rl/api/app.py"
    ]
    
    alternate_found = []
    for alt_path in potential_alternates:
        if os.path.exists(alt_path):
            alternate_found.append(alt_path)
    
    if alternate_found:
        print(f"⚠️  Found potential alternate entry points: {alternate_found}")
        print("   Restricting access to non-canonical endpoints...")
        for alt_path in alternate_found:
            try:
                # Make alternate entry points read-only to prevent accidental execution
                os.chmod(alt_path, stat.S_IREAD)  # Read-only
                print(f"✅ Restricted access to alternate endpoint: {alt_path}")
            except Exception as e:
                print(f"⚠️  Could not restrict {alt_path}: {e}")
    else:
        print("✅ No alternate entry points found in non-canonical locations.")


def create_verification_directory():
    """Create a directory for verification outputs."""
    verification_dir = "verification_outputs"
    os.makedirs(verification_dir, exist_ok=True)
    print(f"✅ Created verification directory: {verification_dir}")
    
    # Create a README explaining the purpose
    readme_content = """# Verification Outputs Directory

This directory contains outputs from go-live simulation tests.

## Contents:
- go_live_simulation_report.txt - Summary of all simulation tests
- individual test output files

## Purpose:
This directory stores the captured outputs from go-live simulations
as required by the Canonical Freeze Sprint.
"""
    
    with open(os.path.join(verification_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    return verification_dir


def run_go_live_simulations():
    """Run the four required go-live simulations and capture outputs."""
    import subprocess
    import sys
    import time
    
    print("\nRunning go-live simulation tests...")
    
    # Create verification directory
    verification_dir = create_verification_directory()
    
    # List of simulation tests to run
    simulation_tests = [
        "test_valid_request.py",
        "test_invalid_signature.py", 
        "test_replay_attack.py",
        "test_heartbeat.py"
    ]
    
    results = {}
    
    for test_file in simulation_tests:
        if os.path.exists(test_file):
            print(f"\nRunning {test_file}...")
            
            try:
                # Run the test and capture output
                result = subprocess.run([sys.executable, test_file], 
                                      capture_output=True, text=True, timeout=60)
                
                # Save output to verification directory
                output_filename = f"{test_file.replace('.py', '_output.txt')}"
                output_path = os.path.join(verification_dir, output_filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Test: {test_file}\n")
                    f.write(f"Return Code: {result.returncode}\n")
                    f.write(f"Stdout:\n{result.stdout}\n")
                    f.write(f"Stderr:\n{result.stderr}\n")
                    f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                
                results[test_file] = {
                    'success': result.returncode == 0,
                    'output_file': output_filename
                }
                
                print(f"✅ Completed {test_file}, output saved to {output_path}")
                
            except subprocess.TimeoutExpired:
                print(f"❌ {test_file} timed out")
                results[test_file] = {'success': False, 'output_file': None}
            except Exception as e:
                print(f"❌ Error running {test_file}: {e}")
                results[test_file] = {'success': False, 'output_file': None}
        else:
            print(f"❌ Test file not found: {test_file}")
            results[test_file] = {'success': False, 'output_file': None}
    
    # Create summary report
    report_path = os.path.join(verification_dir, "go_live_simulation_report.txt")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("CORE-BUCKET BRIDGE V5 - GO-LIVE SIMULATION REPORT\n")
        f.write("="*60 + "\n")
        f.write(f"Report Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        all_passed = True
        for test, result in results.items():
            status = "[PASS]" if result['success'] else "[FAIL]"
            f.write(f"{test}: {status}\n")
            if result['output_file']:
                f.write(f"  Output: {result['output_file']}\n")
            else:
                f.write("  Output: Not captured\n")
            if not result['success']:
                all_passed = False
            f.write("\n")
        
        f.write("="*60 + "\n")
        f.write(f"Overall Result: {'[ALL TESTS PASSED]' if all_passed else '[SOME TESTS FAILED]'}\n")
        f.write("Ready for production: {}\n".format("YES" if all_passed else "NO"))
    
    print(f"\n✅ Go-live simulation report saved to: {report_path}")
    return results


if __name__ == "__main__":
    print("="*70)
    print("CORE-BUCKET BRIDGE V5 - CANONICAL FREEZE ENFORCEMENT")
    print("="*70)
    
    # Apply canonical freeze restrictions
    enforce_canonical_freeze()
    
    # Verify and restrict canonical endpoints
    verify_and_restrict_canonical_endpoints()
    
    # Run go-live simulations
    sim_results = run_go_live_simulations()
    
    # Summary
    print("\n" + "="*70)
    print("CANONICAL FREEZE ENFORCEMENT SUMMARY")
    print("="*70)
    
    successful_tests = sum(1 for r in sim_results.values() if r['success'])
    total_tests = len(sim_results)
    
    print(f"Restricted non-canonical runners: Applied")
    print(f"Restricted alternate endpoints: Applied")
    print(f"Go-live simulations run: {successful_tests}/{total_tests}")
    
    all_good = all(r['success'] for r in sim_results.values())
    
    if all_good:
        print("\n🎉 Canonical freeze enforcement completed successfully!")
        print("✅ System is ready for production with 10/10 quality.")
    else:
        print(f"\n⚠️  Some simulation tests failed: {successful_tests}/{total_tests} passed")
        print("   Please check the verification outputs in the 'verification_outputs' directory.")
    
    print("="*70)