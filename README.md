# Athena Agent v2.0

A comprehensive Specialized Language Memory Agent for Sales & Trading with real-time dashboard, system monitoring, integrations, and agent training capabilities.

## Features

### Core Capabilities
- **Multi-Module Agent** — Sales, Trading, and General advisory contexts
- **Memory System** — Episodic, Semantic, and Working memory
- **Decision Engine** — Structured decision-making with confidence scoring
- **Knowledge Base** — Domain-specific facts and rules for sales & trading

### New in v2.0
- **Real-Time Web Dashboard** — Interactive SPA with live metrics, chat, memory browsing, and system monitoring
- **System Monitoring** — CPU, RAM, Disk, Network I/O metrics with live charts
- **Token Throughput Tracking** — Tokens/sec, latency, rolling averages
- **Integrations System** — Webhooks, API Keys, Slack/Discord/Telegram/Zapier connectors, OAuth
- **Agent Training** — Feedback collection, replay, and behavioral adaptation
- **New Tools** — Calculator, Converter, Analyzer, Scheduler, Notifier
- **Enhanced Security** — Rate limiting, audit logging, CSRF protection, CORS

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the server
python -m athena

# Or use the CLI
athena
```

The dashboard will be available at `http://localhost:8585`.

## Dashboard Views

| View | Description |
|------|-------------|
| Dashboard | Real-time system stats, token throughput charts |
| Chat | Full conversation interface with module selection |
| Memory | Browse/search episodic, semantic, working memory |
| Decisions | View decision history with confidence tracking |
| Knowledge | Browse and add facts/rules |
| Integrations | Configure webhooks, API keys, external connectors |
| Training | Submit feedback, run adaptation, replay sessions |
| System | Real-time machine monitoring with charts |
| Settings | LLM config, server config, security settings |

## API Endpoints

### Core
- `GET /api/v1/health` — Health check
- `POST /api/v1/chat` — Send a message
- `POST /api/v1/decisions` — Make a decision
- `GET /api/v1/memory/episodic` — Retrieve episodic memories
- `GET /api/v1/memory/semantic` — Retrieve semantic memories
- `POST /api/v1/memory/semantic` — Add knowledge
- `DELETE /api/v1/memory/{id}` — Delete a memory

### System & Metrics
- `GET /api/v1/system/metrics` — Real-time system metrics
- `GET /api/v1/system/info` — System information
- `GET /api/v1/metrics/throughput` — Token throughput metrics
- `GET /api/v1/metrics/throughput/history` — Historical throughput

### Integrations
- `GET /api/v1/integrations` — List all integrations
- `POST /api/v1/integrations/webhooks` — Register webhook
- `GET /api/v1/integrations/webhooks` — List webhooks
- `POST /api/v1/integrations/api-keys` — Generate API key
- `POST /api/v1/integrations/{service}/connect` — Connect service
- `DELETE /api/v1/integrations/{service}` — Disconnect service

### Training
- `POST /api/v1/training/feedback` — Submit feedback
- `GET /api/v1/training/history` — View feedback history
- `GET /api/v1/training/stats` — Training statistics
- `POST /api/v1/training/adapt` — Trigger adaptation
- `POST /api/v1/training/replay/{session_id}` — Replay session

## WebSocket

Connect to `ws://localhost:8585/ws` for real-time updates:

```json
{"type": "chat", "payload": {"message": "Hello", "module": "general"}}
{"type": "ping", "payload": {}}
{"type": "health", "payload": {}}
{"type": "get_metrics", "payload": {}}
{"type": "get_system_metrics", "payload": {}}
```

## Configuration

Environment variables (prefix: `ATHENA_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ATHENA_HOST` | `0.0.0.0` | Server host |
| `ATHENA_PORT` | `8585` | Server port |
| `ATHENA_LLM_BASE_URL` | `http://localhost:11434/v1` | LLM API URL |
| `ATHENA_LLM_MODEL` | `llama3.2` | LLM model name |
| `ATHENA_DB_PATH` | `./data/athena.db` | Database path |
| `ATHENA_LOG_LEVEL` | `INFO` | Logging level |
| `ATHENA_RATE_LIMIT` | `100` | Requests per minute |
| `ATHENA_MAX_INPUT_LENGTH` | `10000` | Max input characters |

## Architecture

```
src/athena/
├── core/           # Agent, Memory, Retrieval, Decision engines
├── db/             # Database layer and migrations
├── integrations/   # Webhooks, API Keys, Connectors, OAuth
├── monitor/        # System monitoring and metrics
├── training/       # Feedback, Replay, Adaptation
├── tools/          # Calculator, Converter, Analyzer, Scheduler, Notifier
├── server/         # FastAPI server, WebSocket, static files
├── models/         # LLM client, configuration
├── knowledge/      # Domain knowledge base
└── utils/          # Security, logging utilities
```

## Testing

```bash
# Run all tests with coverage
pytest --cov=athena --cov-report=term-missing

# Run specific test module
pytest tests/test_system.py -v
```

## License

MIT License
