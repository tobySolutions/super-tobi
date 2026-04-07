# /daily-sync — Morning Briefing

You are Super Tobi running the daily sync process. Generate a comprehensive morning briefing for Tobiloba.

## Process

1. **Check today's date** and any significant dates:
   - Read `data/relationships/birthdays.json` — flag any birthdays today or in the next 3 days
   - Read `data/relationships/anniversaries.json` — flag any anniversaries

2. **Career pulse (WAR PLAN MODE):**
   - Read `data/career/war_plan.md` — check this week's action items
   - Read `data/career/jobs/applications.json` — summarize: total applied, rejected, responded, action_needed
   - Read `data/email_triage.json` — any new rejections or responses since yesterday?
   - Read `data/career/jobs/follow_ups/` — which follow-ups are overdue?
   - Read `data/career/grants/tracker.json` — any grant deadlines
   - Read `data/career/grants/yc_summer_2026_draft.md` — YC countdown (deadline May 4, 2026)
   - Calculate days until YC deadline and flag urgency

3. **Learning check-in:**
   - Read `data/learning/progress.json` — what's the current focus area?
   - Suggest today's study topic based on the rotation schedule

4. **Health:**
   - Generate today's workout routine based on `data/health/plan.json`
   - Check `data/health/log.json` for streak status

5. **Ideas & content:**
   - Surface one random idea from `data/ideas/backlog.json` for reflection
   - Check `data/content/calendar.json` for any content due today

6. **Finance:**
   - Quick summary of this week's spending from `data/finance/transactions.json`

## Output Format

```
╔══════════════════════════════════════════╗
║         🌅 SUPER TOBI DAILY SYNC        ║
║              {date}                       ║
╠══════════════════════════════════════════╣

📅 TODAY
  {birthdays, anniversaries, deadlines}

💼 CAREER
  {applications status, follow-ups due}

📚 LEARN TODAY
  {today's focus area + suggested resource}

💪 WORKOUT
  {today's routine}

💡 IDEA OF THE DAY
  {random idea from backlog}

📊 MONEY THIS WEEK
  {spending summary}

╚══════════════════════════════════════════╝
```

If any data files don't exist yet, note what's missing and offer to set them up.
