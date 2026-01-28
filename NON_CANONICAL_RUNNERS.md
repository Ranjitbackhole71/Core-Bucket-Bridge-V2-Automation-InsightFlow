# Core–Bucket Bridge V5 - Non-Canonical Runners (Archived)

**FROZEN FOR PRODUCTION - DO NOT USE**

## 📋 Archived Runner Files

This document lists all non-canonical execution paths that have been identified and archived for production safety.

## 🚫 Forbidden Runners (DO NOT EXECUTE)

### Test Files
These files are for development and testing only:

1. **`automation/plugins/full_sync_test.py`**
   - Purpose: Full synchronization test plugin
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python automation/plugins/full_sync_test.py`

2. **`automation/plugins/sync_test.py`**
   - Purpose: Synchronization test plugin
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python automation/plugins/sync_test.py`

3. **`automation/full_sync_test_runner.py`**
   - Purpose: Test runner for full sync tests
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python automation/full_sync_test_runner.py`

4. **`tests/test_smoke.py`**
   - Purpose: Smoke test suite
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python tests/test_smoke.py`

5. **`test_health_endpoint.py`**
   - Purpose: Health endpoint testing
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python test_health_endpoint.py`

6. **`test_health_security.py`**
   - Purpose: Health security testing
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python test_health_security.py`

7. **`test_heartbeat.py`**
   - Purpose: Heartbeat functionality testing
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python test_heartbeat.py`

8. **`test_plugins.py`**
   - Purpose: Plugin system testing
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python test_plugins.py`

9. **`test_security.py`**
   - Purpose: Security feature testing
   - Status: ARCHIVED - Development testing only
   - DO NOT RUN: `python test_security.py`

### Demo and Script Files
These files are for demonstration and development:

1. **`demo_script.py`**
   - Purpose: Demonstration script
   - Status: ARCHIVED - Development demo only
   - DO NOT RUN: `python demo_script.py`

2. **`final_verification.py`**
   - Purpose: Pre-release verification
   - Status: ARCHIVED - Pre-release only
   - DO NOT RUN: `python final_verification.py`

### Load Testing Files
These files are for performance testing:

1. **`load_test.py`**
   - Purpose: Performance load testing
   - Status: ARCHIVED - Performance testing only
   - DO NOT RUN: `python load_test.py`

2. **`load_test_v5.py`**
   - Purpose: V5 performance load testing
   - Status: ARCHIVED - Performance testing only
   - DO NOT RUN: `python load_test_v5.py`

### Local Development Files
These files are for local development:

1. **`localhost_test.py`**
   - Purpose: Local development testing
   - Status: ARCHIVED - Local development only
   - DO NOT RUN: `python localhost_test.py`

### External Project Files
Files from external projects:

1. **`land-utilization-rl/test_pipeline.py`**
   - Purpose: Land utilization RL pipeline testing
   - Status: ARCHIVED - External project
   - DO NOT RUN: `python land-utilization-rl/test_pipeline.py`

## ✅ Canonical Runners (ONLY THESE ARE APPROVED)

### Production Runners
These are the ONLY files that should be executed in production:

1. **`core_bucket_bridge.py`**
   - Purpose: Core API service
   - Usage: `python core_bucket_bridge.py`
   - Status: ✅ PRODUCTION APPROVED

2. **`automation/runner.py`**
   - Purpose: Automation engine
   - Usage: `python automation/runner.py --once` or `python automation/runner.py --watch`
   - Status: ✅ PRODUCTION APPROVED

## 🛡️ Production Safety Measures

### File Permissions
All archived files should have restricted permissions:
```bash
chmod 600 automation/plugins/full_sync_test.py
chmod 600 automation/plugins/sync_test.py
chmod 600 automation/full_sync_test_runner.py
# ... and so on for all archived files
```

### Directory Structure
Consider moving archived files to a separate directory:
```bash
mkdir archived_runners
mv automation/plugins/full_sync_test.py archived_runners/
mv automation/plugins/sync_test.py archived_runners/
# ... move all archived files
```

### Monitoring
Monitor for unauthorized execution of archived runners:
- Set up file access logging
- Monitor process execution
- Alert on execution of archived files

## 📞 Emergency Procedures

If any archived runner is executed in production:

1. **Immediate Stop**
   - Stop the process immediately
   - Document the incident

2. **Impact Assessment**
   - Check system logs for anomalies
   - Verify data integrity
   - Assess security implications

3. **Recovery**
   - Restart canonical services
   - Validate system state
   - Run health checks

4. **Reporting**
   - Document the incident
   - Update incident response procedures
   - Review access controls

## 📋 Sign-Off

**Backend Lead:** [Name/Signature]
**QA Lead:** Vinayak
**Security Lead:** [Security team contact]

---
**THIS DOCUMENT IS FROZEN FOR PRODUCTION - ANY CHANGES REQUIRE FORMAL APPROVAL**