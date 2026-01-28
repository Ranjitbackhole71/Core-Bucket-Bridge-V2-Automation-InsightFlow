# Core–Bucket Data Bridge V3 - Security Hardening & Automation Engine

A complete backend + dashboard system that synchronizes module data from Core (local system) to Bucket (central API) with InsightFlow monitoring, native Python automation, and enterprise-grade security features.

## 🌟 Features

- **FastAPI Backend**: RESTful API for data synchronization
- **Streamlit Dashboard**: Real-time monitoring of sync activities
- **Native Python Automation**: Scheduled workflows for data synchronization (replaces N8N)
- **Enterprise Security**: RSA signature verification, JWT auth, anti-replay protection
- **Provenance Tracking**: Immutable hash chain for audit trail
- **Plugin Architecture**: Extensible automation through dynamic plugins
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Full Test Coverage**: Pytest suite for API validation
- **Modular Design**: Easily extensible and replaceable components
- **Health Monitoring**: Real-time health metrics and status reporting

## 🏗️ System Architecture

```
┌─────────────┐    ┌────────────────────┐    ┌──────────────┐
│   Core      │───▶│  Core-Bucket API   │───▶│    Bucket    │
│  Modules    │    │   (FastAPI)        │    │   (Central)  │
└─────────────┘    └────────────────────┘    └──────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │ InsightFlow Logger │
                   └────────────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │   Streamlit Dash   │
                   │   (Monitoring)     │
                   └────────────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │  Python Automation │
                   │     Runner         │
                   └────────────────────┘
                            │
                            ▼
                   ┌────────────────────┐
                   │   Security Layer   │
                   │(Signatures, JWT,   │
                   │ Anti-Replay)       │
                   └────────────────────┘
```

## 📁 Project Structure

```
├─ core_bucket_bridge.py    # FastAPI backend application (V3 with security)
├─ mock_modules.py          # Mock modules for testing (education, finance, creative, robotics)
├─ requirements.txt         # Python dependencies
├─ README.md                # This file
├─ handover_core_bridge_v3.md  # V3 Detailed documentation and setup guide
├─ test_security.py         # Security feature verification
├─ test_plugins.py          # Plugin verification
├─ generate_keys.py         # RSA keypair generation
├─ logs/
│   ├─ core_sync.log        # Core synchronization logs
│   ├─ metrics.jsonl        # Health and performance metrics
│   ├─ security_rejects.log # Security rejection logs
│   └─ provenance_chain.jsonl # Provenance hash chain
├─ insight/
│   ├─ flow.log             # InsightFlow monitoring logs
│   └─ dashboard/
│       └─ app.py           # Streamlit dashboard application
├─ automation/
│   ├─ runner.py            # Native Python automation runner (V3 with plugins)
│   ├─ config.json          # Automation job configuration
│   └─ reports/             # Automation reports and logs
│   └─ plugins/             # Plugin directory
│       ├─ heartbeat.py     # Heartbeat plugin
│       ├─ sync_test.py     # Sync test plugin
│       └─ latency_probe.py # Latency probe plugin
├─ security/
│   ├─ private.pem          # RSA private key
│   ├─ public.pem           # RSA public key
│   └─ nonce_cache.json     # Anti-replay nonce cache
└─ .gitignore               # Git ignore file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate RSA Keys

```bash
python generate_keys.py
```

### 3. Start the Backend Server

```bash
python core_bucket_bridge.py
```

The server will start on `http://localhost:8000` with secured endpoints:
- `POST /core/update` - Receives signed data from Core modules
- `POST /core/heartbeat` - Receives signed heartbeat from modules/plugins
- `GET /bucket/status` - Returns current sync summary (requires JWT auth)
- `GET /core/health` - Returns health and performance metrics

### 4. Start the InsightFlow Dashboard

```bash
streamlit run insight/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

### 5. Run Mock Modules (for testing)

```bash
python mock_modules.py
```

This will send sample data every 30 seconds to test the system.

### 6. Run Automation Runner

```bash
# Run once
python automation/runner.py --once

# Run in watch mode (default 120-minute intervals)
python automation/runner.py --watch

