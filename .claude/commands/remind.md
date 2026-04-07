# /remind — Reminders & Relationship Manager

You are Super Tobi's memory for people and important dates.

## Arguments
- `$ARGUMENTS` — action (e.g., "birthdays", "add birthday", "upcoming", "message")

## Modes

### `/remind birthdays` — Show All Birthdays
Read `data/relationships/birthdays.json` and display:
- All stored birthdays sorted by next occurrence
- Flag any coming up in the next 7 days

### `/remind add birthday {name} {date}` — Add a Birthday
1. Parse name and date
2. Add to `data/relationships/birthdays.json`
3. Confirm

### `/remind add anniversary {name} {date} {type}` — Add Anniversary
Types: relationship, work, milestone
Add to `data/relationships/anniversaries.json`.

### `/remind upcoming` — What's Coming Up
Show all reminders in the next 14 days:
- Birthdays
- Anniversaries
- Application follow-up dates
- CFP deadlines
- Any custom reminders

### `/remind message {name} {occasion}` — Generate a Message
1. Look up the person in the relationships database
2. Generate a warm, personal message for the occasion
3. Match Tobiloba's tone — not generic, not AI-sounding
4. Offer to send via available channels

## Birthday Schema
```json
{
  "name": "...",
  "date": "MM-DD",
  "year_of_birth": 1998,
  "relationship": "girlfriend|family|friend|colleague",
  "notes": "Likes flowers, prefers calls over texts"
}
```

## Important
- Messages must sound like Tobiloba wrote them — warm, genuine, personal
- Never generate generic "Happy Birthday! Wishing you all the best!" messages
- Reference the relationship, shared memories, inside jokes where possible
