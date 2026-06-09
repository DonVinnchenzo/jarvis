---
description: Add a note to a contact. Use when a user says "Mark got promoted", "remind me that Lisa is training for a marathon", "note about Mark: ...", "remember that...", "Tom mentioned he's moving", or any life update about a person.
---

# Add Note

## When to Use
When a user wants to record information about a contact — life updates, conversation topics, things to remember. Users often won't say "add a note" — they'll just mention something about someone. Claude should recognize this as a note.

## Pattern Recognition

These are ALL note-worthy statements — Claude should offer to save them:
- "Mark got promoted" → note on Mark
- "Lisa mentioned she's looking for a new house" → note on Lisa
- "We had dinner with Tom and Sarah last week, Tom is changing jobs" → note on Tom
- "Remember that Emma has a peanut allergy" → note on Emma (or Emma's parent contact)
- "Christianne's mom is having surgery next month" → note (may be personal visibility)

If the user mentions something about a person but doesn't explicitly ask to save it, Claude should ask: "Want me to save that as a note on Mark's profile?"

## Steps

1. **Identify the user** — Get CURRENT_USER Telegram ID for `created_by`
2. **Identify the contact** — Search by name: GET `/api/search?q={name}`
   - If multiple matches, ask which one
   - If no match, ask if they want to create a new contact first
3. **Extract the note content** — Parse what the user said about this person
4. **Determine visibility** — Default "shared". If the note is clearly personal (health, private matter the user might not want shared), ask: "Should both you and {other person} see this, or just you?"
5. **Save the note** — POST `/api/contacts/{id}/notes` with note_text, created_by, and visibility
6. **Confirm briefly** — "Got it, saved to Mark's profile." Don't over-confirm.

## API Calls

```bash
# Find the contact
curl -s -H "X-API-Key: $JARVIS_API_KEY" "http://localhost:8000/api/search?q=Mark"

# Add the note
curl -s -X POST -H "X-API-Key: $JARVIS_API_KEY" -H "Content-Type: application/json" \
  http://localhost:8000/api/contacts/{id}/notes \
  -d '{"note_text": "Got promoted at work", "created_by": "12345", "visibility": "shared"}'
```

## Rules
- Notes are attributed to whoever added them
- Keep the note text close to what the user said — don't over-edit or formalize
- If the user mentions multiple people in one message, create separate notes for each
- Default visibility is "shared" — only ask about personal if the content seems private
- Don't ask for confirmation before saving unless the intent is ambiguous. "Mark got promoted" is unambiguous — just save it.
