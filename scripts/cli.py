#!/usr/bin/env python3
"""
Super Tobi CLI — Rich-powered personal OS command center.
"""

import json
import os
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
LOGS = BASE / "logs"
SCRIPTS = BASE / "scripts"
VENV_PYTHON = BASE / ".venv" / "bin" / "python"

console = Console()


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_status():
    """Full system dashboard."""
    # Daemons
    daemon_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    daemon_table.add_column("status", width=3)
    daemon_table.add_column("name", style="bold")
    daemon_table.add_column("info", style="dim")

    try:
        result = subprocess.run(["launchctl", "list"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "supertobi" not in line:
                continue
            parts = line.split()
            pid, exit_code, label = parts[0], parts[1], parts[2]
            name = label.replace("com.supertobi.", "")
            if pid != "-":
                daemon_table.add_row("[green]>>>[/]", name, f"PID {pid}")
            else:
                daemon_table.add_row("[red]---[/]", name, f"exit {exit_code}")
    except Exception:
        daemon_table.add_row("[yellow]?[/]", "unknown", "launchctl error")

    console.print(Panel(daemon_table, title="[bold cyan]Daemons[/]", border_style="cyan", padding=(0, 1)))

    # Jobs summary
    jobs = load_json(DATA / "career" / "jobs" / "applications.json")
    if jobs:
        total = len(jobs)
        applied = sum(1 for j in jobs if j.get("status") == "applied")
        discovered = sum(1 for j in jobs if j.get("status") == "discovered")
        interviewing = sum(1 for j in jobs if j.get("status") in ("interviewing", "interview"))

        job_text = Text()
        job_text.append(f"  {total}", style="bold white")
        job_text.append(" tracked  ", style="dim")
        job_text.append(f"{applied}", style="bold green")
        job_text.append(" applied  ", style="dim")
        job_text.append(f"{discovered}", style="bold yellow")
        job_text.append(" discovered  ", style="dim")
        if interviewing:
            job_text.append(f"{interviewing}", style="bold magenta")
            job_text.append(" interviewing", style="dim")
        console.print(Panel(job_text, title="[bold green]Jobs[/]", border_style="green", padding=(0, 1)))

    # Finance
    txs = load_json(DATA / "finance" / "transactions.json")
    if txs:
        expenses = sum(t.get("amount", 0) for t in txs if t.get("type") == "expense")
        income = sum(t.get("amount", 0) for t in txs if t.get("type") == "income")
        fin_table = Table(box=None, show_header=False, padding=(0, 2))
        fin_table.add_column("label", style="dim")
        fin_table.add_column("value", justify="right")
        fin_table.add_row("Income", f"[green]₦{income:,.0f}[/]")
        fin_table.add_row("Expenses", f"[red]₦{expenses:,.0f}[/]")
        fin_table.add_row("Net", f"[bold]₦{income - expenses:,.0f}[/]")
        console.print(Panel(fin_table, title="[bold yellow]Finance[/]", border_style="yellow", padding=(0, 1)))

    # Today's workout
    plan = load_json(DATA / "health" / "plan.json")
    if plan:
        day = datetime.now().strftime("%A").lower()
        today = plan.get("schedule", {}).get(day, {})
        focus = today.get("focus", "Rest day")
        exercises = today.get("exercises", [])
        if exercises:
            lines = [f"[bold]{focus}[/]"]
            for ex in exercises[:5]:
                sets = ex.get("sets", "")
                reps = ex.get("reps", ex.get("duration", ""))
                if sets:
                    lines.append(f"  [dim]>[/] {ex['name']}: {sets}x{reps}")
                else:
                    lines.append(f"  [dim]>[/] {ex['name']}: {reps}")
            if len(exercises) > 5:
                lines.append(f"  [dim]... +{len(exercises) - 5} more[/]")
            console.print(Panel("\n".join(lines), title="[bold magenta]Workout[/]", border_style="magenta", padding=(0, 1)))

    # Upcoming birthdays (next 30 days)
    bdays = load_json(DATA / "relationships" / "birthdays.json")
    today_date = date.today()
    upcoming = []
    for p in bdays:
        d = p.get("date", "")
        if d == "FILL-IN" or "-" not in d:
            continue
        try:
            m, day_num = d.split("-")
            bday = date(today_date.year, int(m), int(day_num))
            if bday < today_date:
                bday = date(today_date.year + 1, int(m), int(day_num))
            days_until = (bday - today_date).days
            if days_until <= 30:
                upcoming.append((days_until, p["name"], d))
        except (ValueError, KeyError):
            continue

    if upcoming:
        upcoming.sort()
        bday_lines = []
        for days_until, name, d in upcoming[:5]:
            if days_until == 0:
                bday_lines.append(f"  [bold red]TODAY![/] {name}")
            elif days_until <= 3:
                bday_lines.append(f"  [yellow]{days_until}d[/]  {name}")
            else:
                bday_lines.append(f"  [dim]{days_until}d[/]  {name}")
        console.print(Panel("\n".join(bday_lines), title="[bold red]Birthdays[/]", border_style="red", padding=(0, 1)))

    # Last activity
    daemon_log = LOGS / "daemon.log"
    auto_log = LOGS / "autonomous_cycles.log"
    activity_lines = []
    for label, logfile in [("Daemon", daemon_log), ("Auto", auto_log)]:
        try:
            last = logfile.read_text().strip().splitlines()[-1][:70]
            activity_lines.append(f"  [dim]{label}:[/] {last}")
        except (FileNotFoundError, IndexError):
            activity_lines.append(f"  [dim]{label}:[/] no activity")
    console.print(Panel("\n".join(activity_lines), title="[bold blue]Last Activity[/]", border_style="blue", padding=(0, 1)))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DAEMON CONTROL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
PLISTS = ["com.supertobi.daemon", "com.supertobi.telegram", "com.supertobi.autonomous", "com.supertobi.proof"]


def cmd_start():
    for p in PLISTS:
        plist = PLIST_DIR / f"{p}.plist"
        if plist.exists():
            subprocess.run(["launchctl", "load", str(plist)], capture_output=True)
            console.print(f"  [green]>>>[/] {p.replace('com.supertobi.', '')}")
        else:
            console.print(f"  [yellow]---[/] {p} (plist not found)")
    console.print("\n[bold green]All daemons started.[/]")


def cmd_stop():
    for p in PLISTS:
        plist = PLIST_DIR / f"{p}.plist"
        if plist.exists():
            subprocess.run(["launchctl", "unload", str(plist)], capture_output=True)
    console.print("[bold red]All daemons stopped.[/]")


def cmd_restart():
    cmd_stop()
    cmd_start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LOGS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_logs(log_type="daemon"):
    log_map = {
        "daemon": LOGS / "daemon.log",
        "auto": LOGS / "autonomous_cycles.log",
        "telegram": LOGS / "telegram_stderr.log",
        "observer": LOGS / "usage_observer.log",
        "proof": LOGS / "proof_stdout.log",
        "apply": LOGS / "auto_apply.log",
    }
    if log_type == "all":
        files = [str(v) for v in log_map.values() if v.exists()]
        os.execvp("tail", ["tail", "-f"] + files)
    elif log_type in log_map:
        path = log_map[log_type]
        if path.exists():
            os.execvp("tail", ["tail", "-f", str(path)])
        else:
            console.print(f"[red]Log not found:[/] {path}")
    else:
        console.print(f"[red]Unknown log type:[/] {log_type}")
        console.print("[dim]Options: daemon, auto, telegram, all[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JOBS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_jobs(subcmd="list", arg=None):
    if subcmd == "list":
        jobs = load_json(DATA / "career" / "jobs" / "applications.json")
        if not jobs:
            console.print("[dim]No jobs tracked yet.[/]")
            return

        table = Table(title="Job Applications", box=box.ROUNDED, show_lines=False)
        table.add_column("#", style="dim", width=4)
        table.add_column("Company", style="bold")
        table.add_column("Role", max_width=40)
        table.add_column("Status", justify="center")
        table.add_column("Board", style="dim")

        status_colors = {
            "applied": "green",
            "discovered": "yellow",
            "interviewing": "magenta",
            "interview": "magenta",
            "rejected": "red",
            "offer": "bold green",
        }

        for i, j in enumerate(jobs):
            status = j.get("status", "unknown")
            color = status_colors.get(status, "white")
            table.add_row(
                str(i),
                j.get("company", "?"),
                j.get("role", j.get("title", "?")),
                f"[{color}]{status}[/]",
                j.get("board", j.get("source", "?")),
            )

        console.print(table)
        console.print(f"\n[dim]{len(jobs)} total[/]")

    elif subcmd == "hunt":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "job_hunter.py"), "--hunt"])

    elif subcmd == "cover":
        idx = arg or "0"
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "job_hunter.py"), "--cover-letter", str(idx)])

    elif subcmd == "apply":
        max_apps = arg or "10"
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "auto_apply.py"), "--max", str(max_apps)])

    elif subcmd == "resolve":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "url_resolver.py")])

    else:
        console.print(f"[red]Unknown jobs subcommand:[/] {subcmd}")
        console.print("[dim]Options: list, hunt, cover <N>, apply [max], resolve[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TWITTER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_twitter(subcmd="feed"):
    flag_map = {
        "feed": "--full",
        "mentions": "--mentions",
        "tweets": "--my-tweets",
        "topics": "--topics",
    }
    flag = flag_map.get(subcmd)
    if not flag:
        console.print(f"[red]Unknown twitter subcommand:[/] {subcmd}")
        console.print("[dim]Options: feed, mentions, tweets, topics[/]")
        return
    os.chdir(BASE)
    os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "twitter_feed.py"), flag])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FINANCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_finance(subcmd="status"):
    if subcmd == "scan":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "gmail_expenses.py")])
    elif subcmd == "status":
        txs = load_json(DATA / "finance" / "transactions.json")
        if not txs:
            console.print("[dim]No transactions tracked.[/]")
            return

        expenses = sum(t.get("amount", 0) for t in txs if t.get("type") == "expense")
        income = sum(t.get("amount", 0) for t in txs if t.get("type") == "income")

        # By category
        categories = {}
        for t in txs:
            if t.get("type") == "expense":
                cat = t.get("category", "uncategorized")
                categories[cat] = categories.get(cat, 0) + t.get("amount", 0)

        table = Table(title="Finance Overview", box=box.ROUNDED)
        table.add_column("Category", style="bold")
        table.add_column("Amount", justify="right")

        table.add_row("Income", f"[green]₦{income:,.0f}[/]")
        table.add_row("", "")
        for cat, amt in sorted(categories.items(), key=lambda x: -x[1]):
            table.add_row(cat.title(), f"[red]₦{amt:,.0f}[/]")
        table.add_row("", "")
        table.add_row("[bold]Total Expenses[/]", f"[bold red]₦{expenses:,.0f}[/]")
        table.add_row("[bold]Net[/]", f"[bold {'green' if income >= expenses else 'red'}]₦{income - expenses:,.0f}[/]")

        console.print(table)
        console.print(f"\n[dim]{len(txs)} transactions[/]")
    else:
        console.print("[dim]Options: status, scan[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HEALTH
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_health(subcmd="workout"):
    plan = load_json(DATA / "health" / "plan.json")
    if not plan:
        console.print("[dim]No workout plan found.[/]")
        return

    day = datetime.now().strftime("%A").lower()
    today = plan.get("schedule", {}).get(day, {})
    focus = today.get("focus", "Rest day")
    exercises = today.get("exercises", [])

    table = Table(title=f"{day.title()} — {focus}", box=box.ROUNDED, show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Exercise", style="bold")
    table.add_column("Sets", justify="center")
    table.add_column("Reps/Duration", justify="center")

    for i, ex in enumerate(exercises, 1):
        table.add_row(
            str(i),
            ex.get("name", "?"),
            str(ex.get("sets", "-")),
            str(ex.get("reps", ex.get("duration", "-"))),
        )

    console.print(table)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BIRTHDAYS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_birthdays():
    bdays = load_json(DATA / "relationships" / "birthdays.json")
    today_date = date.today()

    table = Table(title="Birthdays", box=box.ROUNDED, show_lines=False)
    table.add_column("Days", justify="right", width=6)
    table.add_column("Name", style="bold")
    table.add_column("Date", style="dim")

    entries = []
    for p in bdays:
        d = p.get("date", "")
        if d == "FILL-IN" or "-" not in d:
            continue
        try:
            m, day_num = d.split("-")
            bday = date(today_date.year, int(m), int(day_num))
            if bday < today_date:
                bday = date(today_date.year + 1, int(m), int(day_num))
            days_until = (bday - today_date).days
            entries.append((days_until, p.get("name", "?"), d))
        except (ValueError, KeyError):
            continue

    entries.sort()
    for days_until, name, d in entries:
        if days_until == 0:
            table.add_row("[bold red]TODAY[/]", f"[bold red]{name}[/]", d)
        elif days_until <= 7:
            table.add_row(f"[yellow]{days_until}[/]", name, d)
        else:
            table.add_row(str(days_until), name, d)

    console.print(table)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LANGUAGE LEARNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_lang(subcmd=None, extra=None, extra2=None):
    lang_script = SCRIPTS / "language_learn.py"
    if subcmd is None:
        # Show progress
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(lang_script), "--progress"])
    elif subcmd == "lesson":
        if not extra:
            console.print("[red]Usage:[/] supertobi lang lesson <lang>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(lang_script), "--lesson", extra])
    elif subcmd == "quiz":
        if not extra:
            console.print("[red]Usage:[/] supertobi lang quiz <lang>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(lang_script), "--quiz", extra])
    elif subcmd == "practice":
        if not extra:
            console.print("[red]Usage:[/] supertobi lang practice <lang>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(lang_script), "--practice", extra])
    elif subcmd == "add":
        if not extra:
            console.print("[red]Usage:[/] supertobi lang add <lang> <word> <translation> [transliteration]")
            return
        add_args = [str(VENV_PYTHON), str(lang_script), "--add"] + sys.argv[3:]
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), add_args)
    else:
        console.print(f"[red]Unknown lang subcommand:[/] {subcmd}")
        console.print("[dim]Options: lesson <lang>, quiz <lang>, practice <lang>, add <lang> <word> <translation>[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMPANY INTEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_intel(subcmd=None, extra=None):
    if subcmd == "batch":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "company_intel.py"), "--batch"])
    elif subcmd == "prep":
        company = extra
        role = sys.argv[4] if len(sys.argv) > 4 else None
        if not company or not role:
            console.print("[red]Usage:[/] supertobi intel prep <company> <role>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "company_intel.py"), "--prep", company, role])
    elif subcmd:
        # Treat subcmd as the company name for research
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "company_intel.py"), "--research", subcmd])
    else:
        console.print("[red]Usage:[/] supertobi intel <company>")
        console.print("[dim]  supertobi intel Google              -- research a company[/]")
        console.print("[dim]  supertobi intel prep Google \"AI Engineer\" -- full prep package[/]")
        console.print("[dim]  supertobi intel batch               -- research all top jobs[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ASK (AI)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_ask(question):
    if not question:
        console.print("[red]Usage:[/] supertobi ask <question>")
        return
    sys.path.insert(0, str(SCRIPTS))
    try:
        from ai import ask_claude
        with console.status("[bold cyan]Thinking...[/]"):
            answer = ask_claude(question)
        console.print(Panel(answer.strip(), border_style="cyan", padding=(1, 2)))
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WRITE (Proof Editor)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_write(subcmd=None, extra=""):
    if subcmd == "list":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "proof_writer.py"), "list"])
    elif subcmd == "publish":
        if not extra:
            console.print("[red]Usage:[/] supertobi write publish <slug>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "proof_writer.py"), "publish", extra])
    elif subcmd:
        # Everything else is a writing prompt
        prompt = f"{subcmd} {extra}".strip()
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "proof_writer.py"), "write", prompt])
    else:
        console.print("[red]Usage:[/] supertobi write <prompt>")
        console.print("[dim]  supertobi write a blog post about Solana agents[/]")
        console.print("[dim]  supertobi write list[/]")
        console.print("[dim]  supertobi write publish <slug>[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SUBSCRIPTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_subs(subcmd=None, extra=None):
    if subcmd == "scan":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "subscription_tracker.py"), "--scan"])
    elif subcmd == "add":
        # Need name, amount, frequency from remaining args
        rest = sys.argv[3:]  # everything after 'subs add'
        if len(rest) < 3:
            console.print("[red]Usage:[/] supertobi subs add <name> <amount> <frequency>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "subscription_tracker.py"), "--add", rest[0], rest[1], rest[2]])
    elif subcmd == "remove":
        name = extra or (sys.argv[3] if len(sys.argv) > 3 else None)
        if not name:
            console.print("[red]Usage:[/] supertobi subs remove <name>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "subscription_tracker.py"), "--remove", name])
    elif subcmd == "total":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "subscription_tracker.py"), "--total"])
    else:
        # Default: list
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "subscription_tracker.py"), "--list"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAX
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_tax(subcmd=None, extra=None):
    if subcmd == "estimate":
        amount = extra or (sys.argv[3] if len(sys.argv) > 3 else None)
        if not amount:
            console.print("[red]Usage:[/] supertobi tax estimate <annual_income>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "tax_tracker.py"), "--estimate", amount])
    elif subcmd == "deadlines":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "tax_tracker.py"), "--deadlines"])
    elif subcmd == "log":
        rest = sys.argv[3:]
        if len(rest) < 2:
            console.print("[red]Usage:[/] supertobi tax log <source> <amount>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "tax_tracker.py"), "--log", rest[0], rest[1]])
    else:
        # Default: status
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "tax_tracker.py"), "--status"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FILES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_files(subcmd=None, extra=None):
    if subcmd == "scan":
        directory = extra or (sys.argv[3] if len(sys.argv) > 3 else None)
        if not directory:
            console.print("[red]Usage:[/] supertobi files scan <directory>")
            return
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "file_organizer.py"), "--scan", directory])
    elif subcmd == "organize":
        directory = extra or (sys.argv[3] if len(sys.argv) > 3 else None)
        if not directory:
            console.print("[red]Usage:[/] supertobi files organize <directory>")
            return
        cmd_args = [str(VENV_PYTHON), str(SCRIPTS / "file_organizer.py"), "--organize", directory]
        if "--confirm" in sys.argv:
            cmd_args.append("--confirm")
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), cmd_args)
    elif subcmd == "cleanup":
        directory = extra or (sys.argv[3] if len(sys.argv) > 3 else None)
        if not directory:
            console.print("[red]Usage:[/] supertobi files cleanup <directory> --confirm")
            return
        cmd_args = [str(VENV_PYTHON), str(SCRIPTS / "file_organizer.py"), "--cleanup", directory]
        if "--confirm" in sys.argv:
            cmd_args.append("--confirm")
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), cmd_args)
    elif subcmd == "downloads":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "file_organizer.py"), "--downloads"])
    else:
        console.print("[red]Usage:[/] supertobi files <scan|organize|cleanup|downloads> [dir]")
        console.print("[dim]  supertobi files scan ~/Downloads[/]")
        console.print("[dim]  supertobi files organize ~/Downloads[/]")
        console.print("[dim]  supertobi files downloads[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_trade(subcmd=None, extra=None):
    trade_args = [str(VENV_PYTHON), str(SCRIPTS / "trading.py")]
    rest = sys.argv[2:]  # everything after 'trade'

    if subcmd == "prices" or subcmd is None:
        trade_args.append("--prices")
    elif subcmd == "log":
        # supertobi trade log <pair> <side> <entry> <size> [--sl X] [--tp X]
        if len(rest) < 5:
            console.print("[red]Usage:[/] supertobi trade log <pair> <side> <entry> <size> [--sl X] [--tp X]")
            return
        trade_args.extend(["--log", rest[1], rest[2], rest[3], rest[4]])
        # Pass through --sl and --tp flags
        i = 5
        while i < len(rest):
            if rest[i] == "--sl" and i + 1 < len(rest):
                trade_args.extend(["--sl", rest[i + 1]])
                i += 2
            elif rest[i] == "--tp" and i + 1 < len(rest):
                trade_args.extend(["--tp", rest[i + 1]])
                i += 2
            else:
                i += 1
    elif subcmd == "close":
        if len(rest) < 3:
            console.print("[red]Usage:[/] supertobi trade close <trade_id> <exit_price>")
            return
        trade_args.extend(["--close", rest[1], rest[2]])
    elif subcmd == "journal":
        trade_args.append("--journal")
    elif subcmd == "watchlist":
        if len(rest) < 3:
            console.print("[red]Usage:[/] supertobi trade watchlist add|remove <pair>")
            return
        trade_args.extend(["--watchlist", rest[1], rest[2]])
    elif subcmd == "alert":
        if len(rest) < 4:
            console.print("[red]Usage:[/] supertobi trade alert <pair> <above|below> <price>")
            return
        trade_args.extend(["--alert", rest[1], rest[2], rest[3]])
    else:
        console.print(f"[red]Unknown trade subcommand:[/] {subcmd}")
        console.print("[dim]Options: prices, log, close, journal, watchlist, alert[/]")
        return

    os.chdir(BASE)
    os.execvp(str(VENV_PYTHON), trade_args)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENTERTAINMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_fun(subcmd=None, extra=None):
    fun_args = [str(VENV_PYTHON), str(SCRIPTS / "entertainment.py")]
    rest = sys.argv[2:]  # everything after 'fun'

    if subcmd is None:
        # Default: show all
        pass  # no flags = show all
    elif subcmd == "movies":
        fun_args.append("--movies")
    elif subcmd == "music":
        fun_args.append("--music")
    elif subcmd == "football":
        fun_args.append("--football")
    elif subcmd == "watch":
        movie = " ".join(rest[1:]) if len(rest) > 1 else None
        if not movie:
            console.print("[red]Usage:[/] supertobi fun watch <movie name>")
            return
        fun_args.extend(["--watch", movie])
    elif subcmd == "rate":
        if len(rest) < 3:
            console.print("[red]Usage:[/] supertobi fun rate <movie name> <1-10>")
            return
        # Last arg is the rating, everything in between is the movie name
        rating = rest[-1]
        movie = " ".join(rest[1:-1])
        fun_args.extend(["--rate", movie, rating])
    elif subcmd == "discover":
        genre = extra or (rest[1] if len(rest) > 1 else None)
        if not genre:
            console.print("[red]Usage:[/] supertobi fun discover <genre>")
            return
        fun_args.extend(["--discover", genre])
    else:
        console.print(f"[red]Unknown fun subcommand:[/] {subcmd}")
        console.print("[dim]Options: movies, music, football, watch, rate, discover[/]")
        return

    os.chdir(BASE)
    os.execvp(str(VENV_PYTHON), fun_args)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRENDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_trends(subcmd=None):
    flag_map = {
        None: "--show",
        "scan": "--scan",
        "digest": "--digest",
        "ideas": "--ideas",
        "report": "--report",
    }
    flag = flag_map.get(subcmd)
    if not flag:
        console.print(f"[red]Unknown trends subcommand:[/] {subcmd}")
        console.print("[dim]Options: scan, digest, ideas, report[/]")
        return
    os.chdir(BASE)
    os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(SCRIPTS / "trends_aggregator.py"), flag])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CREATIVE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_creative(subcmd=None, extra=None):
    creative_args = [str(VENV_PYTHON), str(SCRIPTS / "creative_aggregator.py")]

    if subcmd is None or subcmd == "scan":
        creative_args.append("--scan")
    elif subcmd == "digest":
        creative_args.append("--digest")
    elif subcmd == "ideas":
        creative_args.append("--ideas")
    elif subcmd == "report":
        creative_args.append("--report")
    else:
        console.print(f"[red]Unknown creative subcommand:[/] {subcmd}")
        console.print("[dim]Options: scan, digest, ideas, report[/]")
        return

    os.chdir(BASE)
    os.execvp(str(VENV_PYTHON), creative_args)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USAGE OBSERVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_usage(subcmd=None, extra=None):
    obs_script = SCRIPTS / "usage_observer.py"
    if subcmd == "patterns":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(obs_script), "--patterns"])
    elif subcmd == "insights":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(obs_script), "--insights"])
    elif subcmd == "snapshot":
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(obs_script), "--snapshot"])
    else:
        os.chdir(BASE)
        os.execvp(str(VENV_PYTHON), [str(VENV_PYTHON), str(obs_script), "--today"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELP
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_help():
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("cmd", style="bold cyan", min_width=28)
    table.add_column("desc")

    table.add_row("[dim]--- System ---[/]", "")
    table.add_row("supertobi", "Full dashboard")
    table.add_row("supertobi start", "Start all daemons")
    table.add_row("supertobi stop", "Stop all daemons")
    table.add_row("supertobi restart", "Restart all daemons")
    table.add_row("supertobi logs [type]", "Tail logs (daemon|auto|telegram|all)")
    table.add_row("", "")
    table.add_row("[dim]--- Jobs ---[/]", "")
    table.add_row("supertobi jobs", "Job applications table")
    table.add_row("supertobi jobs hunt", "Search for new jobs")
    table.add_row("supertobi jobs cover N", "Cover letter for job #N")
    table.add_row("supertobi jobs apply [N]", "Auto-apply to top N jobs (default 10)")
    table.add_row("supertobi jobs resolve", "Resolve direct ATS URLs")
    table.add_row("", "")
    table.add_row("[dim]--- Company Intel ---[/]", "")
    table.add_row("supertobi intel <company>", "Research a company (Reddit + Glassdoor)")
    table.add_row("supertobi intel prep <co> <role>", "Full prep package for application")
    table.add_row("supertobi intel batch", "Research all top discovered jobs")
    table.add_row("", "")
    table.add_row("[dim]--- Life ---[/]", "")
    table.add_row("supertobi twitter [sub]", "Feed, mentions, tweets, topics")
    table.add_row("supertobi finance [sub]", "Status or scan Gmail")
    table.add_row("supertobi health", "Today's workout")
    table.add_row("supertobi birthdays", "Upcoming birthdays")
    table.add_row("supertobi ask <question>", "Ask Super Tobi anything")
    table.add_row("", "")
    table.add_row("[dim]--- Languages ---[/]", "")
    table.add_row("supertobi lang", "Language learning progress")
    table.add_row("supertobi lang lesson <lang>", "New lesson (5 words + 2 phrases)")
    table.add_row("supertobi lang quiz <lang>", "Spaced repetition quiz")
    table.add_row("supertobi lang practice <lang>", "AI conversation practice")
    table.add_row("supertobi lang add <lang> <w> <t>", "Add vocabulary word")
    table.add_row("", "")
    table.add_row("[dim]--- Subscriptions ---[/]", "")
    table.add_row("supertobi subs", "List all subscriptions")
    table.add_row("supertobi subs scan", "Scan Gmail for recurring charges")
    table.add_row("supertobi subs list", "Show subscriptions + monthly cost")
    table.add_row("supertobi subs add <n> <amt> <freq>", "Add subscription (monthly/yearly)")
    table.add_row("supertobi subs remove <name>", "Remove a subscription")
    table.add_row("supertobi subs total", "Total monthly spend")
    table.add_row("", "")
    table.add_row("[dim]--- Tax ---[/]", "")
    table.add_row("supertobi tax", "Tax status overview")
    table.add_row("supertobi tax estimate <amount>", "Estimate Nigerian tax")
    table.add_row("supertobi tax deadlines", "Upcoming tax deadlines")
    table.add_row("supertobi tax log <source> <amount>", "Log income from source")
    table.add_row("", "")
    table.add_row("[dim]--- Files ---[/]", "")
    table.add_row("supertobi files scan <dir>", "Scan directory for report")
    table.add_row("supertobi files organize <dir>", "Plan file organization (dry run)")
    table.add_row("supertobi files downloads", "Scan ~/Downloads")
    table.add_row("", "")
    table.add_row("[dim]--- Trading ---[/]", "")
    table.add_row("supertobi trade", "Market prices (default)")
    table.add_row("supertobi trade prices", "Fetch live prices for watchlist")
    table.add_row("supertobi trade log <p> <side> <entry> <sz>", "Log a trade (--sl/--tp)")
    table.add_row("supertobi trade close <id> <exit>", "Close a trade, calc P&L")
    table.add_row("supertobi trade journal", "Trade journal + win rate + P&L")
    table.add_row("supertobi trade watchlist add|rm <pair>", "Manage watchlist")
    table.add_row("supertobi trade alert <p> <above|below> <$>", "Set price alert")
    table.add_row("", "")
    table.add_row("[dim]--- Entertainment ---[/]", "")
    table.add_row("supertobi fun", "All entertainment")
    table.add_row("supertobi fun movies", "Movie recommendations")
    table.add_row("supertobi fun music", "Music recommendations")
    table.add_row("supertobi fun football", "Football scores & fixtures")
    table.add_row("supertobi fun watch <movie>", "Mark movie as watched")
    table.add_row("supertobi fun rate <movie> <1-10>", "Rate a movie")
    table.add_row("supertobi fun discover <genre>", "Discover content by genre")
    table.add_row("", "")
    table.add_row("[dim]--- Writing ---[/]", "")
    table.add_row("supertobi write <prompt>", "Write in Proof editor")
    table.add_row("supertobi write list", "List Proof documents")
    table.add_row("supertobi write publish <slug>", "Export from Proof")
    table.add_row("", "")
    table.add_row("[dim]--- Creative ---[/]", "")
    table.add_row("supertobi creative", "Creative industry scan (default)")
    table.add_row("supertobi creative scan", "Fetch music/streaming/movie trends")
    table.add_row("supertobi creative digest", "AI analysis of creative trends")
    table.add_row("supertobi creative ideas", "Generate ideas for creators")
    table.add_row("supertobi creative report", "Full report (scan + digest + ideas)")
    table.add_row("", "")
    table.add_row("[dim]--- Trends ---[/]", "")
    table.add_row("supertobi trends", "Trends overview + top signals")
    table.add_row("supertobi trends scan", "Fetch new trends from all sources")
    table.add_row("supertobi trends digest", "AI analysis of current trends")
    table.add_row("supertobi trends ideas", "Generate product ideas from trends")
    table.add_row("supertobi trends report", "Full report (scan + digest + ideas)")
    table.add_row("", "")
    table.add_row("[dim]--- Usage Observer ---[/]", "")
    table.add_row("supertobi usage", "Today's PC usage summary")
    table.add_row("supertobi usage patterns", "Learned patterns over time")
    table.add_row("supertobi usage insights", "AI analysis of your habits")

    console.print(Panel(table, title="[bold]SUPER TOBI[/]", subtitle="[dim]Personal OS v2[/]", border_style="cyan", padding=(1, 1)))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"
    sub = args[1] if len(args) > 1 else None
    extra = args[2] if len(args) > 2 else None

    # Banner on main commands
    if cmd in ("status", "help"):
        console.print("[bold cyan]  SUPER TOBI[/] [dim]v2.0[/]\n")

    commands = {
        "status": lambda: cmd_status(),
        "start": lambda: cmd_start(),
        "stop": lambda: cmd_stop(),
        "restart": lambda: cmd_restart(),
        "logs": lambda: cmd_logs(sub or "daemon"),
        "jobs": lambda: cmd_jobs(sub or "list", extra),
        "intel": lambda: cmd_intel(sub, extra),
        "twitter": lambda: cmd_twitter(sub or "feed"),
        "finance": lambda: cmd_finance(sub or "status"),
        "health": lambda: cmd_health(sub or "workout"),
        "birthdays": lambda: cmd_birthdays(),
        "subs": lambda: cmd_subs(sub, extra),
        "tax": lambda: cmd_tax(sub, extra),
        "files": lambda: cmd_files(sub, extra),
        "trade": lambda: cmd_trade(sub, extra),
        "fun": lambda: cmd_fun(sub, extra),
        "creative": lambda: cmd_creative(sub, extra),
        "trends": lambda: cmd_trends(sub),
        "usage": lambda: cmd_usage(sub, extra),
        "lang": lambda: cmd_lang(sub, extra),
        "ask": lambda: cmd_ask(" ".join(args[1:])),
        "write": lambda: cmd_write(sub, " ".join(args[2:]) if len(args) > 2 else ""),
        "help": lambda: cmd_help(),
        "--help": lambda: cmd_help(),
        "-h": lambda: cmd_help(),
    }

    handler = commands.get(cmd)
    if handler:
        handler()
    else:
        console.print(f"[red]Unknown command:[/] {cmd}")
        console.print("[dim]Run 'supertobi help' for all commands[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
