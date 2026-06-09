---
description: Show upcoming events. Use when a user asks "what's coming up", "any birthdays this month", "what's happening next week", etc.
---

# Upcoming Events

## When to Use
When a user wants to see what events are coming up in the near future.

## Steps

1. **Parse the timeframe** — Default 30 days. Adjust if user says "this week" (7), "this month" (30), "next 2 weeks" (14), etc.
2. **Fetch events** — GET `/api/upcoming?days={N}`
3. **Filter by visibility** — Only show personal items to their creator
4. **Format the response** — Group by week or date:
   - Date + day name
   - Event description (whose birthday, which anniversary)
   - Days until the event
   - Recent notes for that contact (if any, last 1-2)
5. **If nothing upcoming** — "Nothing in the next {N} days. Your next event is {X} on {date}."

## API Calls

```bash
curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/upcoming?days=30"
```

## Rules
- Always show how many days until each event
- Include contact notes in the response for context — this is what makes Jarvis an assistant, not a calendar
- Sort by date ascending
