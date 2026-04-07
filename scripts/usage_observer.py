#!/usr/bin/env python3
"""
Super Tobi — Usage Observer
Watches daily PC usage patterns — active apps, window titles, file access,
terminal commands, time-of-day habits — so Super Tobi can learn and eventually
automate or anticipate tasks.

Runs every 30 seconds via the daemon, logs to data/usage/daily/.
"""

import json
import os
import subprocess
import time
from datetime import datetime, date
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
USAGE_DIR = BASE_DIR / "data" / "usage"
DAILY_DIR = USAGE_DIR / "daily"
PATTERNS_FILE = USAGE_DIR / "patterns.json"
LOG_FILE = BASE_DIR / "logs" / "usage_observer.log"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"{ts} | {msg}\n")


def get_today_file():
    """Get today's usage log file."""
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    return DAILY_DIR / f"{date.today().isoformat()}.json"


def load_today():
    f = get_today_file()
    try:
        return json.loads(f.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "date": date.today().isoformat(),
            "snapshots": [],
            "app_time": {},
            "window_titles": [],
            "file_events": [],
            "commands": [],
            "summary": None,
        }


def save_today(data):
    get_today_file().write_text(json.dumps(data, indent=2, default=str))


# ─── Observers ────────────────────────────────────

def get_active_app():
    """Get the currently focused application name using lsappinfo (no accessibility permissions needed)."""
    try:
        result = subprocess.run(
            ["lsappinfo", "info", "-only", "name", str(subprocess.run(
                ["lsappinfo", "front"], capture_output=True, text=True, timeout=3
            ).stdout.strip())],
            capture_output=True, text=True, timeout=5,
        )
        # Parse: "LSDisplayName"="AppName"
        for line in result.stdout.strip().splitlines():
            if "LSDisplayName" in line:
                return line.split("=", 1)[1].strip().strip('"')
        return None
    except Exception:
        return None


def get_active_window_title():
    """Get active app name (window titles require accessibility permissions)."""
    app = get_active_app()
    return app if app else None


def get_running_apps():
    """Get list of currently running user applications."""
    try:
        result = subprocess.run(
            ["lsappinfo", "list"],
            capture_output=True, text=True, timeout=5,
        )
        apps = set()
        # Only keep apps with type="Foreground"
        import re
        entries = result.stdout.split("\n\n")
        for entry in entries:
            if 'type="Foreground"' not in entry:
                continue
            match = re.search(r'^\s*\d+\)\s*"([^"]+)"', entry)
            if match:
                name = match.group(1)
                apps.add(name)
        return sorted(apps)
    except Exception:
        return []


def get_recent_shell_commands(n=5):
    """Get the last N shell commands from history."""
    commands = []
    for hist_file in [
        Path.home() / ".zsh_history",
        Path.home() / ".bash_history",
    ]:
        if hist_file.exists():
            try:
                lines = hist_file.read_text(errors="ignore").strip().splitlines()
                for line in lines[-n:]:
                    # zsh history format: : timestamp:0;command
                    if line.startswith(":"):
                        cmd = line.split(";", 1)[1] if ";" in line else line
                    else:
                        cmd = line
                    # Skip sensitive commands
                    if any(s in cmd.lower() for s in ["password", "secret", "token", "key=", "api_key"]):
                        continue
                    commands.append(cmd.strip())
            except Exception:
                pass
            break
    return commands[-n:]


