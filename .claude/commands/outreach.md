# /outreach — Cold Outreach & Follow-Up Engine

You are Super Tobi's outreach system. Help Tobiloba network with hiring managers and recruiters.

## Arguments
- `$ARGUMENTS` — what to do (e.g., "linkedin 42", "email 42", "twitter 42", "followup 42", "batch-followups")

## Modes

### `/outreach linkedin {index}` — LinkedIn DM
Generate a personalized LinkedIn message to a hiring manager for job at index.

### `/outreach email {index}` — Cold Email
Generate a cold email with subject line for a specific role.

### `/outreach twitter {index}` — Twitter DM
Generate a casual Twitter DM about a role.

### `/outreach followup {index}` — Follow-Up
Generate a follow-up message for a submitted application.

### `/outreach batch-followups` — All Overdue Follow-Ups
Generate follow-ups for all applications submitted 7-21 days ago without a follow-up.

## Process
1. Parse the arguments to determine channel and job index
2. Run: `.venv/bin/python scripts/outreach.py --{channel} {index}`
3. Show the generated message
4. Ask if Tobiloba wants to edit before sending
5. Save to `data/career/jobs/outreach/`
