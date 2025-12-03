# Core–Bucket Bridge V4 - Production Ready System

## 📋 Project Overview

This document provides complete documentation for the Core–Bucket Bridge V4 system, a production-ready implementation with enhanced security features, multi-node automation engine, and comprehensive monitoring capabilities.

## 📁 Project Folder Structure

```
├─ core_bucket_bridge.py     (Main FastAPI application with security features)
├─ mock_modules.py           (Test data generator with 4 modules)
├─ requirements.txt          (Dependencies)
├─ README.md                 (Project documentation)
├─ handover_core_bridge_v4.md (This document)
├─ test_security.py          (Security feature verification script)
├─ test_plugins.py          (Plugin verification script)
├─ test_heartbeat.py         (Heartbeat endpoint verification script)
├─ test_health_security.py   (Health endpoint security metrics verification script)
├─ generate_keys.py         (RSA keypair generation script)
├─ logs/
│   ├─ core_sync.log         (Core synchronization logs)
│   ├─ metrics.jsonl         (Health and performance metrics)
│   ├─ security_rejects.log  (Security rejection logs)
│   ├─ heartbeat.log         (Heartbeat event logs)
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

All requests to POST /core/update, POST /core/heartbeat require signature verification:

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

### JWT Authorization with RBAC

All endpoints require valid JWT tokens with role-based access control:

1. **Token Structure**:
```
Authorization: Bearer <jwt-token>
```

2. **Role-Based Access Control**:
- **module**: Can send heartbeat and data updates
- **automation**: Can control automation tasks and send heartbeat
- **admin**: Can access all endpoints including health & security dashboard

3. **Validation Checks**:
- Token validity (signature verification)
- Issuer verification
- Expiry verification
- Role verification based on endpoint requirements

### Anti-Replay Protection

1. **Nonce Tracking**:
- Each request contains a unique "nonce" field
- Nonces stored in `security/nonce_cache.json` (max 5000 entries)
- Duplicate nonces rejected as replay attacks
- Replay attempts logged to `logs/security_rejects.log`

### Replay Protection Workflow

```
                    ┌─────────────────────┐
                    │   Client/System     │
                    └─────────┬───────────┘
                              │
                    1. Generate Nonce
                              │
                    ┌─────────▼───────────┐
                    │   Nonce Generator   │
                    │  (Cryptographically │
                    │   Secure Random)    │
                    └─────────┬───────────┘
                              │
                    2. Create Payload
                              │
                    ┌─────────▼───────────┐
                    │   Payload Creator   │
                    │  (Data + Nonce)     │
                    └─────────┬───────────┘
                              │
                    3. Sign Payload
                              │
                    ┌─────────▼───────────┐
                    │   Signature Engine  │
                    │ (Private Key +      │
                    │  RSA-PKCS1v15)      │
                    └─────────┬───────────┘
                              │
                    4. Send Request
                              │
         ┌──────────────────▼──────────────────┐
         │        Core-Bucket Bridge API        │
         │              (Server)                │
         └─────────────────────────────────────┘
                              │
                    5. Validate Signature
                              │
                    6. Check Nonce Uniqueness ◄───┐
                              │                   │
                    7. Is Nonce Duplicate? ──► Yes ──► 8. Reject Request
                              │                   │         (Replay Attack)
                             No                  │         Log to security_rejects.log
                              │                   │
                    8. Process Request           │
                              │                   │
                    9. Store Nonce ──────────────┘
                              │
                   10. Return Response
                              │
                    ┌─────────▼───────────┐
                    │   Client/System     │
                    └─────────────────────┘

Key Components:
- Nonce Cache: security/nonce_cache.json (max 5000 entries)
- Security Logs: logs/security_rejects.log
- Signature Verification: RSA-PKCS1v15 with SHA256
- JWT Authentication: Role-based access control
```

### Provenance Hash-Chain

1. **Hash Chain Implementation**:
- Each event contributes to a SHA256 hash chain
- Formula: `hash = SHA256(previous_hash + payload + timestamp)`
- Chain stored in `logs/provenance_chain.jsonl`
- Continuity verified before accepting events

## ⚙️ Multi-Node Automation Engine

### Multi-Node Architecture

The automation engine now supports multi-node execution:

1. **Node Configuration**:
```bash
python automation/runner.py --nodes 3
```

2. **Node Identification**:
- Each node gets a unique ID (node-001, node-002, node-003)
- Node ID is included in all payloads
- Separate log directories per node

3. **Error Isolation**:
- Plugin failures don't crash other plugins or nodes
- Errors logged to `automation/reports/plugin_errors.log`
- Individual node failures don't affect others

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
- `POST /core/update` - Receives signed data from Core modules (module role required)
- `POST /core/heartbeat` - Receives signed heartbeat from modules/plugins (module role required)
- `GET /bucket/status` - Returns current sync summary (module role required)
- `GET /core/health` - Returns health and performance metrics (no role required)

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

# Run multi-node mode
python automation/runner.py --nodes 3
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
    "roles": ["module"]  # or ["automation"] or ["admin"]
}
token = jwt.encode(payload, "secret", algorithm="HS256")
```

