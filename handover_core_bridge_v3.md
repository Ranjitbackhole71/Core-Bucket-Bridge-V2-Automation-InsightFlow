# Core–Bucket Bridge V3 - Security Hardening & Automation Engine Phase II

## 📋 Project Overview

This document provides complete documentation for the Core–Bucket Bridge V3 system with Security Hardening and Automation Engine Phase II. This is a complete working project with enhanced security features, plugin-based automation, and full demo readiness.

## 📁 Project Folder Structure

```
├─ core_bucket_bridge.py     (Main FastAPI application with security features)
├─ mock_modules.py           (Test data generator with 4 modules)
├─ requirements.txt          (Dependencies)
├─ README.md                 (Project documentation)
├─ handover_core_bridge_v3.md (This document)
├─ test_security.py          (Security feature verification script)
├─ test_plugins.py           (Plugin verification script)
├─ generate_keys.py          (RSA keypair generation script)
├─ logs/
│   ├─ core_sync.log         (Core synchronization logs)
│   ├─ metrics.jsonl         (Health and performance metrics)
│   ├─ security_rejects.log  (Security rejection logs)
│   └─ provenance_chain.jsonl (Provenance hash chain)
├─ insight/
│   ├─ flow.log              (InsightFlow monitoring logs)
│   └─ dashboard/
│       └─ app.py            (Streamlit dashboard)
├─ automation/
│   ├─ runner.py             (Native Python automation runner with plugin support)
│   ├─ config.json           (Automation job configuration)
│   └─ reports/
│       ├─ daily_log.txt     (Daily automation updates)
│       ├─ engine.log        (Plugin execution logs)
│       └─ run_*.jsonl       (Automation run reports)
│   └─ plugins/
│       ├─ heartbeat.py      (Heartbeat plugin)
│       ├─ sync_test.py      (Sync test plugin)
│       └─ latency_probe.py  (Latency probe plugin)
├─ security/
│   ├─ private.pem           (RSA private key)
│   └─ public.pem            (RSA public key)
│   └─ nonce_cache.json      (Anti-replay nonce cache)
```

## 🔐 Security Layer Implementation

### Signature Verification

All requests to POST /core/update and GET /bucket/status require signature verification:

1. **Payload Structure**:
```json
{
  "payload": {...},           // Actual data
  "signature": "base64-string" // RSA signature
}
```

2. **Verification Process**:
- Load public key from `security/public.pem`
- Verify signature using RSA-PKCS1v15 with SHA256
- Reject invalid signatures with `{ "status": "rejected", "reason": "invalid_signature" }`

### JWT Authorization

All endpoints require valid JWT tokens with the following validation:

1. **Token Structure**:
```
Authorization: Bearer <jwt-token>
```

2. **Validation Checks**:
- Token validity (signature verification)
- Issuer verification
- Expiry verification
- Role verification (module / automation / admin)

### Anti-Replay Protection

1. **Nonce Tracking**:
- Each request contains a unique "nonce" field
- Nonces stored in `security/nonce_cache.json` (max 5000 entries)
- Duplicate nonces rejected as replay attacks
- Replay attempts logged to `logs/security_rejects.log`

### Provenance Hash-Chain

1. **Hash Chain Implementation**:
- Each event contributes to a SHA256 hash chain
- Formula: `hash = SHA256(previous_hash + payload + timestamp)`
- Chain stored in `logs/provenance_chain.jsonl`
- Continuity verified before accepting events

## ⚙️ Plugin-Based Automation Engine

### Plugin Architecture

1. **Plugin Directory**: `/automation/plugins/`
2. **Plugin Interface**: Each plugin implements a `run()` function
3. **Dynamic Loading**: Plugins loaded at runtime using `importlib`
4. **Execution Logging**: Results logged to `automation/reports/engine.log`

### Available Plugins

1. **heartbeat.py**: Sends periodic heartbeat events
2. **sync_test.py**: Tests synchronization connectivity
3. **latency_probe.py**: Measures internal processing latency

### Plugin Configuration

Plugins are configured in `automation/config.json` as jobs with "run_plugin" actions:

```json
{
  "name": "heartbeat_job",
  "trigger": {
    "type": "intervalMinutes",
    "value": 5
  },
  "actions": [
    {
      "type": "run_plugin",
      "plugin_name": "heartbeat"
    }
  ]
}
```

## 🚀 Setup Instructions

### Environment Setup

1. **Python Installation**: Ensure Python 3.8+ is installed
2. **Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### RSA Key Generation

Generate RSA keypair for signature verification:
```bash
python generate_keys.py
```

This creates:
- `security/private.pem` (keep secure)
- `security/public.pem` (for verification)

### How to Run Backend Server

```bash
python core_bucket_bridge.py
```

The server will start on `http://localhost:8000` with secured endpoints:
- `POST /core/update` - Receives signed data from Core modules
- `GET /bucket/status` - Returns current sync summary (requires authorization)
- `GET /core/health` - Returns health and performance metrics

