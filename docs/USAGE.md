# Usage Guide

## Getting Started

### Start the Server

```bash
# From the project directory
python -m athena

# Or with custom settings
ATHENA_PORT=9000 ATHENA_LLM_MODEL=llama3.1 python -m athena
```

The dashboard will be available at `http://localhost:8585`.

### First Run

On first launch, Athena will:
1. Initialize the SQLite database
2. Seed the knowledge base with sales and trading facts
3. Attempt to connect to the LLM service
4. Start the web server

## Dashboard Navigation

The sidebar provides access to all views:

| View | Shortcut | Description |
|------|----------|-------------|
| Dashboard | — | Overview with real-time stats |
| Chat | — | Conversation interface |
| Memory | — | Browse stored memories |
| Decisions | — | View decision history |
| Knowledge | — | Browse knowledge base |
| Integrations | — | Configure webhooks/connectors |
| Training | — | Submit feedback |
| System | — | Machine monitoring |
| Settings | — | Configuration |

## Chat Interface

### Basic Usage
1. Select a module context (General, Sales, Trading)
2. Type your message
3. Press Enter or click Send
4. View the response with confidence score

### Module Contexts

| Module | Best For |
|--------|----------|
| General | Business decisions, general advisory |
| Sales | Sales strategy, objection handling, closing |
| Trading | Risk management, technical analysis, portfolio |

### Tips
- Use Shift+Enter for multi-line messages
- Switch modules mid-conversation for different contexts
- Click "New Chat" to start a fresh session
- Responses include confidence scores and memory usage

## Memory Browsing

### Episodic Memory
View past interactions filtered by:
- Session ID
- Module context
- Time range

### Semantic Memory
Browse knowledge facts filtered by:
- Module (sales/trading/general)
- Category
- Search keywords

### Working Memory
View recent context for active sessions.

## Decision History

The Decisions page shows:
- Context of each decision
- Options considered
- Selected option with confidence
- Reasoning and evidence

## Knowledge Base

### Browsing
- Search across all knowledge entries
- Filter by category
- View confidence levels and usage counts

### Adding Knowledge
1. Click "Add Knowledge"
2. Select module and category
3. Enter key and value
4. Set confidence level
5. Add optional tags

## Training the Agent

### Submitting Feedback
1. Navigate to Training → Response Feedback
2. Select a response to rate
3. Choose rating (1-5)
4. Add correction if needed
5. Submit

### Running Adaptation
1. Collect sufficient feedback (10+ ratings)
2. Click "Run Adaptation"
3. Review generated rules
4. Future responses will incorporate learnings

### Replaying Sessions
1. Click "Replay Session"
2. Select a session to replay
3. Compare original vs improved responses

## System Monitoring

The System page provides real-time visibility into:
- CPU usage (overall and per-core)
- RAM and swap usage
- Disk space per mount point
- Network I/O
- Process count and uptime

Charts update every 5 seconds via WebSocket.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+K | Focus search |
| Escape | Close modal |
| Enter | Send message (in chat) |
| Shift+Enter | New line (in chat) |

## Configuration

### Environment Variables

```bash
# Server
ATHENA_HOST=0.0.0.0
ATHENA_PORT=8585

# LLM
ATHENA_LLM_BASE_URL=http://localhost:11434/v1
ATHENA_LLM_MODEL=llama3.2
ATHENA_LLM_TIMEOUT=30

# Database
ATHENA_DB_PATH=./data/athena.db

# Security
ATHENA_RATE_LIMIT=100
ATHENA_MAX_INPUT_LENGTH=10000

# Logging
ATHENA_LOG_LEVEL=INFO
```

### Settings Page
Most settings can also be configured through the web UI at Settings.

## API Access

For programmatic access, use the REST API:

```bash
# Chat
curl -X POST http://localhost:8585/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "module": "general"}'

# Health check
curl http://localhost:8585/api/v1/health

# System metrics
curl http://localhost:8585/api/v1/system/metrics
```

See [API.md](API.md) for full reference.

## Troubleshooting

### LLM Not Connecting
1. Verify Ollama is running: `ollama serve`
2. Check model is pulled: `ollama pull llama3.2`
3. Verify base URL in settings

### Dashboard Not Loading
1. Check server is running
2. Clear browser cache
3. Check browser console for errors

### High Memory Usage
1. Check System page for metrics
2. Clear old episodic memories
3. Reduce working memory size in settings

### WebSocket Disconnected
1. Check network connectivity
2. Verify no proxy blocking WebSocket
3. Check server logs for errors
