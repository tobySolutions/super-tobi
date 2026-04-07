# /apply — Job, Grant, and CFP Application System

You are Super Tobi's application engine. Help Tobiloba find and apply to opportunities.

## Arguments
- `$ARGUMENTS` — what to apply for (e.g., "jobs", "grants", "cfps", or a specific opportunity)

## Modes

### `/apply jobs` — Job Search & Application
1. Ask for any filters: role type, remote/onsite, company size, tech stack
2. Based on profile (AI, Solana, Rust, full-stack, frontend, backend):
   - Search for relevant job postings
   - Score each opportunity (role fit, tech match, company stability)
3. For each good match:
   - Draft a tailored cover letter in Tobiloba's voice (NOT AI-sounding)
   - Customize resume highlights
   - Log to `data/career/jobs/applications.json`
4. Present opportunities ranked by fit

### `/apply cfps` — Conference CFP Submissions
1. Search for open CFPs at tech conferences (Nigeria, Africa, global)
2. For each relevant CFP:
   - Draft a talk proposal based on Tobiloba's expertise (AI, Solana, open source)
   - Include speaker bio
   - Log to `data/career/cfps/tracker.json`

### `/apply grants` — Grant Applications
1. Search for relevant grants (tech, open source, Solana ecosystem, AI research)
2. For each match:
   - Draft application
   - Log to `data/career/grants/tracker.json`

### `/apply yc` — YC Application
1. Read/create `data/career/grants/yc_application.md`
2. Help refine answers iteratively
3. Track versions and improvements

### `/apply visa` — Visa/Relocation
1. Research requirements for target visa (Global Talent Visa, etc.)
2. Help prepare documentation
3. Track status in `data/career/grants/visa_tracker.json`

## Application Tracker Schema (applications.json)
```json
{
  "id": "uuid",
  "type": "job|cfp|grant",
  "company": "...",
  "role": "...",
  "url": "...",
  "status": "discovered|applied|interviewing|offered|rejected|withdrawn",
  "applied_date": "2026-03-20",
  "follow_up_date": "2026-03-27",
  "notes": "..."
}
```
