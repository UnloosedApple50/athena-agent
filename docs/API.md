# API Reference

## REST Endpoints

### Health & Status

#### `GET /api/v1/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "llm_connected": true,
  "db_connected": true,
  "uptime_seconds": 3600.5,
  "memory_count": 1500,
  "version": "2.0.0"
}
```

#### `GET /api/v1/settings`
Get current settings.

**Response:**
```json
{
  "llm_base_url": "http://localhost:11434/v1",
  "llm_model": "llama3.2",
  "host": "0.0.0.0",
  "port": 8585,
  "log_level": "INFO"
}
```

### Chat

#### `POST /api/v1/chat`
Send a message to the agent.

**Request:**
```json
{
  "message": "How should I handle price objections?",
  "module": "sales",
  "session_id": "sess_abc123"
}
```

**Response:**
```json
{
  "response": "When handling price objections...",
  "confidence": 0.85,
  "module": "sales",
  "session_id": "sess_abc123",
  "memories_used": 5,
  "fallback": false,
  "timestamp": "2025-01-15T10:30:00"
}
```

### Decisions

#### `POST /api/v1/decisions`
Make a decision between options.

**Request:**
```json
{
  "context": "Client wants to negotiate contract terms",
  "options": ["Offer discount", "Add services", "Walk away"],
  "module": "sales"
}
```

### Memory

#### `GET /api/v1/memory/episodic`
Retrieve episodic memories.

**Query Parameters:**
- `session_id` (optional) — Filter by session
- `module` (optional) — Filter by module
- `limit` (default: 50) — Maximum results

#### `GET /api/v1/memory/semantic`
Retrieve semantic memories.

**Query Parameters:**
- `module` (optional) — Filter by module
- `category` (optional) — Filter by category
- `key` (optional) — Filter by key
- `limit` (default: 50) — Maximum results

#### `POST /api/v1/memory/semantic`
Add knowledge to semantic memory.

**Request:**
```json
{
  "module": "sales",
  "category": "objection_handling",
  "key": "price_objection_response",
  "value": "When clients object to price...",
  "confidence": 0.9,
  "tags": ["objection", "pricing"]
}
```

#### `DELETE /api/v1/memory/{memory_id}`
Delete a memory.

**Query Parameters:**
- `memory_type` (default: "episodic") — Memory type

### Sessions

#### `GET /api/v1/sessions/{session_id}`
Get chat history for a session.

### Feedback

#### `POST /api/v1/feedback/{memory_id}`
Provide feedback on a past interaction.

**Request:**
```json
{
  "outcome": "successful_close",
  "score": 0.95
}
```

### System Metrics

#### `GET /api/v1/system/metrics`
Get real-time system metrics.

**Response:**
```json
{
  "timestamp": 1705312200.0,
  "cpu": {
    "overall_percent": 45.2,
    "per_core_percent": [40.0, 50.4],
    "core_count": 8,
    "load_average": [1.5, 1.2, 0.8],
    "frequency_mhz": 2400
  },
  "ram": {
    "total_bytes": 17179869184,
    "used_bytes": 8589934592,
    "available_bytes": 8589934592,
    "percent_used": 50.0,
    "total_human": "16.0 GB",
    "used_human": "8.0 GB",
    "available_human": "8.0 GB"
  },
  "disks": [...],
  "network": {...},
  "process_count": 245,
  "uptime_seconds": 86400,
  "uptime_human": "1d 0h 0m 0s",
  "platform": {
    "system": "Darwin",
    "release": "24.0.0",
    "machine": "arm64",
    "python": "3.11.15",
    "hostname": "macbook"
  }
}
```

#### `GET /api/v1/system/info`
Get system information.

### Token Throughput

#### `GET /api/v1/metrics/throughput`
Get token throughput metrics.

**Response:**
```json
{
  "total_requests": 1500,
  "total_prompt_tokens": 450000,
  "total_completion_tokens": 225000,
  "total_tokens": 675000,
  "avg_tokens_per_second": 125.5,
  "avg_latency_ms": 450.2,
  "rolling_avg_tps": 130.8,
  "peak_tps": 250.0,
  "min_tps": 50.0,
  "requests_per_minute": 25.3,
  "models_used": {"llama3.2": 1500},
  "modules_used": {"sales": 800, "trading": 500, "general": 200}
}
```

#### `GET /api/v1/metrics/throughput/history?hours=24`
Get historical throughput metrics.

### Integrations

#### `GET /api/v1/integrations`
List all configured integrations.

#### `GET /api/v1/integrations/webhooks`
List registered webhooks.

#### `POST /api/v1/integrations/webhooks`
Register a new webhook.

**Request:**
```json
{
  "url": "https://your-webhook.com/endpoint",
  "events": ["chat.created", "decision.made"]
}
```

**Response:**
```json
{
  "id": "wh_abc123def456",
  "url": "https://your-webhook.com/endpoint",
  "events": ["chat.created", "decision.made"],
  "secret": "whsec_xyz789...",
  "status": "registered"
}
```

#### `DELETE /api/v1/integrations/webhooks/{webhook_id}`
Remove a webhook.

#### `POST /api/v1/integrations/api-keys`
Generate a new API key.

**Request:**
```json
{
  "name": "my-app-key",
  "scopes": ["chat", "memory.read"],
  "rate_limit": 100
}
```

**Response:**
```json
{
  "key": "athena_AbCdEfGhIjKlMnOpQrStUvWxYz123456",
  "id": "key_abc123",
  "name": "my-app-key",
  "prefix": "athena_AbCd...",
  "scopes": ["chat", "memory.read"],
  "created_at": "2025-01-15T10:30:00"
}
```

#### `DELETE /api/v1/integrations/api-keys/{key_id}`
Revoke an API key.

#### `POST /api/v1/integrations/{service}/connect`
Connect an external service (slack, discord, telegram, zapier).

**Request (Slack):**
```json
{
  "bot_token": "xoxb-your-token",
  "channel_id": "C123456"
}
```

#### `DELETE /api/v1/integrations/{service}`
Disconnect a service.

### Training

#### `POST /api/v1/training/feedback`
Submit feedback on a response.

**Request:**
```json
{
  "memory_id": 42,
  "rating": 4,
  "correction": "Should mention BANT framework",
  "comment": "Good but incomplete",
  "category": "sales_methodology"
}
```

#### `GET /api/v1/training/history`
Get feedback history.

**Query Parameters:**
- `session_id` (optional) — Filter by session
- `module` (optional) — Filter by module
- `limit` (default: 50) — Maximum results

#### `GET /api/v1/training/stats`
Get training statistics.

#### `POST /api/v1/training/adapt`
Trigger adaptation based on feedback.

#### `POST /api/v1/training/replay/{session_id}`
Replay a session's interactions.

## WebSocket

Connect to `ws://host:port/ws` for real-time updates.

