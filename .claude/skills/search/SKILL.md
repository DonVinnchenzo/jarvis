---
description: Search contacts, notes, and events. Use when a user asks "who is...", "find...", "what do we know about...", or any lookup query.
---

# Search

## When to Use
When a user wants to find a contact, look up notes, or search for information about someone.

## Steps

1. **Parse the query** — Extract the search term from the user's message
2. **Call the search API** — GET `/api/search?q={term}`
3. **Filter by visibility** — If results include personal items, only show items where `created_by` matches CURRENT_USER or `visibility` is "shared"
4. **Format the response** — Show results grouped by contact:
   - Contact name + relationship
   - Upcoming events (if any)
   - Recent notes (last 3, with who added them and when)
   - Children (if any)
5. **If no results** — Suggest similar names or broader search terms

## API Calls

```bash
curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/search?q=Mark"
```

## Rules
- Respect visibility: never show personal items to the other user
- Show who added each note ("Added by Christianne, 2 weeks ago")
- Keep output concise — summarize, don't dump raw data
