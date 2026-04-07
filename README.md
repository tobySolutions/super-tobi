# super-tobi

A personal operating system built on Claude Code.

```
$ /status

╔══════════════════════════════════════════╗
║         ⚡ SUPER TOBI — SYSTEM STATUS    ║
╠══════════════════════════════════════════╣
  💼 CAREER    34 applied · 3 interviews · 2 follow-ups overdue
  📚 LEARNING  system design (day 14) · streak: 8 days
  ✍️  WRITING   2 drafts · 1 published this week
  💪 HEALTH    4/5 workouts · upper body today
  💰 FINANCE   ₦245k in · ₦180k out · 26% saved
  💡 IDEAS     23 in backlog · top: "agent marketplace"
╚══════════════════════════════════════════╝
```

---

## What this is

I was using Claude Code for job applications. Then email triage. Then writing articles in my voice. Then tracking workouts, finances, learning goals, messages across 4 platforms. Each piece worked, but every new session started blank — all context gone.

So I stopped treating Claude like a conversation and started treating it like a runtime. Gave it a filesystem for state. Scripts for heavy lifting. A config file that defines who I am. Slash commands as the interface.

The result is an operating system:

- **`CLAUDE.md`** is the kernel — edit this file, the whole system changes
- **`.claude/commands/`** — 19 slash commands (the CLI)
- **`scripts/`** — 23+ Python programs (the daemons)
- **`data/`** — JSON + markdown files (the filesystem, no database)
- **`config/`** — settings + API keys
- **`logs/`** — append-only history

## Architecture

```
super-tobi/
├── CLAUDE.md                   # Kernel — identity, rules, voice, architecture
├── config/
│   ├── settings.yaml           # Preferences
│   └── api_keys.env            # Keys (gitignored)
├── .claude/commands/           # CLI — 19 commands
│   ├── status.md               # /status
│   ├── daily-sync.md           # /daily-sync
│   ├── apply.md                # /apply jobs|cfps|grants
│   ├── write.md                # /write {idea}
│   ├── learn.md                # /learn {topic}
│   ├── war-plan.md             # /war-plan
│   ├── analytics.md            # /analytics
│   ├── outreach.md             # /outreach
│   ├── interview-prep.md       # /interview-prep
│   ├── health.md               # /health
│   ├── finance.md              # /finance
│   ├── twitter.md              # /twitter
│   ├── ideas.md                # /ideas
│   ├── messages.md             # /messages
│   ├── network.md              # /network
│   ├── remind.md               # /remind
│   ├── content.md              # /content
│   ├── follow-up.md            # /follow-up
│   └── mass-apply.md           # /mass-apply
├── scripts/                    # Daemons — 23+ Python
│   ├── job_hunter.py           # Scan boards, fetch JDs, score
│   ├── resume_tailor.py        # ATS keyword extraction, per-job CV
│   ├── auto_apply.py           # Browser automation (Playwright)
│   ├── analytics.py            # Funnel conversion, velocity
│   ├── outreach.py             # Cold emails, LinkedIn DMs, follow-ups
│   ├── interview_prep.py       # Mock interviews, answer coaching
│   ├── company_intel.py        # Glassdoor, Reddit, culture research
│   ├── email_triage.py         # Gmail categorization
│   ├── twitter_feed.py         # Twitter API (twitterapi.io)
│   ├── telegram_bot.py         # Mobile command interface
│   ├── cli.py                  # Rich terminal dashboard
│   ├── trading.py              # Market signals
│   ├── language_learn.py       # Hindi, Spanish, etc.
│   ├── entertainment.py        # Movie/music recommendations
│   ├── creative_aggregator.py  # Content ideas from trends
│   ├── message_aggregator.py   # Multi-platform inbox
│   ├── subscription_tracker.py # Track subscriptions
│   ├── tax_tracker.py          # Nigerian tax compliance
│   └── ...more
├── data/                       # State — files are the database
│   ├── career/jobs/            # Applications, JDs, follow-ups
│   ├── career/intel/           # Per-company research
│   ├── career/resume/          # Base + tailored resumes
│   ├── learning/               # Progress, plans, streaks
│   ├── writing/{drafts,voice}/ # Versioned drafts, voice samples
│   ├── health/                 # Workout logs
│   ├── finance/                # Income, expenses
│   ├── ideas/                  # Backlog with scoring
│   ├── relationships/          # Birthdays, contacts
│   └── content/                # Calendar, analytics
├── logs/                       # Append-only
└── life_systems_map_v1.md      # Master life goals
```

---

## Commands