### Message Types

#### Client → Server

| Type | Payload | Description |
|------|---------|-------------|
| `chat` | `{message, module, session_id}` | Send chat message |
| `ping` | `{}` | Ping (responds with pong) |
| `health` | `{}` | Health check |
| `get_metrics` | `{}` | Get token metrics |
| `get_system_metrics` | `{}` | Get system metrics |

#### Server → Client

| Type | Payload | Description |
|------|---------|-------------|
| `connected` | `{connection_id, message, timestamp}` | Welcome message |
| `response` | `{response, confidence, module, ...}` | Chat response |
| `processing` | `{message}` | Processing indicator |
| `pong` | `{timestamp}` | Ping response |
| `health` | `{status, uptime_seconds, ...}` | Health status |
| `metrics` | `{total_requests, total_tokens, ...}` | Token metrics |
| `system_metrics` | `{cpu, ram, disks, network}` | System metrics |
| `realtime_metrics` | `{cpu_percent, memory_percent, ...}` | Periodic updates |
| `notification` | `{title, message, level}` | System notification |
| `error` | `{message}` | Error message |

### Example WebSocket Session

```javascript
const ws = new WebSocket('ws://localhost:8585/ws');

ws.onopen = () => ws.send(JSON.stringify({
    type: 'chat',
    payload: { message: 'Hello!', module: 'general' }
}));

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data.type, data.payload);
};
```

## Error Responses

All endpoints return standard HTTP error codes:

| Code | Meaning |
|------|---------|
| 400 | Bad Request — Invalid input |
| 404 | Not Found — Resource doesn't exist |
| 422 | Validation Error — Invalid request body |
| 429 | Too Many Requests — Rate limit exceeded |
| 500 | Internal Server Error |
| 503 | Service Unavailable — Agent not ready |

Error response format:
```json
{
  "detail": "Error description"
}
```
