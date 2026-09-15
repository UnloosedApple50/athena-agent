# Athena — Specialized Language Memory Agent for Sales & Trading

> Production-ready AI agent combining persistent memory, local LLM reasoning, and a web dashboard — built for sales professionals and traders.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-CPU-lightgrey.svg)
![Status](https://img.shields.io/badge/status-production-success.svg)

---

## Overview

**Athena** is a Specialized Language Memory (SLM) Agent purpose-built for sales and trading workflows. She runs entirely on your local machine, requires no GPU, and stays efficient on 8GB RAM. Athena remembers past interactions, retrieves domain-specific knowledge, and provides confident, sourced recommendations — all through a clean web interface or REST API.

### Key Features

- **Persistent Memory System** — Episodic, semantic, and working memory stored in SQLite (WAL mode for crash safety)
- **Local LLM Integration** — Default Ollama backend, configurable to any OpenAI-compatible endpoint
- **Graceful Degradation** — Rule-based fallback when LLM is unavailable; agent stays functional
- **Sales & Trading Modules** — Domain-specific reasoning for deal strategy, market analysis, risk assessment
- **Web Dashboard** — Clean, responsive UI with real-time WebSocket updates
- **REST API** — Full API for integration with external tools (CRUD on memory, chat, decisions)
- **CPU-Only, RAM-Efficient** — Designed for Intel i5-class machines with 8GB RAM

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Athena Agent                              │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Web UI  │  │   REST API   │  │       WebSocket           │  │
│  │ (HTML/JS)│  │  (FastAPI)   │  │    (Real-time)            │  │
│  └────┬─────┘  └──────┬───────┘  └───────────┬───────────────┘  │
│       │               │                       │                  │
│  ┌────▼───────────────▼───────────────────────▼───────────────┐  │
│  │                     Agent Core                              │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │  Retrieval   │  │   Decision   │  │     Memory       │  │  │
│  │  │   Engine     │  │   Engine     │  │    Manager       │  │  │
│  │  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘  │  │
│  └─────────┼────────────────┼───────────────────┼────────────┘  │
│            │                │                   │                │
│  ┌─────────▼────────────────▼───────────────────▼────────────┐  │
│  │                      Data Layer                            │  │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐  │  │
│  │  │  Knowledge   │  │  LLM Client  │  │   SQLite (WAL)   │  │  │
│  │  │  Base        │  │  (Ollama)    │  │   Memory Store   │  │  │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai) installed locally (optional — agent works without it)
- 8GB RAM minimum

### Quick Start

```bash
# Clone the repository
git clone https://github.com/UnloosedApple50/athena-agent.git
cd athena-agent

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env to match your setup

# Initialize the database
python -m athena db init

# Start Ollama (optional, for LLM features)
ollama serve
ollama pull llama3.2  # or your preferred model

# Run the server
athena run
# or: python -m athena run
```

The dashboard will be available at **http://localhost:8585**.

---

## Configuration

All configuration is managed via environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `ATHENA_HOST` | `0.0.0.0` | Server bind address |
| `ATHENA_PORT` | `8585` | Server port |
| `ATHENA_DB_PATH` | `./data/athena.db` | SQLite database path |
| `ATHENA_LLM_BASE_URL` | `http://localhost:11434/v1` | Ollama/OpenAI endpoint |
| `ATHENA_LLM_MODEL` | `llama3.2` | Model name |
| `ATHENA_LLM_TIMEOUT` | `30` | LLM timeout in seconds |
| `ATHENA_LOG_LEVEL` | `INFO` | Logging level |
| `ATHENA_MAX_MEMORY` | `10000` | Max episodic memories |
| `ATHENA_WORKING_MEMORY_SIZE` | `20` | Working memory window |

---

## API Documentation

### Chat

```http
POST /api/v1/chat
Content-Type: application/json

{
  "message": "What's the best strategy for closing enterprise deals in Q4?",
  "module": "sales",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "response": "Based on historical patterns, the most effective Q4 enterprise strategy...",
  "confidence": 0.87,
  "module": "sales",
  "session_id": "sess_abc123",
  "memories_used": 5
}
```

### Memory

```http
GET    /api/v1/memory/episodic?limit=50
GET    /api/v1/memory/semantic?query=enterprise+sales
POST   /api/v1/memory/semantic
DELETE /api/v1/memory/{memory_id}
```

### Decisions

```http
POST /api/v1/decisions
{
  "context": "Client requesting 30% discount on $500K deal",
  "options": ["Hold firm at 15%", "Meet at 25%", "Offer phased discount"],
  "module": "sales"
}
```

### Health

```http
GET /api/v1/health
```

Response:
```json
{
  "status": "healthy",
  "llm_connected": true,
  "db_connected": true,
  "uptime_seconds": 3600,
  "memory_count": 1523
}
```

---

## Memory Model

Athena uses a three-tier memory system inspired by cognitive science:

| Type | Description | Persistence |
|------|-------------|-------------|
| **Episodic** | Past interactions, outcomes, user feedback | Persistent (SQLite) |
| **Semantic** | Domain facts, rules, strategies, lessons learned | Persistent (SQLite) |
| **Working** | Current session context and reasoning state | Volatile (in-memory) |

### Retrieval Strategy

1. **Keyword Matching** — Fast BM25-like scoring on indexed fields
2. **LLM Relevance** — When LLM is available, re-rank top candidates by semantic relevance
3. **Recency Weighting** — More recent memories get higher priority
4. **Confidence Scoring** — Each retrieval includes a confidence metric

See [MEMORY_MODEL.md](docs/MEMORY_MODEL.md) for full details.

---

## Security Considerations

- All inputs are validated and sanitized via Pydantic models
- SQL queries use parameterized statements exclusively (no string interpolation)
- Rate limiting middleware is built-in (configurable limits)
- No secrets or tokens are logged
- WebSocket connections are origin-validated
- Input length limits enforced on all endpoints

See [SECURITY.md](docs/SECURITY.md) for full details.

---

## Performance Benchmarks

Tested on Intel i5-7360U, 8GB RAM, SSD:

| Operation | Latency | RAM Usage |
|-----------|---------|-----------|
| Memory retrieval (keyword) | <10ms | ~2MB |
| Memory retrieval (LLM rerank) | ~800ms | ~150MB |
| Chat (with LLM) | ~2-5s | ~300MB |
| Chat (rule-based fallback) | <50ms | ~5MB |
| WebSocket message | <5ms | <1MB |
| Database write | <5ms | ~1MB |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run `pytest --cov=athena --cov-fail-under=80`
5. Run `ruff check .` and `mypy src/`
6. Commit and push

See [INSTALLATION.md](docs/INSTALLATION.md) for development setup.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

*Built with precision by Gabriel Garcia*
