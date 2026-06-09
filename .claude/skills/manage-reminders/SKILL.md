---
description: Configure reminder preferences. Use when a user says "remind me earlier", "change reminder timing", "stop reminders for X", etc.
---

# Manage Reminders

## When to Use
When a user wants to change how or when reminders are sent.

## Steps

1. **Understand the request** — What does the user want to change?
   - Global timing (e.g., "remind me 14 days before instead of 7")
   - Disable/enable reminders
   - Check current settings
2. **Show current config** — GET `/api/reminders/config`
3. **Apply changes** — POST `/api/reminders/config` with updated settings
4. **Confirm** — Show the updated configuration

## API Calls

```bash
# Get current config
curl -s -H "X-API-Key: $JARVIS_API_KEY" http://localhost:8000/api/reminders/config

# Update config
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/reminders/config \
  -d '{"days_before": 14, "enabled": true}'
```

## Rules
- In v1, only global defaults can be changed (no per-event overrides)
- Both users share the same reminder config
- Default: 7 days, 1 day, and day-of (0 days) before each event
