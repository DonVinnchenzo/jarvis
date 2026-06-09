---
description: Add a new contact to the Social Circle. Use when a user says something like "add my friend Mark" or "Mark's birthday is June 14".
---

# Add Contact

## When to Use
When a user wants to add a new person, update an existing contact, or add events/children to a contact.

## Steps

1. **Identify the user** — Check CURRENT_USER from the system prompt. Record their Telegram user ID as `created_by`.
2. **Parse the request** — Extract from the user's message:
   - Name (required)
   - Relationship type (friend/family/colleague/custom) — ask if not provided
   - Birthday (day + month, year optional) — ask if not mentioned
   - Anniversary (if mentioned, including partner name)
   - Children (names, birthdays if mentioned)
   - Notes (any context like "just got promoted", "training for marathon")
   - Visibility: shared (default) or personal
3. **Check for duplicates** — GET `/api/search?q={name}` to see if a contact with a similar name exists. If yes, confirm with the user: "There's already a contact named Mark. Did you mean to update them, or is this a different person?"
4. **Create the contact** — POST `/api/contacts` with name, relationship_type, created_by, visibility
5. **Add events** — For each birthday/anniversary: POST `/api/contacts/{id}/events`
6. **Add children** — For each child: POST `/api/contacts/{id}/children`, then POST `/api/contacts/{id}/events` with event_type=child_birthday
7. **Add notes** — For any context mentioned: POST `/api/contacts/{id}/notes`
8. **Confirm** — Reply with a summary of what was created: "Added Mark (friend). Birthday: June 14. Note: just got promoted."

## API Calls

```bash
# Search for duplicates
curl -s -H "X-API-Key: $JARVIS_API_KEY" http://localhost:8000/api/search?q=Mark

# Create contact
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts \
  -d '{"name": "Mark", "relationship_type": "friend", "created_by": "12345"}'

# Add birthday event
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/{id}/events \
  -d '{"event_type": "birthday", "day": 14, "month": 6}'

# Add note
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/{id}/notes \
  -d '{"note_text": "Just got promoted at work", "created_by": "12345"}'
```

## Rules
- ALWAYS check for duplicates before creating
- ALWAYS record created_by with the current user's Telegram ID
- If the user provides partial info, create what you have and note what's missing — don't block on optional fields
- Default visibility is "shared" — only set "personal" if the user explicitly asks
