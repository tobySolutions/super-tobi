# super-tobi

**A personal operating system built on Claude Code.**

```
$ super status

╔══════════════════════════════════════════╗
║         ⚡ SUPER TOBI — SYSTEM STATUS    ║
╠══════════════════════════════════════════╣
  💼 CAREER    12 applied · 3 interviews · 2 follow-ups due
  📚 LEARNING  system design (day 14) · streak: 8 days
  ✍️  WRITING   2 drafts · 1 published this week
  💪 HEALTH    4/5 workouts · upper body today
  💰 FINANCE   ₦245k in · ₦180k out · 26% saved
  💡 IDEAS     23 in backlog · top: "agent marketplace"
╚══════════════════════════════════════════╝
```

Super Tobi is a **personal AI operating system** — not a chatbot, not an assistant, not a wrapper. It's a filesystem-native system of agents, scripts, automations, and data that runs your life through Claude Code.

The `CLAUDE.md` file is the kernel. Slash commands are the CLI. Python scripts are the daemons. Your data is files and folders. Claude is the runtime.

---

## Why this exists

I was using Claude Code for coding. Then I started using it for job applications. Then content writing. Then email triage. Then tracking finances. Then managing my learning schedule.

At some point I realized: I wasn't using an AI assistant — I was building an **operating system**.

The problem with AI assistants is that they're stateless. You start a conversation, get an answer, close the tab. Nothing persists. Nothing connects. Nothing runs in the background.

Super Tobi is the opposite:
- **State lives in files.** Job applications are JSON. Drafts are versioned markdown. Health logs are append-only.
- **Agents run as processes.** The job hunter, email triager, and content writer are independent scripts that can run on schedules.
- **Commands are composable.** `/apply jobs` → `/write cover-letter` → `/follow-up` is a pipeline, not three separate conversations.
- **Everything is auditable.** Logs, session history, application records — you can trace every decision the system made.

---

## Architecture

```
super-tobi/
├── CLAUDE.md                 # The kernel — identity, rules, architecture
├── config/
│   ├── settings.yaml         # Global preferences
│   └── api_keys.env          # API keys (gitignored)
│
├── .claude/commands/         # Slash commands (the CLI)
│   ├── status.md             #   /status — system dashboard
│   ├── daily-sync.md         #   /daily-sync — morning briefing
│   ├── apply.md              #   /apply — job/grant/CFP applications
│   ├── write.md              #   /write — auto-writer pipeline
│   ├── learn.md              #   /learn — learning system
│   ├── health.md             #   /health — fitness tracking
│   ├── finance.md            #   /finance — money tracking
│   ├── twitter.md            #   /twitter — feed & posting
│   ├── ideas.md              #   /ideas — idea backlog
│   ├── messages.md           #   /messages — multi-platform inbox
│   ├── network.md            #   /network — relationship management
│   ├── remind.md             #   /remind — reminders
│   ├── content.md            #   /content — content calendar
│   ├── war-plan.md           #   /war-plan — career offensive
│   ├── follow-up.md          #   /follow-up — chase pending items
│   └── mass-apply.md         #   /mass-apply — batch applications
│
├── scripts/                  # Python daemons & utilities
│   ├── cli.py                #   Rich-powered terminal dashboard
│   ├── job_hunter.py         #   Auto job discovery & application
│   ├── email_triage.py       #   Gmail categorization & surfacing
│   ├── twitter_feed.py       #   Twitter API integration
│   ├── telegram_bot.py       #   Telegram command interface
│   ├── trading.py            #   Market data & signals
│   ├── entertainment.py      #   Movie/music recommendations
│   ├── language_learn.py     #   Language learning sessions
│   ├── company_intel.py      #   Company research for applications
│   ├── creative_aggregator.py #  Content ideas from trends
│   ├── message_aggregator.py  #  Multi-platform message inbox
│   ├── subscription_tracker.py # Track subscriptions & costs
│   ├── tax_tracker.py        #   Tax compliance (Nigeria)
│   └── ...20+ more
│
├── data/                     # All state (files = database)
│   ├── career/
│   │   ├── jobs/             #   Application tracker, follow-ups
│   │   ├── cfps/             #   Conference proposals
│   │   └── grants/           #   Grant applications, YC draft
│   ├── learning/             #   Progress, plans, streaks
│   ├── writing/
│   │   ├── drafts/           #   Versioned drafts (v1, v2, v3…)
│   │   ├── research/         #   Source material
│   │   └── voice/            #   Writing samples for voice training
│   ├── health/               #   Workout logs, plans
│   ├── finance/              #   Income, expenses, budgets
│   ├── ideas/                #   Startup/product idea backlog
│   ├── content/              #   Content calendar, analytics
│   ├── relationships/        #   Birthdays, contacts
│   └── trends/               #   Aggregated market/industry trends
│
├── processes/                # Running process definitions
├── logs/                     # Append-only system logs
└── life_systems_map_v1.md    # Master life goals document
```

---

## The Slash Command System

Every command is a markdown file in `.claude/commands/` that defines how Claude should behave when you type it. They're not prompts — they're **system definitions** with data flows, output formats, and error handling.