def get_recent_downloads():
    """Check for new files in Downloads."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return []
    try:
        now = time.time()
        recent = []
        for f in downloads.iterdir():
            if f.name.startswith("."):
                continue
            age_hours = (now - f.stat().st_mtime) / 3600
            if age_hours < 1:  # Last hour
                recent.append({
                    "name": f.name,
                    "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
                    "type": f.suffix,
                })
        return recent
    except Exception:
        return []


def get_browser_tab_count():
    """Get number of open browser tabs (Safari/Chrome/Arc/Brave)."""
    for browser in ["Google Chrome", "Arc", "Brave Browser", "Safari"]:
        try:
            result = subprocess.run(
                ["osascript", "-e", f'tell application "{browser}" to count of tabs of every window'],
                capture_output=True, text=True, timeout=3,
            )
            if result.returncode == 0:
                counts = result.stdout.strip().split(", ")
                total = sum(int(c) for c in counts if c.isdigit())
                return {"browser": browser, "tabs": total}
        except Exception:
            continue
    return None


# ─── Snapshot ─────────────────────────────────────

def take_snapshot():
    """Take a single usage snapshot."""
    now = datetime.now()
    active_app = get_active_app()
    window_info = get_active_window_title()

    snapshot = {
        "time": now.strftime("%H:%M:%S"),
        "hour": now.hour,
        "active_app": active_app,
        "window": window_info,
        "running_apps": get_running_apps(),
    }

    # Only check these less frequently (every 5 min)
    minute = now.minute
    if minute % 5 == 0:
        snapshot["browser"] = get_browser_tab_count()
        snapshot["recent_downloads"] = get_recent_downloads()
        snapshot["recent_commands"] = get_recent_shell_commands(3)

    return snapshot


def update_app_time(data, app_name, seconds=30):
    """Track cumulative app usage time."""
    if not app_name:
        return
    if app_name not in data["app_time"]:
        data["app_time"][app_name] = 0
    data["app_time"][app_name] += seconds


# ─── Analysis ─────────────────────────────────────

def analyze_day(data):
    """Analyze a day's usage into patterns."""
    if not data["snapshots"]:
        return None

    # Top apps by time
    sorted_apps = sorted(data["app_time"].items(), key=lambda x: -x[1])
    top_apps = [(app, mins // 60, mins % 60) for app, mins in sorted_apps[:10]]

    # Hour distribution
    hour_apps = {}
    for snap in data["snapshots"]:
        h = snap.get("hour", 0)
        app = snap.get("active_app", "Unknown")
        if h not in hour_apps:
            hour_apps[h] = {}
        hour_apps[h][app] = hour_apps[h].get(app, 0) + 1

    # Peak hours (most active)
    hour_counts = {}
    for snap in data["snapshots"]:
        h = snap.get("hour", 0)
        hour_counts[h] = hour_counts.get(h, 0) + 1
    peak_hours = sorted(hour_counts.items(), key=lambda x: -x[1])[:5]

    # Unique window titles (deduplicated)
    unique_windows = list(set(
        snap.get("window", "") for snap in data["snapshots"]
        if snap.get("window")
    ))

    # All commands seen
    all_commands = []
    for snap in data["snapshots"]:
        all_commands.extend(snap.get("recent_commands", []))
    unique_commands = list(set(all_commands))

    return {
        "date": data["date"],
        "total_snapshots": len(data["snapshots"]),
        "hours_tracked": len(data["snapshots"]) * 30 / 3600,
        "top_apps": [(a, f"{m}h {s}m") for a, m, s in top_apps],
        "peak_hours": [(h, c) for h, c in peak_hours],
        "hour_app_map": {str(h): dict(sorted(apps.items(), key=lambda x: -x[1])[:3]) for h, apps in hour_apps.items()},
        "unique_windows": unique_windows[:30],
        "commands_used": unique_commands[:20],
    }


def generate_daily_summary(data):
    """Use Claude to generate insights from usage data."""
    analysis = analyze_day(data)
    if not analysis:
        return None

    claude_path = "/Users/tobiloba/.local/bin/claude"
    prompt = f"""Analyze this daily PC usage data for Tobiloba and provide:

1. **Routine patterns** — what does the day look like? When does he code, browse, communicate?
2. **Automation opportunities** — what repetitive tasks could Super Tobi automate?
3. **Productivity observations** — any context-switching, time sinks, or focus blocks?
4. **Suggested automations** — specific things Super Tobi could do proactively based on these patterns

DATA:
Top apps: {json.dumps(analysis['top_apps'])}
Peak hours: {json.dumps(analysis['peak_hours'])}
Hour-app map: {json.dumps(analysis['hour_app_map'])}
Commands: {json.dumps(analysis['commands_used'][:15])}
Windows: {json.dumps(analysis['unique_windows'][:20])}

Be concise and specific. Output structured markdown."""

    try:
        result = subprocess.run(
            [claude_path, "-p", prompt, "--max-turns", "1"],
            capture_output=True, text=True, timeout=60,
            cwd=str(BASE_DIR),
        )
        return result.stdout.strip()
    except Exception:
        return None


# ─── Pattern Learning ─────────────────────────────

def update_patterns():
    """Aggregate daily logs into learned patterns over time."""
    patterns = load_patterns()

    # Scan all daily files
    for daily_file in sorted(DAILY_DIR.glob("*.json")):
        day_key = daily_file.stem
        if day_key in patterns.get("days_processed", []):
            continue

        try:
            day_data = json.loads(daily_file.read_text())
            analysis = analyze_day(day_data)
            if not analysis:
                continue

            # Aggregate app usage
            for app, time_str in analysis["top_apps"]:
                if app not in patterns["app_totals"]:
                    patterns["app_totals"][app] = 0
                # Parse "Xh Ym"
                parts = time_str.split("h ")
                hours = int(parts[0]) if parts[0] else 0
                mins = int(parts[1].replace("m", "")) if len(parts) > 1 else 0
                patterns["app_totals"][app] += hours * 60 + mins

            # Aggregate hour patterns
            for hour, apps in analysis.get("hour_app_map", {}).items():
                if hour not in patterns["hour_patterns"]:
                    patterns["hour_patterns"][hour] = {}
                for app, count in apps.items():
                    patterns["hour_patterns"][hour][app] = patterns["hour_patterns"][hour].get(app, 0) + count

            # Track commands
            for cmd in analysis.get("commands_used", []):
                patterns["common_commands"][cmd] = patterns["common_commands"].get(cmd, 0) + 1

            patterns["days_processed"].append(day_key)
            patterns["total_days"] += 1

        except Exception:
            continue

    save_patterns(patterns)
    return patterns


def load_patterns():
    try:
        return json.loads(PATTERNS_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "total_days": 0,
            "days_processed": [],
            "app_totals": {},
            "hour_patterns": {},
            "common_commands": {},
            "learned_routines": [],
            "automation_suggestions": [],
        }


def save_patterns(patterns):
    USAGE_DIR.mkdir(parents=True, exist_ok=True)
    PATTERNS_FILE.write_text(json.dumps(patterns, indent=2, default=str))


# ─── CLI ──────────────────────────────────────────

def show_today():
    """Show today's usage summary."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()
    data = load_today()

    if not data["snapshots"]:
        console.print("[dim]No usage data yet today. Observer needs to run first.[/dim]")
        return

    analysis = analyze_day(data)
    if not analysis:
        return

    # App usage table
    table = Table(title=f"Usage — {data['date']}", box=box.ROUNDED)
    table.add_column("App", style="bold")
    table.add_column("Time", justify="right")
    for app, time_str in analysis["top_apps"]:
        table.add_row(app, time_str)
    console.print(table)

    # Peak hours
    console.print(f"\n[bold]Peak hours:[/bold] {', '.join(f'{h}:00 ({c} snapshots)' for h, c in analysis['peak_hours'])}")
    console.print(f"[bold]Tracked:[/bold] {analysis['hours_tracked']:.1f} hours ({analysis['total_snapshots']} snapshots)")


def show_patterns():
    """Show learned patterns across all days."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box

    console = Console()
    patterns = load_patterns()

    if patterns["total_days"] == 0:
        console.print("[dim]No patterns learned yet. Observer needs more data.[/dim]")
        return

    console.print(Panel(f"[bold]{patterns['total_days']} days[/bold] of usage data analyzed", title="Learned Patterns", border_style="cyan"))

    # Top apps all time
    sorted_apps = sorted(patterns["app_totals"].items(), key=lambda x: -x[1])
    table = Table(title="All-Time App Usage", box=box.ROUNDED)
    table.add_column("App", style="bold")
    table.add_column("Total Time", justify="right")
    for app, mins in sorted_apps[:15]:
        h, m = divmod(mins, 60)
        table.add_row(app, f"{h}h {m}m")
    console.print(table)

    # Hour patterns
    console.print("\n[bold]Typical day:[/bold]")
    for hour in sorted(patterns["hour_patterns"].keys(), key=int):
        apps = patterns["hour_patterns"][hour]
        top = sorted(apps.items(), key=lambda x: -x[1])[:2]
        app_str = ", ".join(f"{a}" for a, _ in top)
        console.print(f"  [dim]{int(hour):02d}:00[/dim] → {app_str}")

    # Top commands
    if patterns["common_commands"]:
        sorted_cmds = sorted(patterns["common_commands"].items(), key=lambda x: -x[1])
        console.print(f"\n[bold]Most used commands:[/bold]")
        for cmd, count in sorted_cmds[:10]:
            console.print(f"  [dim]{count}x[/dim] {cmd}")


def show_insights():
    """Generate AI insights from usage data."""
    from rich.console import Console
    from rich.panel import Panel
    console = Console()

    data = load_today()
    if len(data["snapshots"]) < 10:
        console.print("[dim]Need more data. Observer will build up snapshots throughout the day.[/dim]")
        return

    console.print("[cyan]Generating insights from today's usage...[/cyan]")
    summary = generate_daily_summary(data)
    if summary:
        console.print(Panel(summary, title="Daily Insights", border_style="magenta"))
    else:
        console.print("[yellow]Could not generate insights.[/yellow]")


# ─── Daemon Loop ──────────────────────────────────

def observe_loop(interval=30):
    """Main observation loop — runs every `interval` seconds."""
    log("Usage observer started")
    last_app = None
    snapshot_count = 0
    while True:
        try:
            data = load_today()
            snapshot = take_snapshot()
            data["snapshots"].append(snapshot)
            update_app_time(data, snapshot.get("active_app"), interval)
            snapshot_count += 1

            app = snapshot.get("active_app") or "idle"
            running = snapshot.get("running_apps", [])

            # Log every snapshot with app info
            app_time_min = data["app_time"].get(app, 0) // 60
            app_time_sec = data["app_time"].get(app, 0) % 60
            log(f"[{snapshot_count:04d}] {app} ({app_time_min}m{app_time_sec}s today) | {len(running)} apps running")

            # Log app switches
            if app != last_app and last_app is not None:
                log(f"  >> switched: {last_app} -> {app}")
            last_app = app

            # Track unique window titles
            window = snapshot.get("window")
            if window and window not in data["window_titles"]:
                data["window_titles"].append(window)
                log(f"  ++ new window: {window}")

            # Log periodic details (every 5 min)
            if snapshot.get("recent_commands"):
                log(f"  cmds: {', '.join(snapshot['recent_commands'][:3])}")
            if snapshot.get("recent_downloads"):
                for dl in snapshot["recent_downloads"]:
                    log(f"  ++ download: {dl['name']} ({dl['size_mb']}MB)")
            if snapshot.get("browser"):
                b = snapshot["browser"]
                log(f"  browser: {b['browser']} — {b['tabs']} tabs open")

            save_today(data)

            # End of day analysis (11 PM)
            now = datetime.now()
            if now.hour == 23 and now.minute == 0:
                log("Running end-of-day analysis...")
                summary = generate_daily_summary(data)
                if summary:
                    data["summary"] = summary
                    save_today(data)
                update_patterns()
                log("End-of-day analysis complete")

        except Exception as e:
            log(f"Observer error: {e}")

        time.sleep(interval)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        show_today()
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "--daemon":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        observe_loop(interval)
    elif cmd == "--today":
        show_today()
    elif cmd == "--patterns":
        show_patterns()
    elif cmd == "--insights":
        show_insights()
    elif cmd == "--snapshot":
        # Take one snapshot and print it
        snap = take_snapshot()
        print(json.dumps(snap, indent=2))
    elif cmd == "--analyze":
        update_patterns()
        show_patterns()
    else:
        print("Usage:")
        print("  usage_observer.py                — Show today's usage")
        print("  usage_observer.py --daemon [sec]  — Run observer (default 30s)")
        print("  usage_observer.py --today         — Today's summary")
        print("  usage_observer.py --patterns      — Learned patterns")
        print("  usage_observer.py --insights      — AI-powered insights")
        print("  usage_observer.py --snapshot       — Take one snapshot")
        print("  usage_observer.py --analyze       — Analyze all data")