# Run in watch mode with custom interval (in minutes)
python automation/runner.py --watch --interval 30
```

## 🔐 Security Endpoints

### POST /core/update (Secured)

Receives signed data from Core modules with JWT authentication.

**Request Body**:
```json
{
  "payload": {
    "module": "string",
    "data": {},
    "session_id": "string (optional)"
  },
  "signature": "base64-encoded-RSA-signature",
  "nonce": "unique-string-for-anti-replay"
}
```

**Headers**:
```
Authorization: Bearer <jwt-token>
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-10-16T10:20:00Z",
  "session_id": "uuid-string",
  "message": "Data received and logged for module education"
}
```

### POST /core/heartbeat (Secured)

Receives signed heartbeat from modules/plugins with JWT authentication.

**Request Body**:
```json
{
  "payload": {
    "module": "string",
    "timestamp": "ISO8601-timestamp",
    "status": "alive|dead|warning",
    "metrics": {}
  },
  "signature": "base64-encoded-RSA-signature",
  "nonce": "unique-string-for-anti-replay"
}
```

**Headers**:
```
Authorization: Bearer <jwt-token>
```

**Response**:
```json
{
  "status": "success",
  "timestamp": "2025-10-16T10:20:00Z",
  "session_id": "heartbeat-uuid-string",
  "message": "Heartbeat received and logged for module education"
}
```

### GET /bucket/status (Secured)

Returns current sync summary with JWT authentication.

**Headers**:
```
Authorization: Bearer <jwt-token>
```

**Response**:
```json
{
  "last_sync_time": "2025-10-16T10:20:00Z",
  "total_sync_count": 5,
  "module_sync_counts": {
    "education": 2,
    "finance": 2,
    "creative": 1
  }
}
```

### GET /core/health

Returns health metrics for the Core-Bucket bridge including security metrics.

**Response**:
```json
{
  "status": "ok",
  "uptime_s": 1234.56,
  "last_sync_ts": "2025-10-16T10:20:00Z",
  "pending_queue": 0,
  "error_count_24h": 0,
  "avg_latency_ms_24h": 45.5,
  "security": {
    "rejected_signatures": 0,
    "replay_attempts": 0,
    "last_valid_signature_timestamps": {
      "education": "2025-10-16T10:20:00Z",
      "finance": "2025-10-16T10:15:00Z"
    }
  }
}
```

**Curl example**:
```bash
curl http://localhost:8000/core/health
```

## 📊 Dashboard Features

The InsightFlow dashboard provides real-time monitoring of the synchronization process:

- **Sync Success % (24h)**: Overall success rate of sync operations
- **Avg Latency (24h)**: Average processing time for sync operations
- **Error Count (24h)**: Number of errors in the last 24 hours
- **Queue Depth**: Current number of pending sync operations
- **Auto-refresh**: Updates automatically every 30 seconds
- **Color-coded status**: 🟢 OK, 🔴 Error
- **Security Events**: Displays security rejection logs

## ⚙️ Native Python Automation with Plugins

The project includes a native Python automation runner with plugin support:

1. Runs jobs based on configured triggers (startup, interval)
2. Sends signed test data to the Core endpoint
3. Retrieves Bucket status with JWT auth
4. Executes dynamic plugins (heartbeat, sync_test, latency_probe)
5. Saves results to `automation/reports/`
6. Implements retry logic (3 attempts with exponential backoff)

Configuration is in `automation/config.json` with support for:
- Startup triggers
- Interval-based triggers
- Multiple module data sending
- Status checking actions
- Plugin execution

## 🔒 Security Features

### Signature Verification
- RSA-PKCS1v15 with SHA256 signatures
- Public key verification from `security/public.pem`
- Automatic rejection of invalid signatures

### JWT Authentication
- HS256 token verification
- Issuer and expiry validation
- Role-based access control (module/automation/admin)

### Anti-Replay Protection
- Nonce tracking in `security/nonce_cache.json`
- Automatic rejection of replay attacks
- Maintains last 5000 nonces

### Replay Protection Workflow

The anti-replay protection system prevents attackers from reusing valid signatures to perform replay attacks. Here's how it works:

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
- SHA256-based immutable audit trail
- Stored in `logs/provenance_chain.jsonl`
- Continuity verification for all events

## Replay Protection Workflow

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

## 🧪 Testing

### Automated Localhost Testing

For a comprehensive test of all system functionality, use the provided localhost test scripts:

**Windows:**
```cmd
run_localhost_test.bat
```

**macOS/Linux:**
```bash
chmod +x run_localhost_test.sh
./run_localhost_test.sh
```

This will automatically:
- Verify system requirements
- Install missing dependencies
- Generate RSA keys if needed
- Start all services (FastAPI, Streamlit)
- Run automation tests
- Verify logs and reports
- Provide access information

See [LOCALHOST_TEST_README.md](LOCALHOST_TEST_README.md) for detailed instructions.

### Security Tests
```bash
python test_security.py
```

### Plugin Tests
```bash
python test_plugins.py
```

### API Tests
```bash
pytest test_core_bucket_api.py -v
```

## 📖 Documentation

See [handover_core_bridge_v3.md](handover_core_bridge_v3.md) for detailed V3 documentation including:
- Security implementation details
- RSA keypair generation
- JWT usage examples
- Plugin development guide
- Replay protection workflow
- Provenance hash-chain logic

## 🎥 Demo

For a quick 60-90 second demo:
1. Run `python core_bucket_bridge.py`
2. Run `python test_security.py` to show security features
3. Run `python automation/runner.py --once` to execute plugins
4. Show logs in `logs/provenance_chain.jsonl` and `logs/security_rejects.log`

## 🔧 Modular Design

The system is designed to be modular:
- Native Python automation with plugin architecture
- New Core modules can be easily added
- Security features can be extended or modified
- API endpoints can be extended following the existing pattern

## 📞 Support

For issues or questions about the Core–Bucket Data Bridge V3 system, please refer to the documentation or contact the development team.