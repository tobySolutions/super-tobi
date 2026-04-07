#!/bin/bash
# Super Tobi — Autonomous Cycle
# Runs modular scripts for each task, then Claude for smart tasks
# Called by launchd every hour

SUPER_TOBI_DIR="/Users/tobiloba/super-tobi"
VENV="$SUPER_TOBI_DIR/.venv/bin/python"
CLAUDE="/Users/tobiloba/.local/bin/claude"
LOG_FILE="$SUPER_TOBI_DIR/logs/autonomous_cycles.log"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') | $1" >> "$LOG_FILE"; }

log "=== Autonomous cycle starting ==="
cd "$SUPER_TOBI_DIR"

# 1. JOBS — Hunt for new jobs (fast, HTTP-only)
log "JOBS: Hunting..."
$VENV scripts/job_hunter.py --hunt >> "$LOG_FILE" 2>&1
hunt_exit=$?
log "JOBS: Hunt complete (exit $hunt_exit)"

# 2. JOBS — Resolve URLs for new discoveries
log "JOBS: Resolving URLs..."
$VENV scripts/url_resolver.py >> "$LOG_FILE" 2>&1

# 3. JOBS — Gather company intelligence on top discovered jobs
log "JOBS: Running company intel batch..."
BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/company_intel.py --batch --min-score 50 >> "$LOG_FILE" 2>&1
log "JOBS: Company intel complete"

# 4. JOBS — Auto-apply to top 5 (uses Claude CLI per application)
log "JOBS: Auto-applying..."
$VENV scripts/auto_apply.py --max 5 --min-score 30 >> "$LOG_FILE" 2>&1
apply_exit=$?
log "JOBS: Apply complete (exit $apply_exit)"

# 5. TRENDS — Scan tech + creative trends (every cycle)
log "TRENDS: Scanning tech trends..."
BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/trends_aggregator.py --scan >> "$LOG_FILE" 2>&1
log "TRENDS: Scanning creative trends..."
BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/creative_aggregator.py --scan >> "$LOG_FILE" 2>&1

# 6. TRENDS — Generate ideas (once per day, check hour)
HOUR=$(date '+%H')
if [ "$HOUR" = "09" ]; then
    log "TRENDS: Generating daily ideas digest..."
    BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/trends_aggregator.py --digest >> "$LOG_FILE" 2>&1
    BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/trends_aggregator.py --ideas >> "$LOG_FILE" 2>&1
    BRAVE_API_KEY=BSAdfN_w6yx0awOfDb7S9Iko5NO_ggz $VENV scripts/creative_aggregator.py --ideas >> "$LOG_FILE" 2>&1
    log "TRENDS: Ideas generated"
fi

# 7. TWITTER
log "TWITTER: Pulling feed..."
$VENV scripts/twitter_feed.py --full >> "$LOG_FILE" 2>&1

# 8. GMAIL — Expense scan
log "GMAIL: Scanning expenses..."
$VENV scripts/gmail_expenses.py >> "$LOG_FILE" 2>&1

# 8b. EMAIL TRIAGE — Scan for job rejections, responses, recruiter outreach
log "EMAIL TRIAGE: Scanning for job updates..."
$VENV scripts/email_triage.py --days 7 >> "$LOG_FILE" 2>&1

# 9. BIRTHDAYS — Check next 3 days
log "BIRTHDAYS: Checking..."
$VENV -c "
import json
from datetime import date, timedelta
with open('data/relationships/birthdays.json') as f:
    bdays = json.load(f)
today = date.today()
for p in bdays:
    d = p.get('date', '')
    if d == 'FILL-IN' or '-' not in d: continue
    try:
        m, day = d.split('-')
        bday = date(today.year, int(m), int(day))
        if bday < today: bday = date(today.year+1, int(m), int(day))
        diff = (bday - today).days
        if diff <= 3:
            import subprocess
            msg = f\"Birthday alert: {p['name']} in {diff} day(s)!\" if diff > 0 else f\"TODAY: {p['name']}'s birthday!\"
            subprocess.run(['osascript', '-e', f'display notification \"{msg}\" with title \"Super Tobi\"'], capture_output=True)
            print(f'  Notified: {msg}')
    except: pass
" >> "$LOG_FILE" 2>&1

# 10. EMAIL TRIAGE — scan Gmail for rejections, responses, recruiter outreach (replaces old inline scanner)
log "EMAIL TRIAGE: Running full triage..."
$VENV scripts/email_triage.py --days 7 >> "$LOG_FILE" 2>&1

# 11. Log cycle summary
$VENV -c "
import json
from datetime import datetime
log_file = 'logs/repl_cycles.json'
try:
    with open(log_file) as f: cycles = json.load(f)
except: cycles = []

with open('data/career/jobs/applications.json') as f:
    apps = json.load(f)

cycles.append({
    'timestamp': datetime.now().isoformat(),
    'total_jobs': len(apps),
    'applied': sum(1 for a in apps if a.get('status') == 'applied'),
    'discovered': sum(1 for a in apps if a.get('status') == 'discovered'),
    'expired': sum(1 for a in apps if a.get('status') == 'expired'),
})

with open(log_file, 'w') as f:
    json.dump(cycles[-50:], f, indent=2)
print(f'Cycle logged: {cycles[-1]}')
" >> "$LOG_FILE" 2>&1

log "=== Autonomous cycle complete ==="
echo "---" >> "$LOG_FILE"