2. **Token Usage**:
```
Authorization: Bearer <generated-jwt-token>
```

### Replay Protection Workflow

The anti-replay protection system prevents attackers from reusing valid signatures to perform replay attacks. Here's how it works:

```
Client                    Server
  │                         │
  │───1. Generate Nonce────▶│
  │                         │
  │◀───2. Return Nonce──────│
  │                         │
  │                         │
  │───3. Create Payload────▶│
  │                         │
  │───4. Sign Payload+Nonce▶│
  │                         │
  │                         │
  │───5. Send Request──────▶│
  │                         │
  │                         │ 6. Validate Signature
  │                         │ 7. Check Nonce Uniqueness
  │                         │ 8. Process Request
  │                         │ 9. Store Nonce
  │◀──10. Return Response───│
```

Steps:
1. **Nonce Generation**: Client generates a cryptographically secure unique nonce for each request
2. **Payload Signing**: Client signs the payload combined with the nonce using their private key
3. **Backend Validation**: Server verifies the signature using the public key
4. **Nonce Checking**: Server checks if the nonce exists in the nonce cache
5. **Replay Detection**: If nonce exists, reject as replay attack; if not, accept request
6. **Nonce Storage**: Valid nonce is stored in cache for future replay detection
7. **Nonce Expiry**: System maintains only the last 5000 nonces to prevent cache overflow

This workflow ensures that even if an attacker intercepts a valid signed request, they cannot replay it because the nonce will already be in the server's cache.

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

### Heartbeat Endpoint Tests

Run the heartbeat verification script:
```bash
python test_heartbeat.py
```

Tests include:
- Valid heartbeat request (accepted)
- Invalid signature (rejected)
- Replay attack (rejected)
- Role verification

### Health Security Metrics Tests

Run the health security metrics verification script:
```bash
python test_health_security.py
```

Tests include:
- Health endpoint returns security metrics
- All required security fields present
- Metrics update in real time

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
   curl -X POST http://localhost:8000/core/heartbeat \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer <valid-jwt-token>" \
        -d '{"payload": {"module": "test", "timestamp": "2025-11-28T10:00:00Z", "status": "alive"}, "signature": "<valid-signature>"}'
   ```

2. **Check Security Logs**:
   ```bash
   cat logs/security_rejects.log
   ```

3. **Verify Provenance Chain**:
   ```bash
   cat logs/provenance_chain.jsonl
   ```

4. **Check Health Security Metrics**:
   ```bash
   curl http://localhost:8000/core/health
   ```

## 📹 Demo Script (60-90 seconds)

### 1. Valid Request Demonstration
```bash
# Show a valid signed heartbeat being accepted
python test_heartbeat.py
# Select "Valid Heartbeat" test
```

### 2. Security Rejection Demonstration
```bash
# Show invalid signature being rejected
python test_heartbeat.py
# Select "Invalid Signature" test
```

### 3. Replay Attack Prevention
```bash
# Show replay attack being rejected
python test_heartbeat.py
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
grep "heartbeat" logs/core_sync.log
```

### 7. Health Security Metrics
```bash
# Show health endpoint with security metrics
python test_health_security.py
```

## 📋 Expected Output & Verification Checklist

✅ **Security Hardening**:
- Signature verification working
- JWT auth rejecting invalid tokens
- RBAC enforcing role separation
- Anti-replay protection preventing duplicates
- Provenance chain maintaining integrity

✅ **Heartbeat API**:
- POST /core/heartbeat endpoint exists and is secure
- Accepts valid signed heartbeats
- Rejects invalid signatures
- Prevents replay attacks
- Enforces role-based access

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
- Replay workflow diagram and explanation

✅ **Demo Script**:
- Valid requests accepted
- Invalid requests rejected
- Replay attacks blocked
- Provenance chain growing
- Plugins executing
- Heartbeats visible
- Health endpoint shows security metrics

✅ **Backend Integration**:
- All new logs created and updated
- Dashboard showing security events
- All tests passing
- Full system functionality

## 🚀 Additional Features

- **Enhanced Security**: Public-key signatures, JWT auth, anti-replay protection
- **Provenance Tracking**: Immutable hash chain for audit trail
- **Multi-Node Plugin Architecture**: Extensible automation through dynamic plugins with node isolation
- **Role-Based Access Control**: Fine-grained endpoint access control
- **Real-time Security Metrics**: Live security analytics in health endpoint
- **Comprehensive Logging**: Detailed security and automation logs
- **Modular Design**: Easy to extend and maintain
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux
- **Production Ready**: Secure, scalable, and robust implementation

## 📞 Support

For issues or questions about the Core–Bucket Bridge V4 system, please refer to this documentation or contact the development team.