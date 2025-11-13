# Core–Bucket Bridge V2 - Automation & Health Monitoring Handover

## 📋 Project Overview

This document provides complete documentation for the Core–Bucket Bridge V2 system with Automation Engine Phase 1 and Health Monitoring Upgrade. This is a complete working project with enhanced monitoring, native Python automation, and full demo readiness.

## 📁 Project Folder Structure

```
├─ core_bucket_bridge.py     (FastAPI backend with health endpoint)
├─ mock_modules.py           (Test data generator with 4 modules)
├─ requirements.txt          (Dependencies)
├─ README.md                 (Project documentation)
├─ handover_bridge_v2.md     (This document)
├─ test_health_endpoint.py   (Endpoint verification script)
├─ logs/
│   ├─ core_sync.log         (Core synchronization logs)
│   └─ metrics.jsonl         (Health and performance metrics)
├─ insight/
│   ├─ flow.log              (InsightFlow monitoring logs)
│   └─ dashboard/
│       └─ app.py            (Streamlit dashboard)
├─ automation/
│   ├─ runner.py             (Native Python automation runner)
│   ├─ config.json           (Automation job configuration)
│   └─ reports/
│       ├─ daily_log.txt     (Daily automation updates)
│       └─ run_*.jsonl       (Automation run reports)
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

### How to Run Backend Server

```bash
python core_bucket_bridge.py
```

The server will start on `http://localhost:8000` with the following endpoints:
- `POST /core/update` - Receives data from Core modules
- `GET /bucket/status` - Returns current sync summary
- `GET /core/health` - Returns health and performance metrics

### How to Run InsightFlow Dashboard

```bash
streamlit run insight/dashboard/app.py
```

The dashboard will be available at `http://localhost:8501`

### How to Run Native Automation Runner

```bash
# Run once
python automation/runner.py --once

# Run in watch mode (default 120-minute intervals)
python automation/runner.py --watch

# Run in watch mode with custom interval (in minutes)
python automation/runner.py --watch --interval 30
```

## ⚙️ Runner Configuration Schema

The automation runner uses a JSON configuration file (`automation/config.json`) with the following schema:

```json
{
  "jobs": [
    {
      "name": "job_name",
      "trigger": {
        "type": "onStartup|intervalMinutes",
        "value": 30  // Required for intervalMinutes
      },
      "actions": [
        {
          "type": "send_core_update",
          "data": {
            "module": "module_name",
            "data": { /* module-specific data */ }
          }
        },
        {
          "type": "get_bucket_status"
        }
      ]
    }
  ]
}
```

## 🛠 API Endpoint Documentation

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
    "creative": 1,
    "robotics": 1
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

## 🧪 Testing Procedures

### Automated Endpoint Tests

Run the verification script:
```bash
python test_health_endpoint.py
```

### Manual Testing

1. **Verify Health Endpoint**:
   ```bash
   curl http://localhost:8000/core/health
   ```

2. **Send Test Data**:
   ```bash
   curl -X POST http://localhost:8000/core/update \
        -H "Content-Type: application/json" \
        -d '{"module": "test", "data": {"message": "Hello World"}}'
   ```

3. **Check Bucket Status**:
   ```bash
   curl http://localhost:8000/bucket/status
   ```

## 🔧 Retry Logic Implementation

The automation runner implements retry logic with the following characteristics:
- Up to 3 attempts per failed request
- Exponential backoff (1s, 2s, 4s)
- Works for both POST /core/update and GET /bucket/status endpoints

## 📊 Dashboard Features

The InsightFlow dashboard provides real-time monitoring with:

- **Sync Success % (24h)**: Overall success rate of sync operations
- **Avg Latency (24h)**: Average processing time for sync operations
- **Error Count (24h)**: Number of errors in the last 24 hours
- **Queue Depth**: Current number of pending sync operations
- **Auto-refresh**: Updates automatically every 30 seconds
- **Color-coded status**: 🟢 OK, 🔴 Error

## 📹 Demo Recording Guide

Follow these steps to record a complete demo:

### 1. Start FastAPI Backend
```bash
python core_bucket_bridge.py
```
Show the terminal output confirming the server is running on port 8000.

### 2. Show Mock Modules Sending Data
```bash
python mock_modules.py
```
Show the terminal output with successful data transmission messages.

### 3. Open InsightFlow Dashboard
```bash
streamlit run insight/dashboard/app.py
```
Demonstrate:
- Real-time updates in the sync events table
- Average latency calculations
- Last sync time per module
- Auto-refresh functionality
- Color-coded status indicators

### 4. Run Automation Runner
```bash
python automation/runner.py --once
```
Show the terminal output with successful execution.

### 5. Show Report Generation
```bash
ls automation/reports/
```
Show the newly created report files.

### 6. Final Confirmation
Display the message: "Core–Bucket Bridge V2 Fully Operational ✅"

## 📋 Expected Output & Verification Checklist

✅ **Health Monitoring**:
- GET /core/health endpoint returns proper metrics
- Metrics logged to /logs/metrics.jsonl
- Dashboard displays real-time health data

✅ **Native Automation**:
- Runner executes jobs based on config
- Retry logic handles failures
- Reports saved in /automation/reports/

✅ **Enhanced Dashboard**:
- All required metrics displayed
- Color-coded status indicators
- 30-second auto-refresh

✅ **Documentation**:
- Complete setup instructions
- Testing procedures
- Project structure overview
- API endpoint documentation

✅ **Demo Script**:
- Clear steps for recording
- All components demonstrated
- Verification checkpoints

✅ **Backend Integration**:
- Logs updating in real-time
- API endpoints responding correctly
- Data persistence working

## 🚀 Additional Features

- **Real-time Monitoring**: Dashboard updates automatically
- **Comprehensive Logging**: Detailed logs for debugging
- **Modular Architecture**: Easy to extend and maintain
- **Cross-platform Compatibility**: Works on Windows, macOS, and Linux
- **Scalable Design**: Can handle multiple modules and high-frequency data
- **Retry Logic**: Automatic retry with exponential backoff
- **Configurable Automation**: JSON-based job configuration

## 📞 Support

For issues or questions about the Core–Bucket Bridge V2 system, please refer to this documentation or contact the development team.