| Command | What it does |
|---------|-------------|
| `/status` | Life dashboard — all domains at a glance |
| `/daily-sync` | Morning briefing: birthdays, career pipeline, workout, finance, YC countdown |
| `/apply jobs` | Find → score → tailor CV → apply → track |
| `/apply cfps` | Conference proposals |
| `/apply grants` | Grant applications |
| `/write {idea}` | Research → outline → draft in your voice → review |
| `/learn {topic}` | Learning plans, progress tracking, streaks, quizzes |
| `/war-plan` | Career offensive: 3 actions today, conversion rates, overdue follow-ups |
| `/analytics` | Application funnel, board performance, velocity, rejection analysis |
| `/outreach` | Cold LinkedIn/email/Twitter DMs, batch follow-ups |
| `/interview-prep` | Role-specific questions, mock interviews, answer coaching |
| `/health` | Workout plans, logging, streaks |
| `/finance` | Income, expenses, budgets |
| `/twitter` | Feed, mentions, trending, draft tweets |
| `/ideas` | Backlog with auto-scoring |
| `/messages` | Telegram + Discord + WhatsApp + email in one view |
| `/follow-up` | Chase overdue applications, emails, tasks |
| `/network` | Relationship management, recruiter outreach |
| `/remind` | Birthdays, deadlines, custom reminders |

---

## The Career Pipeline

The most battle-tested part. End-to-end autonomous job search:

```
Discovery → Scoring → Intel → Tailoring → Application → Outreach → Analytics → Interview Prep
```

| Stage | Script | What it does |
|-------|--------|-------------|
| Discovery | `job_hunter.py` | 10+ boards: RemoteOK, Web3Career, CryptoJobsList, Twitter/X, Big Tech career pages |
| Scoring | `job_hunter.py` | 0-100 on role fit, tech match, location, seniority, salary |
| Intel | `company_intel.py` | Reddit culture threads, Glassdoor reviews, interview prep via Brave Search |
| Tailoring | `resume_tailor.py` | ATS keyword extraction across 5 domains, per-job CV rewrite, before/after scoring |
| Application | `auto_apply.py` | Playwright browser automation with Greenhouse verification |
| Outreach | `outreach.py` | LinkedIn DMs, cold emails, Twitter DMs, batch follow-ups |
| Analytics | `analytics.py` | Funnel conversion, board performance, score distribution, velocity |
| Interview | `interview_prep.py` | AI-generated questions from actual JD, mock sessions, answer coaching |

The resume tailor is the one I'm proudest of. It extracts keywords from a job description, scores your current resume against it, then rewrites the resume to maximize ATS compatibility — per job, not generically. I've seen scores go from 38% to 84% on a single tailoring run.

```bash
.venv/bin/python scripts/job_hunter.py --hunt
.venv/bin/python scripts/resume_tailor.py --batch
.venv/bin/python scripts/auto_apply.py --max 10
.venv/bin/python scripts/outreach.py --batch-followups
.venv/bin/python scripts/analytics.py --full
.venv/bin/python scripts/interview_prep.py --prep 42
```

---

## Why files instead of a database

I tried Supabase. Spent two days setting it up. Then realized: Claude Code can't query Supabase. But it can read a JSON file, write markdown, and grep through a directory.

For a personal system with hundreds of files, the filesystem is the correct abstraction. Claude already knows how to navigate it. `git` gives you version control. Every file is human-readable. You can open `data/career/jobs/applications.json` on your phone and see exactly what the system knows.

---

## Fork your own

```bash
git clone https://github.com/tobySolutions/super-tobi.git my-os
cd my-os

python3 -m venv .venv
source .venv/bin/activate
pip install rich httpx requests playwright

# 1. Edit CLAUDE.md — this is YOUR kernel. Define who you are.
# 2. Edit config/settings.yaml
# 3. cp config/api_keys.env.example config/api_keys.env
# 4. Create life_systems_map_v1.md from the template
# 5. Open Claude Code. Type /status.
```

Step 1 is what matters. `CLAUDE.md` defines your identity, goals, voice, and rules. The scripts and commands work for anyone. The kernel makes it yours.

---

## Extending

**New command:** Create `.claude/commands/your-command.md` with a process spec. Read from `data/`, do work, write back.

**New script:** Create `scripts/your_script.py`. Same pattern — read files, call APIs, write results, log everything.

**New domain:** Create `data/your-domain/` and add it to `CLAUDE.md` so the system knows about it.

---

## Built with

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) · [Python](https://python.org) + [Rich](https://rich.readthedocs.io/) · [twitterapi.io](https://twitterapi.io) · [Google APIs](https://developers.google.com/) · [Telegram Bot API](https://core.telegram.org/bots) · [Playwright](https://playwright.dev/)

---

## License

MIT

---

**Tobiloba Adedeji** · AI Researcher at Idealik · Solana builder · Co-founder, Solana Students Africa

[@tobaboradev](https://x.com/tobaboradev) · [tobysolutions.dev](https://tobysolutions.dev) · [linkedin.com/in/tobiloba-adedeji](https://linkedin.com/in/tobiloba-adedeji)
