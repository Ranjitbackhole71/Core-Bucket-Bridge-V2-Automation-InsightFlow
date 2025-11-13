# Core–Bucket Data Bridge

A complete backend + dashboard system that synchronizes module data from Core (local system) to Bucket (central API) with InsightFlow monitoring and native Python automation.

## 🌟 Features

- **FastAPI Backend**: RESTful API for data synchronization
- **Streamlit Dashboard**: Real-time monitoring of sync activities
- **Native Python Automation**: Scheduled workflows for data synchronization (replaces N8N)
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
```

## 📁 Project Structure

```
├─ core_bucket_bridge.py    # FastAPI backend application
├─ mock_modules.py          # Mock modules for testing (education, finance, creative, robotics)
├─ requirements.txt         # Python dependencies
├─ README.md                # This file
├─ handover_core_bridge.md  # Detailed documentation and setup guide
├─ logs/
│   ├─ core_sync.log        # Core synchronization logs
│   └─ metrics.jsonl        # Health and performance metrics
├─ insight/
│   ├─ flow.log             # InsightFlow monitoring logs
│   └─ dashboard/
│       └─ app.py           # Streamlit dashboard application
├─ automation/
│   ├─ runner.py            # Native Python automation runner
│   ├─ config.json          # Automation job configuration
│   └─ reports/             # Automation reports and logs
└─ .gitignore               # Git ignore file
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Backend Server

```bash
python core_bucket_bridge.py
```

The server will start on `http://localhost:8000` with endpoints:
- `POST /core/update` - Receives data from Core modules
- `GET /bucket/status` - Returns current sync summary
- `GET /core/health` - Returns health and performance metrics

### 3. Start the InsightFlow Dashboard

```bash
streamlit run insight/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

### 4. Run Mock Modules (for testing)

```bash
python mock_modules.py
```

This will send sample data every 30 seconds to test the system.

### 5. Run Automation Runner

```bash
# Run once
python automation/runner.py --once

# Run in watch mode (default 120-minute intervals)
python automation/runner.py --watch

# Run in watch mode with custom interval (in minutes)
python automation/runner.py --watch --interval 30
```

## 🛠 API Endpoints

### POST /core/update

Receives data from Core modules.

**Request Body**:
```json
{
  "module": "string",
  "data": {},
  "session_id": "string (optional)"
}
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

### GET /bucket/status

Returns current sync summary.

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

## ⚙️ Native Python Automation

The project includes a native Python automation runner that replaces N8N:

1. Runs jobs based on configured triggers (startup, interval)
2. Sends test data to the Core endpoint
3. Retrieves Bucket status
4. Saves results to `automation/reports/`
5. Implements retry logic (3 attempts with exponential backoff)

Configuration is in `automation/config.json` with support for:
- Startup triggers
- Interval-based triggers
- Multiple module data sending
- Status checking actions

## 🧪 Testing

Run the test suite:
```bash
pytest test_core_bucket_api.py -v
```

## 📖 Documentation

See [handover_core_bridge.md](handover_core_bridge.md) for detailed documentation including:
- Complete setup instructions
- API usage examples
- Testing procedures
- Troubleshooting guide
- Demo recording guide

## 🎥 Demo

For a quick 2-3 minute demo:
1. Run `python core_bucket_bridge.py`
2. Run `streamlit run insight/dashboard/app.py`
3. Run `python mock_modules.py` in another terminal
4. Watch the dashboard update in real-time

## 🔧 Modular Design

The system is designed to be modular:
- Native Python automation can be extended or replaced
- New Core modules can be easily added
- API endpoints can be extended following the existing pattern

## 📞 Support

For issues or questions about the Core–Bucket Data Bridge system, please refer to the documentation or contact the development team.