### How to Run InsightFlow Dashboard

```bash
streamlit run insight/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

### How to Run Automation Runner

```bash
# Run once
python automation/runner.py --once

# Run in watch mode (default 120-minute intervals)
python automation/runner.py --watch

# Run in watch mode with custom interval (in minutes)
python automation/runner.py --watch --interval 30
```

## 🔑 Security Implementation Details

### How to Generate RSA Keypairs

Using the provided script:
```bash
python generate_keys.py
```

Manual generation with OpenSSL:
```bash
# Generate private key
openssl genrsa -out security/private.pem 2048

# Extract public key
openssl rsa -in security/private.pem -pubout -out security/public.pem
```

### How JWT Works

1. **Token Creation**:
```python
import jwt
from datetime import datetime, timedelta

payload = {
    "iss": "core-bucket-bridge",
    "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
    "roles": ["module"]
}
token = jwt.encode(payload, "secret", algorithm="HS256")
```

2. **Token Usage**:
```
Authorization: Bearer <generated-jwt-token>
```

### Replay Protection Workflow

1. Client includes unique "nonce" in each request
2. Server checks `security/nonce_cache.json` for existing nonce
3. If found, reject as replay attack
4. If not found, add to cache and process request
5. Maintain only last 5000 nonces

### Provenance Hash-Chain Logic

1. **Hash Calculation**:
```
new_hash = SHA256(previous_hash + json_payload + timestamp)
```

2. **Chain Storage**:
- Each entry stored as JSON line in `logs/provenance_chain.jsonl`
- Includes hash, previous_hash, payload, and timestamp

3. **Continuity Verification**:
- Verify previous_hash matches last entry's hash
- Recalculate hash to ensure data integrity

## 🧪 Testing Procedures

### Security Feature Tests

Run the security verification script:
```bash
python test_security.py
```

Tests include:
- Valid signature + token request (accepted)
- Invalid signature (rejected)
- Invalid token (rejected)
- Replay attack (rejected)

### Plugin Tests

Run the plugin verification script:
```bash
python test_plugins.py
```

Tests include:
- Heartbeat plugin execution
- Sync test plugin execution
- Latency probe plugin execution

### Manual Testing

1. **Verify Signature Verification**:
   ```bash
   # Valid request (will be accepted)
   curl -X POST http://localhost:8000/core/update \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <valid-jwt-token>" \
        -d '{"payload": {"module": "test", "data": {"message": "test"}}, "signature": "<valid-signature>"}'
   ```

2. **Check Security Logs**:
   ```bash
   cat logs/security_rejects.log
   ```

3. **Verify Provenance Chain**:
   ```bash
   cat logs/provenance_chain.jsonl
   ```

## 📹 Demo Script (60-90 seconds)

### 1. Valid Request Demonstration
```bash
# Show a valid signed request being accepted
python test_security.py
# Select "Valid Request" test
```

### 2. Security Rejection Demonstration
```bash
# Show invalid signature being rejected
python test_security.py
# Select "Invalid Signature" test
```

### 3. Replay Attack Prevention
```bash
# Show replay attack being rejected
python test_security.py
# Select "Replay Attack" test
```

### 4. Provenance Chain Growth
```bash
# Show provenance chain entries
tail -f logs/provenance_chain.jsonl
```

### 5. Plugin Execution
```bash
# Run automation runner once to execute plugins
python automation/runner.py --once

# Show plugin results in engine log
tail automation/reports/engine.log
```

### 6. Heartbeats in Dashboard/Logs
```bash
# Show heartbeat entries in logs
grep "heartbeat" automation/reports/engine.log
```

## 📋 Expected Output & Verification Checklist

✅ **Security Hardening**:
- Signature verification working
- JWT auth rejecting invalid tokens
- Anti-replay protection preventing duplicates
- Provenance chain maintaining integrity

✅ **Plugin Engine**:
- Plugins loading and executing correctly
- Results logged to engine.log
- Heartbeats sent periodically

✅ **Documentation**:
- Security layer explanation
- RSA keypair generation instructions
- JWT implementation details
- Plugin usage guide
- Replay protection workflow
- Provenance hash-chain logic

✅ **Demo Script**:
- Valid requests accepted
- Invalid requests rejected
- Replay attacks blocked
- Provenance chain growing
- Plugins executing
- Heartbeats visible

✅ **Backend Integration**:
- All new logs created and updated
- Dashboard showing security events
- All tests passing
- Full system functionality

## 🚀 Additional Features

- **Enhanced Security**: Public-key signatures, JWT auth, anti-replay protection
- **Provenance Tracking**: Immutable hash chain for audit trail
- **Plugin Architecture**: Extensible automation through dynamic plugins
- **Comprehensive Logging**: Detailed security and automation logs
- **Modular Design**: Easy to extend and maintain
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux
- **Production Ready**: Secure, scalable, and robust implementation

## 📞 Support

For issues or questions about the Core–Bucket Bridge V3 system, please refer to this documentation or contact the development team.