# Training Guide

## Overview

Athena's training system lets you improve agent performance through feedback collection, session replay, and behavioral adaptation.

## How It Works

1. **Interact** — Chat with the agent through the dashboard
2. **Rate** — Rate responses (1-5 stars) and provide corrections
3. **Adapt** — Run adaptation to improve future responses
4. **Replay** — Replay past sessions with improved context

## Submitting Feedback

### Via Dashboard
1. Navigate to the Training page
2. Select a response to rate
3. Choose a rating (1-5)
4. Optionally add a correction
5. Click Submit

### Via API

```bash
curl -X POST http://localhost:8585/api/v1/training/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "memory_id": 42,
    "rating": 4,
    "correction": "Include BANT framework in response",
    "comment": "Good but incomplete",
    "category": "sales_methodology"
  }'
```

### Rating Scale

| Rating | Meaning |
|--------|---------|
| 1 | Poor — Response was incorrect or unhelpful |
| 2 | Below Average — Needs significant improvement |
| 3 | Average — Acceptable but could be better |
| 4 | Good — Minor improvements possible |
| 5 | Excellent — Perfect response |

## Feedback Categories

| Category | Use For |
|----------|---------|
| `sales_methodology` | Sales technique responses |
| `trading_analysis` | Trading analysis responses |
| `general_knowledge` | General knowledge responses |
| `objection_handling` | Objection handling responses |
| `risk_management` | Risk-related responses |

## Viewing Feedback History

### Dashboard
Navigate to Training → Response Feedback to see all submitted feedback.

### API

```bash
curl http://localhost:8585/api/v1/training/history
curl http://localhost:8585/api/v1/training/stats
```

## Statistics

The Training Stats panel shows:
- Total feedback submitted
- Average rating across all feedback
- Number of corrections provided
- Category and module distribution

## Session Replay

Replay past sessions with the current (improved) system to verify improvements:

```bash
curl -X POST http://localhost:8585/api/v1/training/replay/sess_abc123
```

Response:
```json
{
  "session_id": "sess_abc123",
  "replayed": 10,
  "improved": 3
}
```

## Adaptation

Adaptation analyzes feedback patterns and generates rules to improve future behavior:

```bash
curl -X POST http://localhost:8585/api/v1/training/adapt
```

Response:
```json
{
  "rules_generated": 2,
  "adaptations": {
    "total_rules": 5,
    "applied": 3,
    "skipped": 2
  },
  "stats": {
    "total_rules": 5,
    "total_adaptations": 12,
    "modules_covered": 3,
    "avg_confidence": 0.72
  }
}
```

## Adaptation Rules

Rules are generated from patterns in low-rated feedback:

| Pattern | Action |
|---------|--------|
| Low ratings in sales module | Review and improve sales responses |
| Low ratings in trading module | Review and improve trading responses |
| Common corrections for category | Prioritize improvement in category |

## Best Practices

1. **Rate consistently** — Submit feedback for every response
2. **Be specific** — Add detailed corrections, not just low ratings
3. **Use categories** — Categorize feedback for better adaptation
4. **Review regularly** — Check stats weekly to track improvement
5. **Replay sessions** — Verify improvements by replaying old sessions
6. **Adapt periodically** — Run adaptation after collecting sufficient feedback

## Integration with Webhooks

Training events trigger webhooks when configured:

```bash
# Register webhook for training events
curl -X POST http://localhost:8585/api/v1/integrations/webhooks \
  -d '{"url": "https://your-service.com/training", "events": ["training.feedback"]}'
```

## Data Export

Export training data for analysis:

1. Navigate to Training → Export
2. Download as JSON or CSV
3. Analyze feedback patterns externally

## Limitations

- Adaptation rules are in-memory (not persisted across restarts)
- Replay requires the original session to exist in memory
- Feedback statistics are calculated from in-memory data only
