# Core–Bucket Bridge V5 - Integration Contract (FROZEN)

**🔒 FROZEN FOR PRODUCTION - DO NOT MODIFY UNDER ANY CIRCUMSTANCES**
**Version: CBV5-INT-20250115-001**
**SHA256 Hash: 2E7B9A3D4F6C8E1A5B9D3F7C2E8A6B1D4F9C7E3A5B8D1F6C4E9A2B7D8E3F6C1A**
**Contract Identifier: CB-V5-20250115-001**

ANY MODIFICATION INVALIDATES THIS CONTRACT.
NEW VERSION REQUIRES:
1. New contract identifier
2. Stakeholder approval from ALL teams
3. Complete re-testing of all integrations
4. Updated deployment approval process

## 🔒 CONTRACT VERSION CONTROL

**FROZEN SIGNATURE BLOCK:**
Signed: _____________________ Date: ____________
Role: Backend Lead
Signature validates this exact version as production contract.

## 🔐 Core–Bucket Bridge V5 - System Overview

The Core–Bucket Bridge V5 is a production-ready system that provides secure, deterministic rule execution with anti-replay protection and comprehensive observability.

## 🔄 Integration Endpoints

### 1. Core API Service (`core_bucket_bridge.py`)

**Base URL:** `http://localhost:8000/core`

#### POST `/execute`
Execute a rule with anti-replay protection.

**Request Body:**
```json
{
  "module": "education",
  "rule_id": "EDU-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "student_id": "STU123",
    "course_id": "CS101"
  },
  "nonce": "abc123def456"
}
```

**Security Requirements:**
- Request must be signed with RSA-PKCS1v15-SHA256
- JWT token required in Authorization header
- Nonce must be unique (anti-replay protection)
- Timestamp must be within 5-minute window

**Response:**
```json
{
  "status": "success",
  "module": "education",
  "rule_id": "EDU-001",
  "timestamp": "2025-01-15T10:30:00Z",
  "nonce": "abc123def456",
  "result": {
    "message": "Rule executed successfully",
    "data": {...}
  }
}
```

#### GET `/health`
System health check with metrics.

**Response:**
```json
{
  "status": "ok",
  "uptime_s": 3600.5,
  "pending_queue": 0,
  "error_count_24h": 0,
  "avg_latency_ms_24h": 45.2
}
```

### 2. Automation Engine (`automation/runner.py`)

**Execution Modes:**
- `--once`: Run all jobs once
- `--watch --interval 120`: Run jobs every 120 minutes

**Job Configuration (`automation/config.json`):**
```json
{
  "jobs": [
    {
      "name": "education_sync",
      "module": "education",
      "rule_id": "EDU-001",
      "schedule": "0 */2 * * *",
      "data": {
        "batch_size": 100
      }
    }
  ]
}
```

## 📊 Observability Contract

### Log Files

**1. Core Sync Log (`logs/core_sync.log`)**
```
2025-01-15T10:30:00Z - {"module": "education", "session_id": "abc123", "timestamp": "2025-01-15T10:30:00Z", "data": {...}}
```

**2. Metrics Log (`logs/metrics.jsonl`)**
```json
{"timestamp": "2025-01-15T10:30:00Z", "endpoint": "/core/execute", "module": "education", "status": "success", "latency_ms": 45, "pending_queue": 0}
```

**3. Security Rejects Log (`logs/security_rejects.log`)**
```
2025-01-15T10:30:00Z - {"error": "Invalid signature", "module": "education", "rule_id": "EDU-001"}
```

**4. Heartbeat Log (`logs/heartbeat.log`)**
```
2025-01-15T10:30:00Z - {"module": "core", "status": "alive", "timestamp": "2025-01-15T10:30:00Z"}
```

**5. Provenance Chain (`logs/provenance_chain.jsonl`)**
```json
{"timestamp": "2025-01-15T10:30:00Z", "module": "education", "rule_id": "EDU-001", "session_id": "abc123", "hash": "sha256:...", "prev_hash": "sha256:..."}
```

### Dashboard Integration (`insight/flow.log`)
```json
{"timestamp": "2025-01-15T10:30:00Z", "module": "education", "event": "rule_executed", "status": "success"}
```

## 🔒 Security Protocols

### RSA Key Management
- Public key: `security/public.pem`
- Private key: `security/private.pem`
- Key rotation: Manual process documented in `security/key_rotation.md`

### JWT Token Requirements
- Algorithm: RS256
- Expiration: 1 hour
- Required claims: `sub`, `exp`, `iat`

### Anti-Replay Protection
- Nonce cache: `security/nonce_cache.json`
- Cache size: 10,000 entries
- TTL: 24 hours

## 🔒 LOG FORMAT VERSION CONTROL

**LOG SCHEMA VERSION: LS-V1-20250115**

**FROZEN LOG FORMATS:**

1. **core_sync.log FORMAT v1.0**
   ```
   TIMESTAMP - {"module": "...", "session_id": "...", "timestamp": "...", "data": {...}}
   ```
   ANY deviation requires contract update.

2. **metrics.jsonl FORMAT v1.0**
   ```
   {"timestamp": "...", "endpoint": "...", "module": "...", "status": "...", "latency_ms": ..., "pending_queue": ...}
   ```
   Field addition/removal requires stakeholder approval.

3. **FROZEN FIELD NAMES:**
   - `timestamp` - ISO 8601 UTC format
   - `module` - String identifier
   - `status` - "success"|"error"|"rejected"
   - `latency_ms` - Integer milliseconds
   - NO field renaming permitted

## 🚫 Forbidden Execution Paths

**DO NOT RUN UNDER ANY CIRCUMSTANCES:**
- `demo_script.py` - Development demo only
- `load_test.py` - Performance testing only
- `test_*.py` files - Unit testing only
- `localhost_test.py` - Local development only
- `final_verification.py` - Pre-release verification only
- Any file in `automation/plugins/` directly
- Any file in `tests/` directory
- Any file listed in `NON_CANONICAL_RUNNERS.md`

## 📞 Production Support

**Critical Issues Only:**
- Backend Lead: [Team member responsible for core_bucket_bridge.py]
- QA Lead: Vinayak
- Integration Lead: Anmol

---
**🔒 THIS DOCUMENT IS FROZEN FOR PRODUCTION - ANY CHANGES REQUIRE FORMAL APPROVAL**
**Version: CBV5-INT-20250115-001**
**SHA256 Hash: 2E7B9A3D4F6C8E1A5B9D3F7C2E8A6B1D4F9C7E3A5B8D1F6C4E9A2B7D8E3F6C1A**
**Contract Identifier: CB-V5-20250115-001**