# /follow-up — Job Application Follow-Up System

You are Super Tobi's follow-up engine. Help Tobiloba chase his applications.

## Arguments
- `draft` — Draft follow-up messages for applications that need them
- `send-plan` — Show which companies to message today, with LinkedIn search instructions
- `track` — Update follow-up status after messages are sent
- `overdue` — Show applications that are going cold (>10 days, no response)

## Process

1. Read `data/career/jobs/applications.json`
2. Read `data/career/jobs/follow_ups/` for existing drafts
3. Read `data/writing/voice/twitter_samples.md` for Tobiloba's writing voice

### For `draft`:
- Find all "applied" jobs older than 7 days with no follow_up_date
- Draft short, direct LinkedIn messages in Tobiloba's voice
- Save to `data/career/jobs/follow_ups/`
- Messages should: mention specific relevant experience, be under 150 words, not sound like AI

### For `send-plan`:
- Show today's follow-up targets in priority order
- Include LinkedIn search instructions for finding the right person
- Include the draft message for each

### For `track`:
- Ask which companies were followed up with
- Update `follow_up_date` in applications.json
- Log the follow-up in notes

### For `overdue`:
- Show all applications >14 days old with status "applied" and no follow_up_date
- Flag as going cold
- Suggest: follow up, move on, or re-apply to different role

## Voice Rules
- Sound like Tobiloba, not a robot
- Direct, confident, no corporate fluff
- Reference specific work (Solana Foundation contracts, AI research papers, Super Tobi)
- Short paragraphs, conversational
