---
description: Add a note to a contact. Use when a user says "Mark got promoted" or "remind me that Lisa is training for a marathon" or "note about Mark: ...".
---

# Add Note

## When to Use
When a user wants to record information about a contact — life updates, conversation topics, things to remember.

## Steps

1. **Identify the user** — Get CURRENT_USER Telegram ID for `created_by`
2. **Identify the contact** — Search by name: GET `/api/search?q={name}`
   - If multiple matches, ask which one
   - If no match, ask if they want to create a new contact first
3. **Extract the note content** — Parse what the user said about this person
4. **Save the note** — POST `/api/contacts/{id}/notes` with note_text and created_by
5. **Confirm** — "Got it. Added note to Mark: 'Got promoted at work.'"

## API Calls

```bash
# Find the contact
curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/search?q=Mark"

# Add the note
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/{id}/notes \
  -d '{"note_text": "Got promoted at work", "created_by": "12345"}'
```

## Rules
- Notes are attributed to whoever added them
- Keep the note text close to what the user said — don't over-edit
- If the user mentions multiple people in one message, create separate notes for each
