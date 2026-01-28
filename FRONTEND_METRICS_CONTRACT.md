# Core–Bucket Bridge V5 - Frontend Metrics Contract

## 📋 Overview

This document specifies the metrics and log fields that the frontend/dashboard system consumes from the Core–Bucket Bridge V5 backend. These fields must remain stable and backward-compatible.

## 📊 Immutable Health Metrics Fields

These fields from the `/core/health` endpoint must never change:

### Core Health Fields
```json
{
  "status": "string (must be exactly 'ok' or 'error')",
  "uptime_s": "float (seconds since system startup)",
  "pending_queue": "integer (number of pending requests)",
  "error_count_24h": "integer (rolling 24-hour error count)",
  "avg_latency_ms_24h": "float (rolling 24-hour average latency in milliseconds)"
}
```

### Security Metrics Fields
```json
{
  "security": {
    "signature_rejects_24h": "integer (rolling 24-hour signature rejection count)",
    "replay_rejects_24h": "integer (rolling 24-hour replay attack rejection count)",
    "last_valid_signature_ts": "object mapping module names to ISO 8601 timestamps",
    "last_nonce": "string or null (most recent nonce processed)"
  }
}
```

## 📈 Log File Consumption

### Metrics Log Format (logs/metrics.jsonl)
Each line contains a JSON object with these guaranteed fields:
```json
{
  "timestamp": "ISO 8601 UTC timestamp",
  "endpoint": "string (endpoint that generated this metric)",
  "module": "string (module name, may be empty)",
  "status": "string (success|error|rejected)"
}
```

Additional fields may be present depending on the endpoint:
- For `/core/update`: `latency_ms`, `pending_queue`
- For `/core/heartbeat`: `provenance_hash`
- For `/core/health`: `uptime_s`, `pending_queue`, `error_count_24h`, `avg_latency_ms_24h`

### Heartbeat Log Format (logs/heartbeat.log)
Each line contains a JSON object with these fields:
```json
{
  "module": "string (module that sent heartbeat)",
  "timestamp": "ISO 8601 UTC timestamp",
  "status": "string (alive|warning|error)",
  "metrics": "object (optional custom metrics from module)"
}
```

### Security Rejection Log Format (logs/security_rejects.log)
Each line contains a JSON object with these fields:
```json
{
  "timestamp": "ISO 8601 UTC timestamp",
  "message": "string (description of security event)"
}
```

### Provenance Chain Format (logs/provenance_chain.jsonl)
Each line contains a JSON object with these fields:
```json
{
  "hash": "string (SHA256 hash of this entry)",
  "previous_hash": "string (SHA256 hash of previous entry)",
  "payload": "object (original payload data)",
  "timestamp": "ISO 8601 UTC timestamp"
}
```

## 🔄 Integration Log Format (logs/insight/integration.jsonl)

For dashboard integration events:
```json
{
  "timestamp": "ISO 8601 UTC timestamp",
  "module": "string (module name)",
  "event_type": "string (type of integration event)",
  "status": "string (success|error|warning)"
}
```

## 🎯 Required Dashboard Components

### Health Status Panel
Must display:
- Overall system status (OK/Error)
- Uptime in human-readable format
- Pending queue depth
- 24-hour error count
- Average latency (ms)

### Security Events Panel
Must display:
- 24-hour signature rejection count
- 24-hour replay attack count
- Last valid signature timestamps per module
- Security status indicator (OK/WARN)

### Module Activity Panel
Must display:
- Last sync time per module
- Heartbeat status per module
- Module-specific metrics from heartbeat logs

### Provenance Chain Viewer
Must display:
- Hash chain integrity visualization
- Timestamps of entries
- Navigation through chain

## ⚠️ Backward Compatibility Rules

### Field Changes
1. New fields may be added to any response
2. Existing fields must not change data type
3. Existing fields must not change meaning
4. Fields may not be removed once published

### Endpoint Changes
1. Existing endpoints must maintain current behavior
2. New endpoints may be added
3. Deprecated endpoints must be marked with sunset headers

### Log Format Changes
1. New log fields may be added
2. Existing log fields must not change format
3. Log file locations must not change
4. Log rotation policies must be documented

## 📞 Frontend Contact Information

For frontend/dashboard integration questions:
- **Frontend Lead**: Chandragupta
- **Dashboard Repository**: [Specify repository location]
- **Support Channel**: [Specify communication channel]

---
*This document defines the stable contract between Core–Bucket Bridge V5 backend and frontend systems. Any changes require coordination with the frontend team.*