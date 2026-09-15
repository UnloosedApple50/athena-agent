# Memory Model

## Overview

Athena's memory system is modeled after human cognitive memory, consisting of three distinct types that work together to provide context-aware responses.

## Memory Types

### 1. Episodic Memory

**Purpose:** Records specific interactions, their context, and outcomes.

**Structure:**
```
EpisodicMemory
├── id: Unique identifier
├── session_id: Groups interactions into conversations
├── module: Domain context (sales/trading/general)
├── query: The user's question
├── response: Athena's answer
├── confidence: How confident Athena was (0-1)
├── outcome: User-provided feedback on result
├── outcome_score: Numerical outcome rating (0-1)
├── metadata: Additional structured data
└── created_at: Timestamp
```

**Use Cases:**
- "What did we discuss last Tuesday about the Acme deal?"
- "Has this client asked about pricing before?"
- "What strategies have worked for similar objections?"

**Characteristics:**
- Never automatically deleted (unless manually pruned)
- Session-grouped for conversation continuity
- Outcome-tagged for learning from feedback
- Indexed by session, module, and timestamp

---

### 2. Semantic Memory

**Purpose:** Stores domain knowledge, facts, rules, and best practices.

**Structure:**
```
SemanticMemory
├── id: Unique identifier
├── module: Domain context
├── category: Grouping (closing, risk_management, etc.)
├── key: Unique identifier within module+category
├── value: The actual knowledge content
├── confidence: Reliability of the fact (0-1)
├── source: Origin (seed, user, llm-derived)
├── tags: Searchable labels
├── use_count: How often it's been retrieved
└── timestamps: created_at, updated_at
```

**Use Cases:**
- "What's the BANT qualification framework?"
- "How do I calculate position sizing?"
- "What are the rules for stop-loss placement?"

**Characteristics:**
- Upsert semantics (same key updates existing)
- Confidence-weighted retrieval
- Tag-based search
- Use-count tracking for popularity
- Seeded with domain knowledge on first run

---

### 3. Working Memory

**Purpose:** Maintains current session context for coherent multi-turn conversations.

**Structure:**
```
Working Memory (per session)
├── session_id: Session identifier
├── entries: Ordered list of recent interactions
│   ├── query: User message
│   ├── response: Agent response
│   └── timestamp: When it occurred
└── max_size: Configurable limit (default: 20)
```

**Use Cases:**
- "What did I just ask about?"
- "Reference the previous answer"
- "Maintain context across a long conversation"

**Characteristics:**
- In-memory only (volatile, not persisted)
- LRU eviction when max size reached
- Cleared when session ends
- Fastest access (no database query)

---

## Retrieval Strategy

### Multi-Stage Pipeline

```
Query
  │
  ▼
┌─────────────────────┐
│ 1. Keyword Matching │ ← Fast, always runs
│    (BM25-like)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 2. Candidate Filter │ ← Remove low-relevance
│    (threshold 0.1)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌──────────────┐
│ 3. LLM Re-ranking   │ ←── │ Only if LLM  │
│    (semantic match) │     │ available    │
└──────────┬──────────┘     └──────────────┘
           │
           ▼
┌─────────────────────┐
│ 4. Recency Weighting│ ← Time-decay factor
│    (optional)       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ 5. Top-K Selection  │ ← Return best matches
│    (default: 5)     │
└─────────────────────┘
```

### Keyword Matching

The keyword matcher uses a simplified BM25-like scoring:

1. Extract meaningful keywords (remove stop words)
2. Count matches in target text
3. Normalize by query keyword count
4. Multiply by stored confidence

```python
score = (matching_keywords / total_keywords) * stored_confidence
```

### LLM Re-ranking

When the LLM is available, top candidates are re-scored:

1. Send query + candidate text to LLM
2. Ask for relevance score (0-1)
3. Combine with keyword score: `final = keyword * 0.4 + llm * 0.6`

This provides semantic understanding beyond keyword overlap.

### Confidence Scoring

Each retrieval result includes a confidence score:

| Source | Base Score | Notes |
|--------|-----------|-------|
| Semantic (seeded) | 0.8-0.95 | High confidence for curated knowledge |
| Semantic (user-added) | 0.5-0.9 | Depends on user-specified confidence |
| Episodic (with outcome) | 0.7-1.0 | Outcome-validated interactions |
| Episodic (no outcome) | 0.5-0.8 | Unvalidated interactions |

---

## Memory Lifecycle

### Creation

```
User Query
    │
    ▼
Agent processes query
    │
    ▼
Response generated
    │
    ▼
Episodic memory created
(query + response + metadata)
    │
    ▼
Working memory updated
```

### Retrieval

```
New Query
    │
    ▼
Keyword search → candidates
    │
    ▼
LLM rerank (if available)
    │
    ▼
Top-K results → context for response
    │
    ▼
Semantic memories increment use_count
```

### Feedback Loop

```
User receives response
    │
    ▼
User provides outcome feedback
    │
    ▼
Episodic memory updated
(outcome + outcome_score)
    │
    ▼
Future retrievals use outcome data
to weight similar situations
```

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Episodic store | <5ms | Single INSERT |
| Semantic store | <5ms | INSERT or UPDATE |
| Keyword retrieval | <10ms | Indexed columns |
| LLM reranking | ~800ms | Per candidate |
| Working memory | <1ms | In-memory |

### Optimization Strategies

1. **Indexes** on session_id, module, created_at
2. **WAL Mode** for concurrent reads during writes
3. **Connection Pooling** to reuse connections
4. **Query Limiting** to prevent large result sets
5. **In-Memory Working Memory** for session context

---

## Data Retention

| Type | Default Limit | Behavior |
|------|--------------|----------|
| Episodic | 10,000 | Oldest pruned when limit reached |
| Semantic | Unlimited | Grows with added knowledge |
| Working | 20 per session | LRU eviction |

---

## Future Enhancements

1. **Embedding-Based Retrieval** — Use sentence-transformers for true semantic search
2. **Memory Consolidation** — Periodically summarize episodic into semantic
3. **Forgetting Curve** — Reduce relevance of unused memories over time
4. **Cross-Session Learning** — Identify patterns across sessions
5. **Memory Graph** — Link related memories for graph traversal
