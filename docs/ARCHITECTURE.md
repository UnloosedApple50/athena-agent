# Architecture

## Overview

Athena is a Specialized Language Memory (SLM) Agent built for sales and trading professionals. It combines persistent memory, local LLM reasoning, and a clean web interface.

## System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │  Web UI      │  │  REST API     │  │  WebSocket      │  │
│  │  (HTML/CSS)  │  │  (FastAPI)    │  │  (Real-time)    │  │
│  └──────┬───────┘  └──────┬────────┘  └───────┬─────────┘  │
└─────────┼─────────────────┼───────────────────┼────────────┘
          │                 │                   │
┌─────────▼─────────────────▼───────────────────▼────────────┐
│                      Core Layer                              │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │  Agent       │  │  Decision     │  │  Retrieval      │  │
│  │  Orchestrator│  │  Engine       │  │  Engine         │  │
│  └──────┬───────┘  └──────┬────────┘  └───────┬─────────┘  │
│         │                 │                   │             │
│  ┌──────▼─────────────────▼───────────────────▼──────────┐  │
│  │                   Memory Manager                      │  │
│  └──────┬────────────────────────────────┬──────────────┘  │
└─────────┼────────────────────────────────┼─────────────────┘
          │                                │
┌─────────▼─────────────┐    ┌─────────────▼────────────────┐
│   Data Layer          │    │   External Services          │
│  ┌──────────────────┐ │    │  ┌────────────────────────┐  │
│  │  SQLite (WAL)    │ │    │  │  LLM (Ollama/OpenAI)  │  │
│  │  + Migrations    │ │    │  └────────────────────────┘  │
│  └──────────────────┘ │    └──────────────────────────────┘
│  ┌──────────────────┐ │
│  │  Knowledge Base  │ │
│  └──────────────────┘ │
└───────────────────────┘
```

## Component Details

### 1. Agent Core (`core/agent.py`)

The main orchestrator that:
- Validates and sanitizes inputs
- Delegates to retrieval and decision engines
- Manages session lifecycle
- Stores interactions in episodic memory
- Tracks confidence scores

### 2. Memory System (`core/memory.py`)

Three-tier memory inspired by cognitive science:

| Type | Description | Storage |
|------|-------------|---------|
| **Episodic** | Full interaction history | SQLite (persistent) |
| **Semantic** | Facts, rules, knowledge | SQLite (persistent) |
| **Working** | Current session context | In-memory LRU |

### 3. Retrieval Engine (`core/retrieval.py`)

Multi-stage retrieval pipeline:
1. **Keyword Matching** — Fast BM25-like scoring
2. **LLM Re-ranking** — Semantic relevance (when available)
3. **Recency Weighting** — Time-decay for older memories
4. **Confidence Scoring** — Combined relevance metric

### 4. Decision Engine (`core/decision.py`)

Dual-mode decision making:
- **LLM Mode** — Structured analysis with reasoning
- **Rule-Based Fallback** — Pattern matching against domain rules

Domain-specific rules for:
- Sales (closing, negotiation, objection handling, prospecting)
- Trading (risk management, technical analysis, portfolio)
- General (finance fundamentals, communication)

### 5. LLM Client (`models/llm.py`)

HTTP client for OpenAI-compatible endpoints:
- Connection pooling
- Configurable timeouts
- Retry with exponential backoff
- Health checking
- Relevance scoring capability

### 6. Database Layer (`db/database.py`)

SQLite with WAL (Write-Ahead Logging) mode:
- **Crash Safety** — WAL ensures data integrity
- **Concurrent Reads** — Multiple readers don't block writes
- **Parameterized Queries** — All queries use parameter binding
- **Connection Pooling** — Efficient connection management

### 7. Web Server (`server/api.py`)

FastAPI application with:
- REST API for all operations
- WebSocket for real-time communication
- Static file serving for the dashboard
- Pydantic validation on all endpoints
- Automatic OpenAPI documentation

## Data Flow

### Chat Request Flow

```
User → WebSocket/REST → Agent.chat()
                         │
                    ┌────▼────┐
                    │Sanitize │
                    └────┬────┘
                         │
              ┌──────────▼──────────┐
              │ Decision.analyze()  │
              │  ├─ Retrieval.retrieve()
              │  │   ├─ Keyword search
              │  │   └─ LLM rerank
              │  ├─ LLM generate (if available)
              │  └─ Rule fallback
              └──────────┬──────────┘
                         │
              ┌──────────▼──────────┐
              │ Store episodic      │
              │ memory              │
              └──────────┬──────────┘
                         │
                    ┌────▼────┐
                    │ Response│
                    └─────────┘
```

### Memory Retrieval Flow

```
Query → RetrievalEngine.retrieve()
         │
    ┌────▼────┐
    │Keyword  │ → Candidate set from semantic + episodic
    │Search   │
    └────┬────┘
         │
    ┌────▼────┐     ┌──────────┐
    │LLM      │────▶│Relevance │
    │Rerank   │◀────│Scoring   │
    └────┬────┘     └──────────┘
         │
    ┌────▼────┐
    │Sort &   │
    │Filter   │
    └────┬────┘
         │
    ┌────▼────┐
    │Top-K    │
    │Results  │
    └─────────┘
```

## Scalability Considerations

### Current Design (Single Machine)
- SQLite handles up to ~100K memories efficiently
- Working memory limited to 20 entries per session
- LLM client limited to 10 concurrent connections
- FastAPI handles thousands of requests per second

### Future Scaling Path
- Replace SQLite with PostgreSQL for multi-user
- Add Redis for distributed working memory
- Implement true embeddings (sentence-transformers) for retrieval
- Add Celery for async task processing
- Containerize with Docker for deployment

## Security Architecture

1. **Input Validation** — Pydantic models on all endpoints
2. **SQL Injection Prevention** — Parameterized queries only
3. **XSS Prevention** — HTML escaping, CSP-ready
4. **Rate Limiting** — Built-in middleware (configurable)
5. **No Secrets in Logs** — Structured logging with filtering
6. **WebSocket Origin Validation** — Same-origin enforcement
