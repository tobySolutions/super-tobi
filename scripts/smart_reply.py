#!/usr/bin/env python3
"""
Super Tobi — Smart Reply Engine
Generates AI-powered replies that sound like Tobiloba, not templates.

How it works:
1. Reads conversation history from iMessage/Telegram/Discord
2. Loads Tobiloba's voice profile + past messaging patterns
3. Uses Claude API to generate a response AS Tobiloba
4. Optionally sends automatically or queues for approval

This is NOT template matching — it's full AI generation in Tobiloba's voice.
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
VOICE_DIR = os.path.join(DATA_DIR, "writing", "voice")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Contacts that Super Tobi can auto-reply to without approval
AUTO_REPLY_CONTACTS_FILE = os.path.join(DATA_DIR, "relationships", "smart_reply_config.json")


def load_voice_profile():
    """Load Tobiloba's writing/messaging voice characteristics."""
    voice_file = os.path.join(VOICE_DIR, "voice_analysis.md")
    if os.path.exists(voice_file):
        with open(voice_file) as f:
            return f.read()
    return ""


def load_messaging_patterns():
    """Load Tobiloba's past iMessage patterns to learn his casual texting style."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get Tobiloba's SENT messages to learn his texting style
        mac_epoch = datetime(2001, 1, 1)
        cutoff = datetime.now() - timedelta(days=30)
        cutoff_mac = int((cutoff - mac_epoch).total_seconds() * 1e9)

        query = """
        SELECT m.text
        FROM message m
        WHERE m.is_from_me = 1
        AND m.text IS NOT NULL
        AND m.text != ''
        AND m.date > ?
        ORDER BY m.date DESC
        LIMIT 200
        """

        cursor.execute(query, (cutoff_mac,))
        rows = cursor.fetchall()
        conn.close()

        return [row[0] for row in rows if row[0]]

    except Exception as e:
        print(f"Error loading messaging patterns: {e}", file=sys.stderr)
        return []


def get_conversation_context(contact, platform="imessage", limit=20):
    """Get recent conversation history with a specific contact."""
    if platform == "imessage":
        return get_imessage_conversation(contact, limit)
    return []


def get_imessage_conversation(contact, limit=20):
    """Get conversation thread from iMessage."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        mac_epoch = datetime(2001, 1, 1)

        query = """
        SELECT
            m.text,
            m.is_from_me,
            m.date
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        WHERE h.id LIKE ?
        AND m.text IS NOT NULL
        AND m.text != ''
        ORDER BY m.date DESC
        LIMIT ?
        """

        cursor.execute(query, (f"%{contact}%", limit))
        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            msg_date = mac_epoch + timedelta(seconds=row[2] / 1e9)
            sender = "Tobiloba" if row[1] else contact
            messages.append({
                "sender": sender,
                "text": row[0],
                "time": msg_date.strftime("%H:%M"),
            })

        return messages

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return []


def build_reply_prompt(contact, conversation, incoming_message, voice_profile, my_patterns):
    """Build the prompt for generating a smart reply."""

    # Sample of Tobiloba's texting patterns
    pattern_samples = "\n".join(f"- {p[:100]}" for p in my_patterns[:30])

    conversation_text = "\n".join(
        f"{'Tobiloba' if m['sender'] == 'Tobiloba' else m['sender']}: {m['text']}"
        for m in conversation[-15:]
    )

    prompt = f"""You are Tobiloba. You need to reply to a message in a conversation.

## Your texting style (from real messages you've sent)
{pattern_samples}

## Your voice profile
{voice_profile[:1500]}

## Key traits for messaging:
- You're casual and warm with friends
- You use "lol", "nah", "tbh", "fr", emoji sometimes but not excessively
- You're direct — you don't over-explain
- You match the energy of the conversation
- You sound like a real person texting, not an AI or a corporate bot
- You're Nigerian — you might use pidgin or local slang naturally
- Keep it SHORT — texts are short. Usually 1-3 sentences max.

## Current conversation with {contact}:
{conversation_text}

## New message from {contact}:
{incoming_message}

## Your task:
Reply as Tobiloba. Be natural. Match the vibe. Keep it short.
ONLY output the reply text — nothing else. No quotes, no explanation."""

    return prompt


def generate_reply(contact, incoming_message, platform="imessage"):
    """Generate an AI reply as Tobiloba."""
    voice_profile = load_voice_profile()
    my_patterns = load_messaging_patterns()
    conversation = get_conversation_context(contact, platform)

    prompt = build_reply_prompt(contact, conversation, incoming_message, voice_profile, my_patterns)

    # Use Claude via the Anthropic API or fall back to claude CLI
    # For now, output the prompt so Claude Code can process it
    return {
        "contact": contact,
        "platform": platform,
        "incoming": incoming_message,
        "conversation_length": len(conversation),
        "prompt": prompt,
        "patterns_loaded": len(my_patterns),
    }


def load_smart_reply_config():
    """Load smart reply configuration."""
    if os.path.exists(AUTO_REPLY_CONTACTS_FILE):
        with open(AUTO_REPLY_CONTACTS_FILE) as f:
            return json.load(f)
    return {
        "enabled": False,
        "mode": "queue",  # "queue" = needs approval, "auto" = sends immediately
        "contacts": {},
        "notes": "Add contacts and set mode to 'auto' for hands-free replies"
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Super Tobi Smart Reply")
    parser.add_argument("--contact", help="Contact to reply to")
    parser.add_argument("--message", help="Incoming message to reply to")
    parser.add_argument("--platform", default="imessage", choices=["imessage", "telegram", "discord"])
    parser.add_argument("--history", action="store_true", help="Just show conversation history")
    parser.add_argument("--patterns", action="store_true", help="Show Tobiloba's messaging patterns")

    args = parser.parse_args()

    if args.patterns:
        patterns = load_messaging_patterns()
        print(f"Loaded {len(patterns)} of Tobiloba's recent messages:\n")
        for p in patterns[:20]:
            print(f"  > {p[:100]}")
        return

    if args.history:
        convo = get_conversation_context(args.contact, args.platform)
        for m in convo:
            print(f"  [{m['time']}] {m['sender']}: {m['text']}")
        return

    if args.message:
        result = generate_reply(args.contact, args.message, args.platform)
        print(json.dumps(result, indent=2))
    else:
        # Get latest unread message from this contact and generate reply
        convo = get_conversation_context(args.contact, args.platform)
        if convo and convo[-1]["sender"] != "Tobiloba":
            last_msg = convo[-1]["text"]
            result = generate_reply(args.contact, last_msg, args.platform)
            print(json.dumps(result, indent=2))
        else:
            print("No pending message from this contact.")


if __name__ == "__main__":
    main()
