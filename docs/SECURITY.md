# Security Considerations

## Threat Model

Athena is designed for single-user, local deployment. It is not intended for multi-user or internet-facing deployments without additional hardening.

## Input Validation

### All User Inputs Are:

1. **Length-Limited** — Max 10,000 characters per message
2. **HTML-Escaped** — Prevents XSS in stored data
3. **Null-Byte Stripped** — Prevents injection attacks
4. **Whitespace-Normalized** — Prevents padding attacks
5. **Pattern-Checked** — SQL injection detection

```python
# Example: How inputs are sanitized
from athena.utils.security import sanitize_input

safe_text = sanitize_input(user_input)  # Always sanitize
```

### Validation Layers

| Layer | What It Checks |
|-------|---------------|
| Pydantic Models | Type, length, format |
| Security Module | SQLi, XSS patterns |
| Module Validator | Allowed module names |
| DB Layer | Parameterized queries |

## SQL Injection Prevention

**All database queries use parameterized statements:**

```python
# SAFE — Parameterized
await db.execute(
    "SELECT * FROM memories WHERE id = ?",
    (memory_id,)
)

# NEVER DO THIS — String interpolation
await db.execute(f"SELECT * FROM memories WHERE id = {memory_id}")
```

The `check_sql_injection()` function provides additional detection:

```python
from athena.utils.security import check_sql_injection

if check_sql_injection(user_input):
    raise SecurityError("Suspicious input detected")
```

## XSS Prevention

1. **Input Sanitization** — HTML entities escaped
2. **Output Encoding** — Browser renders stored data safely
3. **Content Security Policy** — Ready for CSP headers
4. **No Inner HTML** — Frontend uses textContent where possible

## Rate Limiting

Built-in rate limiting prevents abuse:

```python
# Configuration
ATHENA_RATE_LIMIT=100  # requests per minute
```

Implementation uses token bucket algorithm per IP address.

## No Secrets in Logs

Sensitive data is never logged:

```python
# BAD — Never do this
logger.info(f"User login: {username}, password: {password}")

# GOOD — Sanitized logging
logger.info(f"User login attempt: {username}")
```

## WebSocket Security

- **Origin Validation** — Same-origin policy enforced
- **Connection Limits** — Max 10 concurrent connections
- **Message Size** — 1MB max per message
- **Rate Limiting** — Messages per second capped

## Data Protection

### At Rest
- SQLite database file (file system permissions)
- No encryption by default (add for sensitive deployments)
- WAL mode ensures crash consistency

### In Transit
- HTTP (default) — Suitable for localhost
- Add TLS for remote access (use reverse proxy)

### Sensitive Data Handling
- Session IDs are random UUIDs
- No PII stored by default
- Knowledge base is user-controlled

## Deployment Checklist

For production deployments:

- [ ] Use HTTPS (nginx/caddy reverse proxy)
- [ ] Set strong file permissions on database
- [ ] Enable rate limiting
- [ ] Run as non-root user
- [ ] Use firewall to restrict access
- [ ] Enable audit logging
- [ ] Regular database backups
- [ ] Update dependencies regularly

## Vulnerability Reporting

Report security issues to: security@athena-agent.dev

## Security Architecture

```
┌─────────────────────────────────────────┐
│           Input Validation              │
│  ┌─────────┐ ┌────────┐ ┌───────────┐ │
│  │ Length  │ │ XSS    │ │ SQLi      │ │
│  │ Check   │ │ Filter │ │ Detection │ │
│  └─────────┘ └────────┘ └───────────┘ │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           Processing Layer              │
│  ┌───────────────────────────────────┐  │
│  │     Parameterized Queries Only    │  │
│  └───────────────────────────────────┘  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│           Output Layer                  │
│  ┌─────────┐ ┌────────┐ ┌───────────┐ │
│  │ HTML    │ │ JSON   │ │ Rate      │ │
│  │ Escape  │ │ Encode │ │ Limited   │ │
│  └─────────┘ └────────┘ └───────────┘ │
└─────────────────────────────────────────┘
```
