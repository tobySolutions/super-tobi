#!/usr/bin/env python3
"""
Super Tobi — Persistent Daemon
Runs on your Mac via launchd. Handles scheduled tasks:
- Morning daily sync
- Gmail expense scanning
- Birthday/anniversary checks
- Message aggregation polling
- Exercise reminders
"""

import os
import sys
import json
import logging
import schedule
import time
import subprocess
from datetime import datetime, date

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")

os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "daemon.log")),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("super-tobi")


def notify(title, message, sound="default"):
    """Send a macOS notification."""
    script = f'display notification "{message}" with title "{title}" sound name "{sound}"'
    subprocess.run(["osascript", "-e", script], capture_output=True)
    log.info(f"Notification: {title} — {message}")


def refresh_google_token():
    """Proactively refresh Google token before it expires."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        token_file = os.path.join(BASE_DIR, "config", "google_token.json")
        creds = Credentials.from_authorized_user_file(token_file)
        if creds.expired and creds.refresh_token:
            log.info("Google token expired, refreshing...")
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
            log.info(f"Google token refreshed, new expiry: {creds.expiry}")
        elif creds.valid:
            # Check if expiring within 10 minutes
            from datetime import timezone
            import datetime as dt
            now = dt.datetime.now(timezone.utc)
            expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry.tzinfo is None else creds.expiry
            remaining = (expiry - now).total_seconds()
            if remaining < 600:  # Less than 10 min
                log.info(f"Google token expiring in {remaining:.0f}s, refreshing...")
                creds.refresh(Request())
                with open(token_file, "w") as f:
                    f.write(creds.to_json())
                log.info(f"Google token refreshed, new expiry: {creds.expiry}")
    except Exception as e:
        log.error(f"Google token refresh failed: {e}")
        notify("⚠️ Google Token", "Token refresh failed! Run: python scripts/google_auth.py")


def check_birthdays():
    """Check for birthdays today and upcoming."""
    try:
        with open(os.path.join(DATA_DIR, "relationships", "birthdays.json")) as f:
            birthdays = json.load(f)

        today = date.today().strftime("%m-%d")

        for person in birthdays:
            if person.get("date") == today:
                name = person["name"]
                relationship = person.get("relationship", "")
                if relationship == "self":
                    notify("🎂 Happy Birthday!", "It's YOUR birthday today, Tobiloba! Celebrate yourself!")
                else:
                    notify(f"🎂 Birthday Alert!", f"It's {name}'s birthday today! Send them a message!")
                log.info(f"Birthday today: {name}")

            # Also check 3 days ahead
            from datetime import timedelta
            in_3_days = (date.today() + timedelta(days=3)).strftime("%m-%d")
            if person.get("date") == in_3_days:
                name = person["name"]
                notify(f"📅 Birthday in 3 days", f"{name}'s birthday is coming up on {person['date']}!")

    except Exception as e:
        log.error(f"Birthday check failed: {e}")


def scan_gmail_expenses():
    """Run the Gmail expense scanner."""
    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "gmail_expenses.py")],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            log.info(f"Gmail scan complete: {result.stdout.strip().split(chr(10))[-1]}")
        else:
            log.error(f"Gmail scan failed: {result.stderr}")
    except Exception as e:
        log.error(f"Gmail scan error: {e}")


def exercise_reminder():
    """Send daily exercise reminder."""
    try:
        with open(os.path.join(DATA_DIR, "health", "plan.json")) as f:
            plan = json.load(f)

        day = datetime.now().strftime("%A").lower()
        today_plan = plan.get("schedule", {}).get(day, {})
        focus = today_plan.get("focus", "Rest day")

        notify("💪 Time to Exercise!", f"Today's focus: {focus}")
    except Exception as e:
        log.error(f"Exercise reminder failed: {e}")


def check_messages():
    """Run message digest — summarize who texted, what they want, handle auto-replies."""
    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "message_digest.py"), "--hours", "1", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.stdout.strip():
            try:
                digest = json.loads(result.stdout)
                needs_attention = digest.get("needs_attention", [])
                if needs_attention:
                    names = ", ".join(e["contact"] for e in needs_attention[:3])
                    notify("📨 Messages Pending", f"{len(needs_attention)} need attention: {names}")
                    log.info(f"Message digest: {digest.get('summary', '')}")
            except json.JSONDecodeError:
                log.info(f"Messages: {result.stdout.strip()}")
    except Exception as e:
        log.error(f"Message digest failed: {e}")


def daily_job_hunt():
    """Autonomous job hunt — search boards and notify of new matches."""
    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "job_hunter.py"), "--hunt"],
            capture_output=True, text=True, timeout=300,
        )
        if result.returncode == 0:
            # Count new jobs
            import json as _json
            with open(os.path.join(DATA_DIR, "career", "jobs", "applications.json")) as f:
                apps = _json.load(f)
            new_today = [a for a in apps if a.get("discovered_date") == datetime.now().strftime("%Y-%m-%d")]
            if new_today:
                top = new_today[0]
                notify("💼 New Jobs Found!",
                       f"{len(new_today)} new matches. Top: {top['role']} @ {top['company']}")
            log.info(f"Job hunt complete: {len(new_today)} new jobs")
        else:
            log.error(f"Job hunt failed: {result.stderr[:200]}")
    except Exception as e:
        log.error(f"Job hunt error: {e}")


def pull_twitter_feed():
    """Pull Twitter feed — mentions, own tweets, trending topics."""
    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "twitter_feed.py"), "--full"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            log.info("Twitter feed pulled successfully")
            # Check for new mentions and notify
            import json as _json
            cache_file = os.path.join(DATA_DIR, "content", "twitter_feed.json")
            if os.path.exists(cache_file):
                with open(cache_file) as f:
                    cache = _json.load(f)
                mentions = cache.get("mentions", [])
                if mentions:
                    notify("🐦 Twitter", f"{len(mentions)} new mentions on Twitter")
        else:
            log.error(f"Twitter feed failed: {result.stderr[:200]}")
    except Exception as e:
        log.error(f"Twitter feed error: {e}")


def run_email_triage():
    """Run email triage — scan for rejections, responses, recruiter outreach."""
    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "email_triage.py"), "--days", "7"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            log.info(f"Email triage complete")
            # Check for rejections/responses in output
            out = result.stdout
            if "REJECTION" in out:
                import re
                rejections = re.findall(r'REJECTION: (.+?)$', out, re.MULTILINE)
                if rejections:
                    notify("❌ Job Update", f"{len(rejections)} rejection(s): {rejections[0][:40]}")
            if "RESPONSE" in out:
                import re
                responses = re.findall(r'RESPONSE: (.+?)$', out, re.MULTILINE)
                if responses:
                    notify("📩 Job Response!", f"{responses[0][:50]}")
        else:
            log.error(f"Email triage failed: {result.stderr[:200]}")
    except Exception as e:
        log.error(f"Email triage error: {e}")


def morning_sync():
    """Full morning sync routine."""
    log.info("=" * 50)
    log.info("MORNING SYNC STARTING")
    log.info("=" * 50)

    notify("🌅 Super Tobi", "Running morning sync...")

    check_birthdays()
    scan_gmail_expenses()
    run_email_triage()

    # Summary notification
    notify("✅ Morning Sync Complete", "Check Claude Code for full briefing — run /daily-sync")
    log.info("Morning sync complete")


def main():
    log.info("Super Tobi daemon starting...")
    notify("⚡ Super Tobi", "Daemon is now running!")

    # Schedule tasks
    schedule.every().day.at("08:00").do(morning_sync)
    schedule.every().day.at("09:00").do(exercise_reminder)
    schedule.every().day.at("17:00").do(exercise_reminder)  # Afternoon nudge
    schedule.every(6).hours.do(scan_gmail_expenses)
    schedule.every(30).minutes.do(check_messages)
    schedule.every().day.at("07:55").do(check_birthdays)
    schedule.every(3).hours.do(pull_twitter_feed)
    schedule.every().day.at("08:30").do(daily_job_hunt)
    schedule.every().day.at("14:00").do(daily_job_hunt)
    schedule.every(4).hours.do(run_email_triage)  # Check for job rejections/responses
    schedule.every(30).minutes.do(refresh_google_token)  # Keep Google token alive

    # Run birthday check immediately on startup
    check_birthdays()

    log.info("Scheduled tasks:")
    log.info("  08:00 — Morning sync (birthdays + gmail + briefing)")
    log.info("  09:00 — Exercise reminder")
    log.info("  17:00 — Exercise reminder (afternoon)")
    log.info("  Every 6h — Gmail expense scan")
    log.info("  Every 30m — Message check")
    log.info("  07:55 — Birthday check")

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
