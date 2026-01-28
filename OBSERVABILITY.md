# Core–Bucket Bridge V5 - Observability Guide

**FROZEN FOR PRODUCTION - DO NOT MODIFY**

## 📊 Log Files Overview

This document explains all system logs in plain English for operational monitoring.

## 📁 Log File Locations

All logs are stored in the `logs/` directory:

```
logs/
├── core_sync.log              # Core data synchronization events
├── metrics.jsonl              # Performance and system metrics
├── security_rejects.log       # Security violation events
├── heartbeat.log              # Module heartbeat events
├── provenance_chain.jsonl     # Immutable audit trail
└── insight/flow.log           # Dashboard integration events
```

## 📖 Understanding Each Log File

### 1. core_sync.log - Core Data Sync Events

**What it contains:** Every data update sent to the system

**Example entry:**
```
2025-01-15 10:30:45,123 - {"module": "finance", "session_id": "abc123", "timestamp": "2025-01-15T10:30:45Z", "data": {"transaction_id": "tx_001"}}
```

**What to look for:**
- High frequency = normal operation
- Missing entries = potential data loss
- Error patterns = module issues

### 2. metrics.jsonl - Performance Metrics

**What it contains:** System performance data in JSON Lines format

**Example entry:**
```json
{"timestamp": "2025-01-15T10:30:45Z", "endpoint": "/core/update", "module": "finance", "status": "success", "latency_ms": 45, "pending_queue": 0}
```

**Key fields:**
- `latency_ms`: Response time (should be < 100ms)
- `status`: "success" or "error"
- `pending_queue`: Requests waiting to be processed
- `endpoint`: Which API endpoint was called

**What to monitor:**
- Latency > 100ms = performance issue
- Status = "error" = failure investigation needed
- Pending queue > 10 = system overload

### 3. security_rejects.log - Security Violations

**What it contains:** All rejected security events

**Example entry:**
```
2025-01-15 10:30:45,123 - Invalid signature for /core/update
```

**Common messages:**
- "Invalid signature" = tampered data or wrong key
- "Expired token" = JWT token timeout
- "Insufficient privileges" = unauthorized access attempt
- "Replay attack detected" = duplicate request attempt

**What to do:**
- Occasional rejections = normal security working
- High volume = potential attack or configuration issue
- Investigate source IP and module involved

### 4. heartbeat.log - Module Health Status

**What it contains:** Periodic health checks from active modules

**Example entry:**
```json
{"module": "rule-engine", "timestamp": "2025-01-15T10:30:45Z", "status": "alive", "metrics": {"cpu": 45, "memory": 128}}
```

**Status values:**
- "alive" = module operating normally
- "warning" = module has issues but still functional
- "error" = module not functioning properly

**What to monitor:**
- Missing heartbeats = module offline
- Status = "error" = immediate investigation needed
- Metrics anomalies = resource issues

### 5. provenance_chain.jsonl - Immutable Audit Trail

**What it contains:** Cryptographically secure record of all data transactions

**Example entry:**
```json
{
  "hash": "a1b2c3d4e5f6...",
  "previous_hash": "f6e5d4c3b2a1...",
  "payload": {"module": "finance", "data": {...}},
  "timestamp": "2025-01-15T10:30:45Z"
}
```

**What it ensures:**
- Data integrity: Any tampering breaks the chain
- Audit trail: Complete history of all transactions
- Non-repudiation: Proof of what happened when

**What to verify:**
- Chain continuity (each hash matches previous)
- No gaps in timestamps
- All expected modules appear

### 6. insight/flow.log - Dashboard Integration Events

**What it contains:** Events for frontend dashboard display

**Example entry:**
```json
{"event_type": "core_update", "module": "finance", "timestamp": "2025-01-15T10:30:45Z", "status": "success"}
```

**Event types:**
- "core_update" = data received from module
- "heartbeat" = module health check
- "signature_rejection" = security violation
- "replay_rejection" = duplicate request blocked

**What it's used for:**
- Real-time dashboard updates
- Operational monitoring
- Alerting systems

## 🚨 Alerting Thresholds

### Critical Alerts (Immediate Action Required)
- **Security rejections** > 10 per minute = potential attack
- **Heartbeat failures** > 5 modules = system outage
- **Pending queue** > 50 = system overload
- **Error rate** > 1% = functional issues

### Warning Alerts (Investigate Soon)
- **Latency** > 100ms for > 5 minutes = performance degradation
- **Missing heartbeats** from 1-2 modules = partial outage
- **Security rejections** > 1 per minute = suspicious activity

### Info Alerts (Monitor)
- **System uptime** < 99.9% = availability issue
- **Average latency** > 50ms = optimization opportunity

## 📊 Monitoring Commands

### Check system health:
```bash
curl http://localhost:8000/core/health
```

### View recent security events:
```bash
tail -f logs/security_rejects.log
```

### Monitor performance metrics:
```bash
tail -f logs/metrics.jsonl | jq '.latency_ms'
```

### Check module heartbeats:
```bash
tail -f logs/heartbeat.log | jq '.status'
```

## 🔧 Log Rotation and Retention

- **Daily rotation:** All logs rotate daily at midnight
- **Retention:** 30 days of logs kept
- **Compression:** Older logs are compressed
- **Backup:** Critical logs backed up to secure storage

## 📞 Support Escalation

**Level 1 (Operations):**
- Monitor dashboards and logs
- Basic troubleshooting
- Contact: Operations team

**Level 2 (Engineering):**
- Deep log analysis
- Configuration issues
- Contact: Backend team

**Level 3 (Security):**
- Security incident response
- Forensic analysis
- Contact: Security team

---
**THIS DOCUMENT IS FROZEN FOR PRODUCTION - ANY CHANGES REQUIRE FORMAL APPROVAL**