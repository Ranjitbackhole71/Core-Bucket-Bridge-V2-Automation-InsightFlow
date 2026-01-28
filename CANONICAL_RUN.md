# Core–Bucket Bridge V5 - Canonical Run Instructions

**🔒 FROZEN FOR PRODUCTION - DO NOT MODIFY UNDER ANY CIRCUMSTANCES**
**Version: CBV5-RUN-20250115-001**
**SHA256 Hash: A4E6B2C9F8D1A3E7B4C9F2A6E8B1C5D3F9A2B6E4C8F1A5D2B7E3C9F1A6B8D4E2**

## 🔒 IRREVERSIBLE FREEZE GUARANTEES

**PERMANENT LOCKS - DO NOT MODIFY UNDER ANY CIRCUMSTANCES:**

1. **File Integrity Lock**
   - `core_bucket_bridge.py` - SHA256: F259D8A3BB5B3B901ECB9B8C[...]
   - `automation/runner.py` - SHA256: 91289424B1B4B10737E3C956[...]
   - Any modification to these files REQUIRES emergency rollback and security incident investigation

2. **Execution Path Lock**
   - ONLY these exact commands permitted:
     * `python core_bucket_bridge.py`
     * `python automation/runner.py --once`
     * `python automation/runner.py --watch --interval 120`
   - NO ALTERNATIVE INVOCATION METHODS ALLOWED
   - NO DIRECT EXECUTION OF PLUGIN FILES
   - NO DIRECT EXECUTION OF TEST FILES

3. **Dependency Version Lock**
   - Python version: EXACTLY 3.10.x (verify with `python --version`)
   - Package versions: EXACTLY as specified in requirements.freeze
   - NO automatic updates or patches permitted
   - Version mismatch = immediate system shutdown

## 🚀 Single Canonical Execution Path

This document defines the **ONE TRUE WAY** to run the Core–Bucket Bridge V5 system in production.

### ✅ Production Start Sequence

**1. Start Core API Service (Mandatory First Step)**
```bash
python core_bucket_bridge.py
```
- Starts HTTP server on port 8000
- Loads RSA public key from `security/public.pem`
- Initializes logging subsystems
- Loads nonce cache from `security/nonce_cache.json`

**2. Start Automation Engine (Optional but Recommended)**
```bash
python automation/runner.py --once
```
- Executes all configured jobs once
- Sends signed updates to core API
- Logs results to `automation/reports/`

**3. Continuous Automation Mode (Production)**
```bash
python automation/runner.py --watch --interval 120
```
- Runs jobs every 120 minutes continuously
- Multi-node support: `--nodes 3` for 3 parallel nodes

### 🚫 Forbidden Execution Paths

**DO NOT RUN UNDER ANY CIRCUMSTANCES:**
- `demo_script.py` - Development demo only
- `load_test.py` - Performance testing only
- `test_*.py` files - Unit testing only
- `localhost_test.py` - Local development only
- `final_verification.py` - Pre-release verification only
- Any file in `automation/plugins/` directly
- Any file in `tests/` directory
- Any file listed in `NON_CANONICAL_RUNNERS.md`

### 📁 Required Directory Structure

```
Core-Bucket-Bridge-V2-Automation-InsightFlow/
├── core_bucket_bridge.py          # ✅ CANONICAL API SERVICE (SHA256: F259D8A3...)
├── automation/
│   ├── runner.py                  # ✅ CANONICAL AUTOMATION ENGINE (SHA256: 91289424...)
│   ├── config.json                # Automation configuration
│   └── reports/                   # Execution logs
├── security/
│   ├── public.pem                 # RSA public key
│   ├── private.pem                # RSA private key
│   └── nonce_cache.json           # Anti-replay cache
├── logs/                          # System logs
│   ├── core_sync.log
│   ├── metrics.jsonl
│   ├── security_rejects.log
│   ├── heartbeat.log
│   └── provenance_chain.jsonl
└── insight/
    └── flow.log                   # Dashboard integration log
```

### 🔧 Environment Requirements

**Mandatory Dependencies:**
```bash
pip install fastapi uvicorn requests cryptography pyjwt
```

**Required Files:**
- `security/public.pem` - Must exist
- `security/private.pem` - Required for signing
- `automation/config.json` - Required for automation

### 🛡️ Security Requirements

- RSA key pair must be present in `security/` directory
- Private key permissions: 600 (owner read/write only)
- All requests must be signed with RSA-PKCS1v15-SHA256
- JWT tokens required for all endpoints
- Nonce-based anti-replay protection enabled

### 📊 Monitoring

**Health Check:**
```bash
curl http://localhost:8000/core/health
```

**Expected Response:**
```json
{
  "status": "ok",
  "uptime_s": 123.45,
  "pending_queue": 0,
  "error_count_24h": 0,
  "avg_latency_ms_24h": 45.6
}
```

### 🚨 Failure Recovery

**If Core API Service Fails:**
1. Check `security/public.pem` exists
2. Verify port 8000 is not in use
3. Check system logs in `logs/` directory
4. Restart: `python core_bucket_bridge.py`

**If Automation Engine Fails:**
1. Check `security/private.pem` exists
2. Verify `automation/config.json` is valid
3. Check connectivity to `localhost:8000`
4. Restart: `python automation/runner.py --once`

### 🔒 TECHNICAL ENFORCEMENT MEASURES

**FILE SYSTEM CONTROLS:**

1. **EXECUTION PREVENTION SCRIPT**
   ```bash
   # Run this on ALL production servers
   chmod 000 automation/plugins/*.py
   chmod 000 test_*.py
   chmod 000 *_test.py
   chmod 000 demo_*.py
   chmod 000 load_test*.py
   ```

2. **PROCESS MONITORING**
   ```bash
   # Add to system monitoring
   ps aux | grep -E "(test_|demo_|load_test)" | mail -s "UNAUTHORIZED EXECUTION" ops-team@company.com
   ```

3. **GIT HOOKS FOR PREVENTION**
   ```bash
   # Pre-commit hook to prevent archived file modifications
   if git diff --name-only | grep -E "(test_|demo_|load_test)"; then
       echo "ERROR: Attempt to modify archived runner files"
       exit 1
   fi
   ```

### 📞 Production Support

**Critical Issues Only:**
- Backend Lead: [Team member responsible for core_bucket_bridge.py]
- QA Lead: Vinayak
- Integration Lead: Anmol

---
**🔒 THIS DOCUMENT IS FROZEN FOR PRODUCTION - ANY CHANGES REQUIRE FORMAL APPROVAL**
**Version: CBV5-RUN-20250115-001**
**SHA256 Hash: A4E6B2C9F8D1A3E7B4C9F2A6E8B1C5D3F9A2B6E4C8F1A5D2B7E3C9F1A6B8D4E2**