#!/usr/bin/env python3
"""
Super Tobi — Message Aggregator
Reads messages from iMessage, Telegram, and Discord.
Can auto-reply on behalf of Tobiloba.

Platforms:
- iMessage: reads directly from ~/Library/Messages/chat.db (macOS native)
- Telegram: via Bot API (needs TELEGRAM_BOT_TOKEN)
- Discord: via Bot API (needs DISCORD_BOT_TOKEN)
- WhatsApp: via whatsapp-web.js bridge (needs setup)
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
MESSAGES_LOG = os.path.join(DATA_DIR, "messages_log.json")

# Ensure messages log exists
if not os.path.exists(MESSAGES_LOG):
    with open(MESSAGES_LOG, "w") as f:
        json.dump([], f)


# ─── iMessage ───────────────────────────────────────────────

def get_recent_imessages(hours_back=1):
    """Read recent iMessages from the macOS Messages database."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")

    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # macOS stores dates as nanoseconds since 2001-01-01
        # We need to convert to/from this format
        mac_epoch = datetime(2001, 1, 1)
        cutoff = datetime.now() - timedelta(hours=hours_back)
        cutoff_mac = int((cutoff - mac_epoch).total_seconds() * 1e9)

        query = """
        SELECT
            m.rowid,
            m.text,
            m.date,
            m.is_from_me,
            m.is_read,
            h.id as contact,
            c.display_name as chat_name
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.rowid
        WHERE m.date > ?
        ORDER BY m.date DESC
        LIMIT 50
        """

        cursor.execute(query, (cutoff_mac,))
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            msg_date = mac_epoch + timedelta(seconds=row[2] / 1e9)
            messages.append({
                "platform": "imessage",
                "id": str(row[0]),
                "text": row[1] or "",
                "timestamp": msg_date.isoformat(),
                "is_from_me": bool(row[3]),
                "is_read": bool(row[4]),
                "contact": row[5] or "Unknown",
                "chat_name": row[6] or "",
            })

        return messages

    except Exception as e:
        print(f"iMessage error: {e}", file=sys.stderr)
        return []


def send_imessage(contact, message):
    """Send an iMessage via AppleScript."""
    # Escape quotes in the message
    message = message.replace('"', '\\"')

    script = f'''
    tell application "Messages"
        set targetBuddy to "{contact}"
        set targetService to id of 1st account whose service type = iMessage
        set targetChat to participant targetBuddy of account id targetService
        send "{message}" to targetChat
    end tell
    '''

    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return True
        else:
            print(f"iMessage send error: {result.stderr}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"iMessage send error: {e}", file=sys.stderr)
        return False


# ─── Telegram ───────────────────────────────────────────────

def get_telegram_token():
    """Load Telegram bot token from config."""
    env_file = os.path.join(CONFIG_DIR, "api_keys.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("TELEGRAM_BOT_TOKEN=") and "pending" not in line:
                    token = line.strip().split("=", 1)[1]
                    if token and not token.startswith("#"):
                        return token
    return None


# ─── Discord ────────────────────────────────────────────────

def get_discord_token():
    """Load Discord bot token from config."""
    env_file = os.path.join(CONFIG_DIR, "api_keys.env")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("DISCORD_BOT_TOKEN=") and "pending" not in line:
                    token = line.strip().split("=", 1)[1]
                    if token and not token.startswith("#"):
                        return token
    return None


# ─── Aggregator ─────────────────────────────────────────────

def check_all_messages(hours_back=1):
    """Check all platforms for new messages."""
    all_messages = []

    # iMessage
    imessages = get_recent_imessages(hours_back)
    unread = [m for m in imessages if not m["is_from_me"] and not m["is_read"]]
    all_messages.extend(unread)

    # Telegram (if configured)
    tg_token = get_telegram_token()
    if tg_token:
        # Will be handled by the Telegram bot running separately
        pass

    # Discord (if configured)
    dc_token = get_discord_token()
    if dc_token:
        # Will be handled by the Discord bot running separately
        pass

    return all_messages


def format_message_summary(messages):
    """Format messages into a readable summary."""
    if not messages:
        return "No new messages."

    summary = []
    by_platform = {}
    for m in messages:
        platform = m["platform"]
        if platform not in by_platform:
            by_platform[platform] = []
        by_platform[platform].append(m)

    for platform, msgs in by_platform.items():
        icon = {"imessage": "💬", "telegram": "✈️", "discord": "🎮", "whatsapp": "📱"}.get(platform, "📨")
        summary.append(f"\n{icon} {platform.upper()} ({len(msgs)} new)")
        for m in msgs[:10]:  # Show max 10 per platform
            contact = m.get("contact", "Unknown")
            text = (m.get("text", "") or "")[:80]
            summary.append(f"  {contact}: {text}")

    return "\n".join(summary)


# ─── Auto-Reply Rules ──────────────────────────────────────

AUTO_REPLY_FILE = os.path.join(DATA_DIR, "relationships", "auto_reply_rules.json")


def load_auto_reply_rules():
    """Load auto-reply configuration."""
    if os.path.exists(AUTO_REPLY_FILE):
        with open(AUTO_REPLY_FILE) as f:
            return json.load(f)
    return {"enabled": False, "rules": []}


def should_auto_reply(message, rules):
    """Check if a message matches any auto-reply rule."""
    if not rules.get("enabled"):
        return None

    contact = message.get("contact", "").lower()

    for rule in rules.get("rules", []):
        rule_contact = rule.get("contact", "").lower()
        if rule_contact in contact or contact in rule_contact:
            return rule.get("reply_template")

    return None


# ─── CLI Interface ──────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Super Tobi Message Aggregator")
    parser.add_argument("--check", action="store_true", help="Check for new messages")
    parser.add_argument("--summary", action="store_true", help="Show message summary")
    parser.add_argument("--send", nargs=2, metavar=("CONTACT", "MESSAGE"), help="Send iMessage")
    parser.add_argument("--hours", type=int, default=1, help="Hours to look back")

    args = parser.parse_args()

    if args.check or args.summary:
        messages = check_all_messages(args.hours)
        print(format_message_summary(messages))

        # Log messages
        with open(MESSAGES_LOG) as f:
            log = json.load(f)
        log.extend(messages)
        # Keep only last 500 messages in log
        log = log[-500:]
        with open(MESSAGES_LOG, "w") as f:
            json.dump(log, f, indent=2)

    elif args.send:
        contact, message = args.send
        success = send_imessage(contact, message)
        print(f"{'✅ Sent' if success else '❌ Failed'}: {message[:50]}...")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
