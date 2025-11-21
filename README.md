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

Returns health metrics for the Core-Bucket bridge.

**Response**:
```json
{
  "status": "ok",
  "uptime_s": 1234.56,
  "last_sync_ts": "2025-10-16T10:20:00Z",
  "pending_queue": 0,
  "error_count_24h": 0,
  "avg_latency_ms_24h": 45.5
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

### Provenance Hash-Chain
- SHA256-based immutable audit trail
- Stored in `logs/provenance_chain.jsonl`
- Continuity verification for all events

## 🧪 Testing

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