# API Documentation

## Base URL

```
http://localhost:8585/api/v1
```

## Endpoints

### Health

#### GET /health

Returns the current health status of the agent.

**Response:**
```json
{
  "status": "healthy",
  "llm_connected": true,
  "db_connected": true,
  "uptime_seconds": 3600.5,
  "memory_count": 1523,
  "version": "1.0.0"
}
```

---

### Chat

#### POST /chat

Send a message to the agent and receive a response.

**Request:**
```json
{
  "message": "What's the best strategy for closing enterprise deals?",
  "module": "sales",
  "session_id": "optional-session-id"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| message | string | Yes | User message (1-10000 chars) |
| module | string | No | `general`, `sales`, or `trading` (default: `general`) |
| session_id | string | No | Session ID for context (auto-generated if omitted) |

**Response (200):**
```json
{
  "response": "Based on domain knowledge, the most effective strategy...",
  "confidence": 0.87,
  "module": "sales",
  "session_id": "sess_abc123def456",
  "memories_used": 5,
  "fallback": false,
  "timestamp": "2024-01-15T10:30:00"
}
```

**Errors:**
- `400` — Invalid module or input
- `422` — Validation error (empty message, etc.)
- `500` — Internal processing error

---

### Decisions

#### POST /decisions

Request a decision between multiple options.

**Request:**
```json
{
  "context": "Client requesting 30% discount on $500K deal",
  "options": [
    "Hold firm at 15%",
    "Meet at 25%",
    "Offer phased discount over 2 years"
  ],
  "module": "sales",
  "session_id": "optional-session-id"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| context | string | Yes | Decision context (1-10000 chars) |
| options | array | Yes | 2-10 options to evaluate |
| module | string | No | Module context (default: `general`) |
| session_id | string | No | Session ID |

**Response (200):**
```json
{
  "context": "Client requesting 30% discount on $500K deal",
  "recommendation": "Meet at 25% with additional value-adds...",
  "confidence": 0.82,
  "reasoning": "Based on negotiation best practices...",
  "module": "sales",
  "options": ["Hold firm at 15%", "Meet at 25%", "Offer phased discount"],
  "selected_option": "Meet at 25%",
  "risks": ["Sets precedent for deep discounts", "May reduce margin"],
  "supporting_evidence": ["[negotiation] anchoring: First number influences outcome..."]
}
```

---

### Episodic Memory

#### GET /memory/episodic

Retrieve past interactions.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| session_id | string | — | Filter by session |
| module | string | — | Filter by module |
| limit | integer | 50 | Max results (1-100) |

**Response (200):**
```json
[
  {
    "id": 1,
    "session_id": "sess_abc123",
    "module": "sales",
    "query": "How do I handle pricing objections?",
    "response": "Use the feel-felt-found framework...",
    "confidence": 0.85,
    "outcome": "success",
    "created_at": "2024-01-15T10:30:00"
  }
]
```

#### DELETE /memory/{memory_id}?memory_type=episodic

Delete a specific memory.

**Response (200):**
```json
{"status": "deleted"}
```

---

### Semantic Memory

#### GET /memory/semantic

Retrieve domain knowledge and facts.

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| module | string | — | Filter by module |
| category | string | — | Filter by category |
| key | string | — | Filter by key |
| limit | integer | 50 | Max results |

**Response (200):**
```json
[
  {
    "id": 1,
    "module": "sales",
    "category": "closing",
    "key": "assumptive_close",
    "value": "Proceed as if the prospect has decided...",
    "confidence": 0.9,
    "tags": ["closing", "tactic"],
    "use_count": 5
  }
]
```

#### POST /memory/semantic

Add knowledge to semantic memory.

**Request:**
```json
{
  "module": "sales",
  "category": "negotiation",
  "key": "custom_strategy",
  "value": "Always trade concessions, never give unilaterally.",
  "confidence": 0.9,
  "tags": ["negotiation", "custom"]
}
```

**Response (200):**
```json
{"id": 42, "status": "created"}
```

#### DELETE /memory/{memory_id}?memory_type=semantic

Delete a semantic memory.

---

### Sessions

#### GET /sessions/{session_id}

Get chat history for a session.

**Response (200):**
```json
[
  {
    "query": "How do I close deals?",
    "response": "Use assumptive close techniques...",
    "confidence": 0.85,
    "created_at": "2024-01-15T10:30:00"
  }
]
```

---

### Feedback

#### POST /feedback/{memory_id}

Provide outcome feedback on a past interaction.

**Request:**
```json
{
  "outcome": "Deal closed at 20% discount",
  "score": 0.8
}
```

**Response (200):**
```json
{"status": "received"}
```

---

## WebSocket API

### Connection

```
ws://localhost:8585/ws
```

### Message Types

#### Client → Server

**Chat:**
```json
{
  "type": "chat",
  "payload": {
    "message": "Query text",
    "module": "sales",
    "session_id": "optional"
  }
}
```

**Ping:**
```json
{"type": "ping"}
```

**Health Check:**
```json
{"type": "health"}
```

#### Server → Client

**Connected:**
```json
{
  "type": "connected",
  "payload": {
    "connection_id": "sess_xyz",
    "message": "Connected to Athena Agent",
    "timestamp": 1705312200.0
  }
}
```

**Response:**
```json
{
  "type": "response",
  "payload": {
    "response": "Agent's reply...",
    "confidence": 0.87,
    "module": "sales",
    "session_id": "sess_xyz",
    "memories_used": 5,
    "fallback": false,
    "timestamp": "2024-01-15T10:30:00"
  }
}
```

**Processing:**
```json
{
  "type": "processing",
  "payload": {"message": "Analyzing your query..."}
}
```

**Error:**
```json
{
  "type": "error",
  "payload": {"message": "Description of error"}
}
```
