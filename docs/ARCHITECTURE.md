# Architecture

## System Overview

Athena Agent v2.0 is a comprehensive AI agent platform with real-time monitoring, external integrations, and adaptive training capabilities.

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                        Web Dashboard (SPA)                       │
│  Dashboard │ Chat │ Memory │ Decisions │ Knowledge │ Training   │
└─────────────────────────────┬────────────────────────────────────┘
                              │ WebSocket + REST
┌─────────────────────────────▼────────────────────────────────────┐
│                      FastAPI Server                               │
│  Router (/api/v1) │ WebSocket │ Static Files │ Templates          │
└──────┬──────────────┬──────────────┬──────────────┬──────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  System    │ │   Token    │ │Training    │ │Integrations│
│  Monitor   │ │  Metrics   │ │  System    │ │   System   │
└────────────┘ └────────────┘ └────────────┘ └────────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                              │
                   ┌──────────▼──────────┐
                   │   SQLite Database   │
                   │  (WAL mode)         │
                   └─────────────────────┘
```

## Modules

### Core Layer (`src/athena/core/`)
- **agent.py** — Main orchestrator (AthenaAgent)
- **memory.py** — Episodic, semantic, working memory management
- **retrieval.py** — Context retrieval engine
- **decision.py** — Decision evaluation engine

### Integration Layer (`src/athena/integrations/`)
- **webhooks.py** — Webhook registration and event dispatch
- **api_keys.py** — API key lifecycle management
- **connectors.py** — Slack, Discord, Telegram, Zapier connectors
- **oauth.py** — OAuth flow for external services

### Monitor Layer (`src/athena/monitor/`)
- **system.py** — CPU, RAM, disk, network metrics
- **metrics.py** — Token throughput tracking

### Training Layer (`src/athena/training/`)
- **feedback.py** — User feedback collection
- **replay.py** — Session replay functionality
- **adaptation.py** — Behavioral adaptation engine

### Tools Layer (`src/athena/tools/`)
- **calculator.py** — Math/financial calculations
- **converter.py** — Unit/currency conversion
- **analyzer.py** — Text/data analysis
- **scheduler.py** — Task scheduling
- **notifier.py** — Multi-channel notifications

### Server Layer (`src/athena/server/`)
- **api.py** — FastAPI REST endpoints
- **websocket.py** — Real-time WebSocket handler
- **static/** — Dashboard CSS/JS
- **templates/** — Dashboard HTML

## Data Flow

1. User sends message via Dashboard (WebSocket or REST)
2. Agent processes through memory retrieval → decision → response
3. Response stored in episodic memory, metrics recorded
4. Real-time updates broadcast to connected clients
5. Webhooks dispatched for configured events

## Database Schema

| Table | Purpose |
|-------|---------|
| episodic_memory | Interaction history |
| semantic_memory | Knowledge facts/rules |
| decisions | Decision history |
| sessions | Session tracking |
| metrics_throughput | Token usage metrics |
| webhooks | Webhook registrations |
| api_keys | API key storage |
| oauth_tokens | OAuth tokens |
| training_feedback | User feedback |
| scheduled_tasks | Scheduled tasks |
| notifications | Notification history |
| audit_log | Security audit log |

## Security Model

- Rate limiting per client (configurable RPM)
- API key authentication with scoped permissions
- Input sanitization (XSS, SQL injection prevention)
- HMAC webhook signatures
- CSRF token generation/validation
- CORS configuration
- Audit logging for all operations

## Performance

- WAL mode SQLite for concurrent reads
- Connection pooling for LLM HTTP client
- In-memory rate limiter with cleanup
- Efficient WebSocket broadcasting
- Indexed database queries
- Lightweight dashboard (no frameworks)
