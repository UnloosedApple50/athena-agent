# Monitoring Guide

## Overview

Athena Agent includes comprehensive system monitoring to track both machine resources and agent performance metrics.

## Dashboard Views

### System Page
The System page shows real-time machine metrics:
- CPU usage (overall and per-core)
- RAM usage (total, used, available, swap)
- Disk usage per mount point
- Network I/O (bytes sent/received)
- Process count and uptime

### Dashboard Page
The Dashboard shows:
- Quick stats cards for CPU, RAM, Disk, Network
- Token throughput chart (live)
- Recent activity feed
- Quick stats grid (sessions, memories, decisions, knowledge)

## Metrics Collected

### System Metrics

| Metric | Source | Endpoint |
|--------|--------|----------|
| CPU Overall % | psutil | `/api/v1/system/metrics` |
| CPU Per-Core % | psutil | `/api/v1/system/metrics` |
| CPU Load Average | os.getloadavg() | `/api/v1/system/metrics` |
| RAM Total/Used/Available | psutil | `/api/v1/system/metrics` |
| Swap Usage | psutil | `/api/v1/system/metrics` |
| Disk Usage per Mount | psutil | `/api/v1/system/metrics` |
| Network I/O | psutil | `/api/v1/system/metrics` |
| Process Count | psutil | `/api/v1/system/metrics` |
| System Uptime | psutil | `/api/v1/system/metrics` |

### Token Throughput Metrics

| Metric | Description | Endpoint |
|--------|-------------|----------|
| Total Requests | Count of LLM requests | `/api/v1/metrics/throughput` |
| Total Tokens | Sum of all tokens | `/api/v1/metrics/throughput` |
| Avg Tokens/sec | Average throughput | `/api/v1/metrics/throughput` |
| Rolling Avg TPS | Last 100 requests average | `/api/v1/metrics/throughput` |
| Peak TPS | Highest recorded TPS | `/api/v1/metrics/throughput` |
| Avg Latency | Average response time (ms) | `/api/v1/metrics/throughput` |
| Requests/min | Current request rate | `/api/v1/metrics/throughput` |

## WebSocket Real-Time Updates

The server broadcasts metrics every 5 seconds to all connected clients:

```json
{
  "type": "realtime_metrics",
  "payload": {
    "cpu_percent": 45.2,
    "memory_percent": 62.1,
    "network_rx_bytes": 1024000,
    "network_tx_bytes": 512000,
    "tokens_per_second": 125.5,
    "active_connections": 3,
    "timestamp": 1705312200.0
  }
}
```

## Database Storage

Metrics are stored in SQLite for historical analysis:

### metrics_throughput Table
```sql
CREATE TABLE metrics_throughput (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    tokens_per_second REAL DEFAULT 0.0,
    latency_ms REAL DEFAULT 0.0,
    model TEXT DEFAULT 'unknown',
    module TEXT DEFAULT 'general',
    session_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Querying Historical Data

```bash
# Get last 24 hours of throughput data
curl http://localhost:8585/api/v1/metrics/throughput/history?hours=24
```

## Charts

The dashboard uses lightweight canvas-based charts (no external dependencies):

- **Token Throughput Chart** — Line chart showing tokens/sec over time
- **CPU History Chart** — CPU usage percentage over time
- **Memory History Chart** — RAM usage percentage over time
- **Network I/O Chart** — Bytes sent/received over time

All charts maintain a rolling window of 60 data points.

## Alerting

Configure webhooks to receive system alerts:

```bash
curl -X POST http://localhost:8585/api/v1/integrations/webhooks \
  -d '{"url": "https://your-service.com/alerts", "events": ["system.alert"]}'
```

## Performance Impact

Monitoring is designed to be lightweight:
- System metrics collected on-demand (not polled)
- Token metrics recorded per-request only
- WebSocket broadcasts throttled to 5-second intervals
- Charts render efficiently with canvas (no DOM manipulation)
- Database queries use indexes for fast retrieval

## Troubleshooting

### High CPU Usage
- Check process count on System page
- Review active WebSocket connections
- Consider reducing dashboard refresh rate

### High Memory Usage
- Check memory chart for trends
- Review number of stored memories
- Consider clearing old episodic memories

### Low Token Throughput
- Check average latency
- Verify LLM service health
- Review network connectivity