| Command | What it does |
|---------|-------------|
| `/status` | Full system dashboard — all domains at a glance |
| `/daily-sync` | Morning briefing — birthdays, career pipeline, workout, finance |
| `/apply jobs` | Find jobs, score fit, tailor CV, draft cover letter, track |
| `/apply cfps` | Find conferences, draft talk proposals |
| `/apply grants` | Find grants, draft applications |
| `/write {idea}` | Full writing pipeline — research → outline → draft → review |
| `/learn {topic}` | Create learning plan, track progress, generate exercises |
| `/learn quiz {topic}` | Knowledge check targeting weak areas |
| `/health log` | Log workout, track streak |
| `/finance track` | Log income/expenses, show budget |
| `/twitter feed` | Pull mentions, trending topics, own tweet performance |
| `/ideas add {idea}` | Add to backlog with auto-scoring |
| `/war-plan` | Career offensive — daily action items, pipeline health, YC countdown |
| `/follow-up` | Chase overdue applications, emails, tasks |
| `/messages` | Aggregate Telegram, Discord, WhatsApp, email |

---

## The Script Layer

Scripts are Python programs that do the heavy lifting. They can run standalone, on cron schedules, or be invoked by slash commands.

```bash
# Terminal dashboard
.venv/bin/python scripts/cli.py status

# Pull Twitter feed
.venv/bin/python scripts/twitter_feed.py --full

# Triage emails
.venv/bin/python scripts/email_triage.py

# Discover job opportunities
.venv/bin/python scripts/job_hunter.py --scan

# Run as macOS daemons (launchd)
launchctl load scripts/com.supertobi.daemon.plist
```

---

## Setup — Fork Your Own

### 1. Fork & clone

```bash
git clone https://github.com/tobySolutions/super-tobi.git my-super
cd my-super
```

### 2. Create your virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install rich httpx requests playwright
```

### 3. Set up your identity

Edit `CLAUDE.md` — replace Tobiloba's identity with yours. This is the most important file. It defines:
- Who you are
- What you're optimizing for
- How the system talks to you
- How it writes as you

Edit `config/settings.yaml` — your preferences, platforms, goals.

Copy `config/api_keys.env.example` to `config/api_keys.env` and add your keys:
```bash
TWITTER_API_KEY=your_key_here
TELEGRAM_BOT_TOKEN=your_token_here
GOOGLE_CALENDAR_CREDENTIALS=path_to_creds
```

### 4. Create your data directories

```bash
mkdir -p data/{career/jobs,career/cfps,career/grants,learning,writing/{drafts,research,voice},health,finance,ideas,content,relationships,trends}
```

### 5. Initialize your life systems map

Create `life_systems_map_v1.md` with your goals across all domains. This is the document Super Tobi reads to understand what you're building toward.

### 6. Start using it

Open Claude Code in the project directory. The `CLAUDE.md` file loads automatically. Type any slash command:

```
/status
/daily-sync
/learn system design
/apply jobs
/write a blog post about building personal AI systems
```

---

## Design Principles

**Files are the database.** No Postgres, no Redis, no Firebase. JSON files for structured data. Markdown files for text. Append-only logs for history. `git` for versioning. This is intentional — it means your entire life state is portable, readable, and diffable.

**Commands are composable.** `/apply jobs` finds opportunities. `/write cover-letter` drafts the letter. `/follow-up` chases the response. They share data through files, not through conversation context.

**The kernel is a markdown file.** `CLAUDE.md` isn't a prompt. It's a system specification. It defines identity, architecture, data conventions, voice profiles, and process verbs. When you edit it, you're reconfiguring your OS.

**Agents are scripts, not magic.** Each Python script does one thing well. `job_hunter.py` hunts for jobs. `email_triage.py` triages email. They're readable, debuggable, and replaceable. No framework. No LangChain. Just Python + APIs.

**Privacy by architecture.** All personal data is gitignored by default. API keys are environment variables. The repo you push is the system definition — not your data.

---

## What This Is NOT

- ❌ A chatbot wrapper
- ❌ A prompt collection
- ❌ An "awesome Claude" list
- ❌ A SaaS product
- ❌ An agent framework

It's a **personal operating system**. You fork it, make it yours, and run your life on it.

---

## The Thesis

> Using AI is not enough. You need AI **systems**.

Most people use AI like a search engine with better grammar — type a question, get an answer, close the tab. That's not leverage. That's convenience.

A system is what happens when your AI has:
- **Persistent state** that survives across sessions
- **Scheduled processes** that run without you
- **Data pipelines** that feed one agent's output into another's input
- **Audit trails** so you can see what happened and why

This is what operating systems do for programs. Super Tobi does it for your life.

---

## Extending It

### Add a new command

Create `.claude/commands/your-command.md`:

```markdown
# /your-command — Description

You are Super Tobi running {description}.

## Process
1. Read {relevant data files}
2. Do {the thing}
3. Output {formatted result}
4. Save to {data path}
```

### Add a new script

Create `scripts/your_script.py`. Follow the pattern:
- Read from `data/`
- Do work (API calls, processing, etc.)
- Write results back to `data/`
- Log to `logs/`

### Add a new data domain

Create `data/your-domain/` and add it to the `CLAUDE.md` architecture section so the system knows about it.

---

## Built With

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — the AI runtime
- [Python](https://python.org) + [Rich](https://rich.readthedocs.io/) — scripts and terminal UI
- [twitterapi.io](https://twitterapi.io) — Twitter integration
- [Google APIs](https://developers.google.com/) — Gmail, Calendar
- [Telegram Bot API](https://core.telegram.org/bots) — mobile command interface
- [Playwright](https://playwright.dev/) — browser automation for job applications

---

## License

MIT — fork it, make it yours, run your life on it.

---

## Author

**Tobiloba Adedeji** — AI Researcher, Solana builder, person who got tired of copying data between apps.

- Twitter: [@tobaboradev](https://x.com/tobaboradev)
- Site: [tobysolutions.dev](https://tobysolutions.dev)
- LinkedIn: [tobiloba-adedeji](https://linkedin.com/in/tobiloba-adedeji)
