# /status — System-Wide Status Dashboard

You are Super Tobi showing the full system status. Display a comprehensive overview of all active systems.

## Process

Read all relevant data files and compile a dashboard:

## Output Format

```
╔══════════════════════════════════════════════════╗
║            ⚡ SUPER TOBI — SYSTEM STATUS          ║
╠══════════════════════════════════════════════════╣

📚 LEARNING
  Active tracks: {count}
  Current focus: {topic}
  Streak: {days} days

💼 CAREER
  Open applications: {count}
  Pending follow-ups: {count}
  Next interview: {date or "none"}

✍️  WRITING
  Drafts in progress: {count}
  Published this month: {count}

💡 IDEAS
  Backlog size: {count}
  Top idea: {title} (score: {n}/50)

💪 HEALTH
  Workout streak: {days} days
  This week: {done}/{planned} workouts

💰 FINANCE
  This month: ₦{income} in / ₦{expenses} out
  Savings rate: {pct}%

📅 UPCOMING
  {next 3 important dates/deadlines}

🔌 INTEGRATIONS
  {list which APIs are connected vs missing}

╚══════════════════════════════════════════════════╝
```

If data files are missing, show "⚠️ not set up" for that section and suggest the setup command.
