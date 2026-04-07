#!/usr/bin/env python3
"""
Super Tobi — Message Digest & Smart Reply Router

Three tiers of message handling:
1. DIGEST (default) — Summarize who texted, what they want, priority
2. AUTO-REPLY — AI responds as Tobiloba for listed contacts
3. NEVER-REPLY — Just notify, never touch (girlfriend, family, work)

The digest tells Tobiloba:
- Who texted
- What they're asking about / what they want
- How urgent it seems
- Suggested action (reply yourself, let AI handle, ignore)
"""

import os
import sys
import json
import sqlite3
import subprocess
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")
SMART_CONFIG = os.path.join(DATA_DIR, "relationships", "smart_reply_config.json")
DIGEST_LOG = os.path.join(DATA_DIR, "message_digests.json")
LAST_CHECK_FILE = os.path.join(DATA_DIR, "last_message_check.json")


def load_config():
    if os.path.exists(SMART_CONFIG):
        with open(SMART_CONFIG) as f:
            return json.load(f)
    return {"enabled": False, "default_mode": "digest", "auto_reply_contacts": [], "never_reply_contacts": []}


def get_contact_mode(contact_id, config):
    """Determine how to handle messages from this contact."""
    contact_lower = (contact_id or "").lower()

    # Check never-reply list first (family, girlfriend, important)
    for c in config.get("never_reply_contacts", []):
        if c.get("identifier", "").lower() in contact_lower or contact_lower in c.get("identifier", "").lower():
            return "never", c.get("name", contact_id)

    # Check auto-reply list
    for c in config.get("auto_reply_contacts", []):
        if c.get("identifier", "").lower() in contact_lower or contact_lower in c.get("identifier", "").lower():
            return "auto", c.get("name", contact_id)

    # Default: digest only
    return config.get("default_mode", "digest"), contact_id


