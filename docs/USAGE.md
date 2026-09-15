# Usage Guide

## Getting Started

### Starting the Server

```bash
# Start Athena
python -m athena run

# Or with custom settings
ATHENA_PORT=9000 python -m athena run
```

The dashboard is available at `http://localhost:8585`.

### First Interaction

1. Open the dashboard in your browser
2. Select a module (General, Sales, or Trading)
3. Type your question in the input box
4. Press Enter or click Send

## Using the Web Dashboard

### Module Selection

- **General** — Broad business and finance questions
- **Sales** — Sales strategy, negotiation, closing, pipeline
- **Trading** — Risk management, technical analysis, portfolio

### Chat Interface

- Type questions naturally
- Shift+Enter for multi-line input
- Click "+" to start a new session
- Click "×" to clear current chat

### Reading Responses

Each response includes:
- **The recommendation** — Actionable advice
- **Confidence badge** — How certain Athena is (0-100%)
- **"Rule-based" badge** — Shown when LLM is unavailable
- **Supporting evidence** — What knowledge informed the answer

## Using the API

### Python

```python
import httpx

# Chat
response = httpx.post("http://localhost:8585/api/v1/chat", json={
    "message": "How should I negotiate a $1M deal?",
    "module": "sales",
})
print(response.json()["response"])

# Make a decision
response = httpx.post("http://localhost:8585/api/v1/decisions", json={
    "context": "Client wants custom features",
    "options": ["Build custom", "Offer standard", "Phase the build"],
    "module": "sales",
})
print(response.json()["selected_option"])
```

### cURL

```bash
# Chat
curl -X POST http://localhost:8585/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Best closing technique?", "module": "sales"}'

# Health check
curl http://localhost:8585/api/v1/health

# List memories
curl http://localhost:8585/api/v1/memory/semantic?module=sales
```

### JavaScript

```javascript
// Chat
const response = await fetch('/api/v1/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        message: 'Position sizing for volatile stocks?',
        module: 'trading'
    })
});
const data = await response.json();
console.log(data.response);
```

## Using WebSocket (Real-time)

```javascript
const ws = new WebSocket('ws://localhost:8585/ws');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'chat',
        payload: {
            message: 'How do I handle objections?',
            module: 'sales'
        }
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data);
};
```

## Providing Feedback

After receiving a response, you can provide outcome feedback:

```bash
curl -X POST http://localhost:8585/api/v1/feedback/42 \
  -H "Content-Type: application/json" \
  -d '{"outcome": "Deal closed successfully", "score": 0.9}'
```

This improves future recommendations by learning from outcomes.

## Adding Custom Knowledge

Add your own strategies and rules:

```bash
curl -X POST http://localhost:8585/api/v1/memory/semantic \
  -H "Content-Type: application/json" \
  -d '{
    "module": "sales",
    "category": "custom",
    "key": "acme_corp_strategy",
    "value": "For Acme Corp, always involve the CTO early. They value technical validation.",
    "confidence": 0.9,
    "tags": ["acme", "enterprise", "ct-engagement"]
  }'
```

## Example Queries

### Sales

- "How do I handle price objections from enterprise procurement?"
- "What's the best way to create urgency without being pushy?"
- "How should I structure a $500K deal with milestone payments?"
- "What questions should I ask during discovery for a complex sale?"
- "How do I negotiate with a competitor already entrenched?"

### Trading

- "What's the optimal stop loss for a volatile tech stock?"
- "How do I size positions when correlation is high?"
- "What signals confirm a trend reversal?"
- "How should I allocate across sectors in a downturn?"
- "What risk management rules should I never break?"

### General

- "What's the rule of 72 and how do I apply it?"
- "How do I evaluate opportunity cost for a business decision?"
- "What are best practices for executive presentations?"

## Tips for Best Results

1. **Be specific** — "How do I close a $100K SaaS deal?" beats "How to sell?"
2. **Use the right module** — Switch between Sales/Trading for relevant expertise
3. **Provide context** — Include deal size, timeline, stakeholders when relevant
4. **Give feedback** — Mark outcomes to improve future recommendations
5. **Build knowledge** — Add your own playbooks and strategies over time

## Session Management

- Sessions auto-generate on first use
- Pass `session_id` to continue a conversation
- Working memory maintains context for 20 messages
- Episodic memory persists indefinitely

```python
# Continue a session
response = httpx.post("/api/v1/chat", json={
    "message": "Follow-up question...",
    "session_id": "sess_abc123"  # From previous response
})
```
