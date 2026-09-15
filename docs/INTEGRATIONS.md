# Integrations Guide

## Overview

Athena Agent's integrations system allows you to connect external services, register webhooks for event notifications, and generate API keys for programmatic access.

## Webhooks

### Registering a Webhook

```bash
curl -X POST http://localhost:8585/api/v1/integrations/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-service.com/webhook",
    "events": ["chat.created", "decision.made"]
  }'
```

### Available Events

| Event | Description |
|-------|-------------|
| `chat.created` | New chat message received |
| `chat.response` | Agent response generated |
| `decision.made` | Decision evaluated |
| `memory.created` | New memory stored |
| `memory.updated` | Memory updated |
| `knowledge.added` | Knowledge fact added |
| `training.feedback` | Feedback submitted |
| `system.alert` | System alert triggered |

### Webhook Payload

```json
{
  "event": "chat.created",
  "timestamp": "2025-01-15T10:30:00",
  "data": {
    "session_id": "sess_abc123",
    "module": "sales",
    "query": "How to handle price objections?"
  }
}
```

### Signature Verification

Webhooks include an HMAC-SHA256 signature in the `X-Webhook-Signature` header:

```python
import hmac, hashlib

signature = hmac.new(
    webhook_secret.encode(),
    payload.encode(),
    hashlib.sha256
).hexdigest()

assert signature == request.headers["X-Webhook-Signature"]
```

## API Keys

### Generating a Key

```bash
curl -X POST http://localhost:8585/api/v1/integrations/api-keys \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-application",
    "scopes": ["chat", "memory.read"]
  }'
```

### Available Scopes

| Scope | Permission |
|-------|-----------|
| `chat` | Send chat messages |
| `decisions` | Make decisions |
| `memory.read` | Read memories |
| `memory.write` | Create/update memories |
| `knowledge.read` | Read knowledge |
| `knowledge.write` | Add knowledge |
| `metrics` | Read metrics |
| `system` | Read system info |
| `webhooks` | Manage webhooks |
| `admin` | Full access |

### Using an API Key

```bash
curl -X POST http://localhost:8585/api/v1/chat \
  -H "Authorization: Bearer athena_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "module": "general"}'
```

## External Connectors

### Slack

```bash
curl -X POST http://localhost:8585/api/v1/integrations/slack/connect \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "xoxb-your-bot-token",
    "channel_id": "C1234567890"
  }'
```

### Discord

```bash
curl -X POST http://localhost:8585/api/v1/integrations/discord/connect \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "your-bot-token",
    "channel_id": "1234567890"
  }'
```

### Telegram

```bash
curl -X POST http://localhost:8585/api/v1/integrations/telegram/connect \
  -H "Content-Type: application/json" \
  -d '{
    "bot_token": "123456:ABC-DEF...",
    "channel_id": "-1001234567890"
  }'
```

### Zapier

```bash
curl -X POST http://localhost:8585/api/v1/integrations/zapier/connect \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://hooks.zapier.com/hooks/catch/..."
  }'
```

## OAuth Flow

### Supported Providers
- Google
- GitHub
- Microsoft

### Flow
1. Register provider with client credentials
2. Get authorization URL
3. User authorizes and is redirected back
4. Exchange code for tokens

## Rate Limiting

All API endpoints are rate-limited. Default: 100 requests per minute.

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705312260
```

When rate limited, you'll receive:
```json
{
  "detail": "Rate limit exceeded. Retry after 60 seconds."
}
```