def get_recent_imessages(since_hours=1):
    """Get recent inbound iMessages grouped by contact."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        return {}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        mac_epoch = datetime(2001, 1, 1)
        cutoff = datetime.now() - timedelta(hours=since_hours)
        cutoff_mac = int((cutoff - mac_epoch).total_seconds() * 1e9)

        query = """
        SELECT
            m.text,
            m.is_from_me,
            m.date,
            h.id as contact,
            c.display_name as chat_name
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        LEFT JOIN chat_message_join cmj ON m.rowid = cmj.message_id
        LEFT JOIN chat c ON cmj.chat_id = c.rowid
        WHERE m.date > ?
        AND m.text IS NOT NULL
        AND m.text != ''
        ORDER BY m.date ASC
        """

        cursor.execute(query, (cutoff_mac,))
        rows = cursor.fetchall()
        conn.close()

        # Group by contact
        conversations = defaultdict(list)
        for row in rows:
            msg_date = mac_epoch + timedelta(seconds=row[2] / 1e9)
            contact = row[3] or "Unknown"
            chat_name = row[4] or ""
            display = chat_name if chat_name else contact

            conversations[contact].append({
                "text": row[0],
                "is_from_me": bool(row[1]),
                "time": msg_date.strftime("%H:%M"),
                "timestamp": msg_date.isoformat(),
                "display_name": display,
            })

        return dict(conversations)

    except Exception as e:
        print(f"iMessage error: {e}", file=sys.stderr)
        return {}


def get_conversation_thread(contact_id, limit=15):
    """Get the last N messages in a conversation for context."""
    db_path = os.path.expanduser("~/Library/Messages/chat.db")
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        mac_epoch = datetime(2001, 1, 1)

        query = """
        SELECT m.text, m.is_from_me, m.date
        FROM message m
        LEFT JOIN handle h ON m.handle_id = h.rowid
        WHERE h.id LIKE ?
        AND m.text IS NOT NULL AND m.text != ''
        ORDER BY m.date DESC
        LIMIT ?
        """

        cursor.execute(query, (f"%{contact_id}%", limit))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "text": row[0],
                "sender": "Tobiloba" if row[1] else "them",
                "time": (mac_epoch + timedelta(seconds=row[2] / 1e9)).strftime("%H:%M"),
            }
            for row in reversed(rows)
        ]

    except Exception:
        return []


def analyze_message_intent(messages):
    """Quick heuristic analysis of what someone wants."""
    all_text = " ".join(m["text"] for m in messages if not m["is_from_me"]).lower()

    intents = []
    if "?" in all_text:
        intents.append("asking a question")
    if any(w in all_text for w in ["help", "can you", "could you", "please", "need"]):
        intents.append("requesting help")
    if any(w in all_text for w in ["urgent", "asap", "now", "emergency", "quickly"]):
        intents.append("seems urgent")
    if any(w in all_text for w in ["hi", "hey", "hello", "sup", "what's up", "how are"]):
        intents.append("greeting/checking in")
    if any(w in all_text for w in ["meet", "call", "hangout", "come", "let's", "link up"]):
        intents.append("wants to meet/call")
    if any(w in all_text for w in ["money", "pay", "send", "transfer", "owe"]):
        intents.append("money-related")
    if any(w in all_text for w in ["job", "role", "opportunity", "position", "hiring"]):
        intents.append("job/opportunity")
    if any(w in all_text for w in ["project", "build", "code", "repo", "pr", "merge"]):
        intents.append("project/code related")

    if not intents:
        intents.append("general message")

    return intents


def estimate_priority(messages, intents):
    """Estimate message priority: high, medium, low."""
    if "seems urgent" in intents or "money-related" in intents:
        return "high"
    if "requesting help" in intents or "job/opportunity" in intents or "wants to meet/call" in intents:
        return "medium"
    # Multiple messages = they're waiting
    inbound_count = sum(1 for m in messages if not m["is_from_me"])
    if inbound_count >= 3:
        return "medium"
    return "low"


def build_digest(hours_back=6):
    """Build a full message digest."""
    config = load_config()
    conversations = get_recent_imessages(hours_back)

    digest = {
        "generated_at": datetime.now().isoformat(),
        "hours_covered": hours_back,
        "contacts": [],
        "auto_replied": [],
        "needs_attention": [],
        "summary": "",
    }

    for contact_id, messages in conversations.items():
        inbound = [m for m in messages if not m["is_from_me"]]
        if not inbound:
            continue  # Skip conversations where only Tobiloba sent messages

        display_name = inbound[0].get("display_name", contact_id)
        mode, resolved_name = get_contact_mode(contact_id, config)
        if resolved_name != contact_id:
            display_name = resolved_name

        intents = analyze_message_intent(messages)
        priority = estimate_priority(messages, intents)

        last_message = inbound[-1]["text"]
        message_count = len(inbound)

        entry = {
            "contact": display_name,
            "contact_id": contact_id,
            "mode": mode,
            "message_count": message_count,
            "last_message": last_message[:200],
            "intents": intents,
            "priority": priority,
            "latest_time": inbound[-1].get("time", ""),
            "all_messages": [m["text"][:150] for m in inbound],
        }

        digest["contacts"].append(entry)

        if mode == "never":
            digest["needs_attention"].append(entry)
        elif mode == "auto":
            digest["auto_replied"].append(entry)
        else:
            # digest mode — just report
            if priority in ("high", "medium"):
                digest["needs_attention"].append(entry)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    digest["contacts"].sort(key=lambda x: priority_order.get(x["priority"], 3))
    digest["needs_attention"].sort(key=lambda x: priority_order.get(x["priority"], 3))

    # Build summary
    total = len(digest["contacts"])
    attention = len(digest["needs_attention"])
    auto = len(digest["auto_replied"])
    digest["summary"] = f"{total} conversations, {attention} need your attention, {auto} auto-replied"

    return digest


def format_digest(digest):
    """Format digest for display."""
    lines = []
    lines.append("╔══════════════════════════════════════════╗")
    lines.append("║       📨 SUPER TOBI MESSAGE DIGEST       ║")
    lines.append(f"║  {digest['summary']:^40}  ║")
    lines.append("╠══════════════════════════════════════════╣")

    if digest["needs_attention"]:
        lines.append("")
        lines.append("🔴 NEEDS YOUR ATTENTION")
        lines.append("─" * 42)
        for entry in digest["needs_attention"]:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(entry["priority"], "⚪")
            mode_tag = {"never": "👤 Personal", "digest": "📋 Digest", "auto": "🤖 Auto"}.get(entry["mode"], "")
            lines.append(f"  {priority_icon} {entry['contact']} ({entry['message_count']} msgs) [{mode_tag}]")
            lines.append(f"     What they want: {', '.join(entry['intents'])}")
            lines.append(f"     Last message: \"{entry['last_message'][:80]}\"")
            lines.append(f"     Time: {entry['latest_time']}")
            lines.append("")

    # Other messages (low priority, digest mode)
    other = [c for c in digest["contacts"] if c not in digest["needs_attention"] and c not in digest["auto_replied"]]
    if other:
        lines.append("🟢 OTHER MESSAGES")
        lines.append("─" * 42)
        for entry in other:
            lines.append(f"  💬 {entry['contact']} ({entry['message_count']} msgs)")
            lines.append(f"     \"{entry['last_message'][:80]}\"")
            lines.append("")

    if digest["auto_replied"]:
        lines.append("🤖 AUTO-REPLIED (by Super Tobi)")
        lines.append("─" * 42)
        for entry in digest["auto_replied"]:
            lines.append(f"  ✅ {entry['contact']} ({entry['message_count']} msgs)")
            lines.append(f"     They said: \"{entry['last_message'][:80]}\"")
            lines.append("")

    if not digest["contacts"]:
        lines.append("")
        lines.append("  No new messages. Inbox zero! 🎉")
        lines.append("")

    lines.append("╚══════════════════════════════════════════╝")
    return "\n".join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi Message Digest")
    parser.add_argument("--hours", type=int, default=6, help="Hours to look back")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    digest = build_digest(args.hours)

    if args.json:
        print(json.dumps(digest, indent=2))
    else:
        print(format_digest(digest))

    # Save digest
    if os.path.exists(DIGEST_LOG):
        with open(DIGEST_LOG) as f:
            logs = json.load(f)
    else:
        logs = []
    logs.append(digest)
    logs = logs[-50:]  # Keep last 50 digests
    with open(DIGEST_LOG, "w") as f:
        json.dump(logs, f, indent=2)


if __name__ == "__main__":
    main()
