#!/usr/bin/env python3
"""
Super Tobi — WhatsApp Business Cloud API Connector
Handles reading and sending WhatsApp messages via the official Meta API.

Integrates with the three-tier message system:
- DIGEST: summarize who texted, what they want
- AUTO-REPLY: AI responds as Tobiloba for listed contacts
- NEVER-REPLY: just notify (Ore, family)
"""

import os
import sys
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
LOG_DIR = os.path.join(BASE_DIR, "logs")
WHATSAPP_LOG = os.path.join(DATA_DIR, "whatsapp_messages.json")

API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"


def load_whatsapp_config():
    """Load WhatsApp API credentials from config."""
    env_file = os.path.join(CONFIG_DIR, "api_keys.env")
    config = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                config[key.strip()] = val.strip()

    return {
        "access_token": config.get("WHATSAPP_ACCESS_TOKEN", ""),
        "phone_number_id": config.get("WHATSAPP_PHONE_NUMBER_ID", ""),
        "business_account_id": config.get("WHATSAPP_BUSINESS_ACCOUNT_ID", ""),
    }


def send_message(to_number, message_text):
    """
    Send a WhatsApp message to a phone number.
    to_number: international format without '+', e.g., '2348012345678'
    """
    config = load_whatsapp_config()

    if not config["access_token"] or not config["phone_number_id"]:
        print("Error: WhatsApp API credentials not configured.")
        print("Add WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID to config/api_keys.env")
        return None

    url = f"{BASE_URL}/{config['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": message_text,
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        result = response.json()

        if response.status_code == 200:
            msg_id = result.get("messages", [{}])[0].get("id", "unknown")
            log_message("sent", to_number, message_text, msg_id)
            return {"success": True, "message_id": msg_id}
        else:
            error = result.get("error", {}).get("message", "Unknown error")
            print(f"WhatsApp API error: {error}")
            return {"success": False, "error": error}

    except Exception as e:
        print(f"WhatsApp send error: {e}")
        return {"success": False, "error": str(e)}


def send_reaction(message_id, emoji):
    """React to a message with an emoji."""
    config = load_whatsapp_config()
    url = f"{BASE_URL}/{config['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "type": "reaction",
        "reaction": {
            "message_id": message_id,
            "emoji": emoji,
        },
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        return response.status_code == 200
    except Exception:
        return False


def mark_as_read(message_id):
    """Mark a message as read."""
    config = load_whatsapp_config()
    url = f"{BASE_URL}/{config['phone_number_id']}/messages"
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        return response.status_code == 200
    except Exception:
        return False


def get_media_url(media_id):
    """Get download URL for a media message (image, audio, document)."""
    config = load_whatsapp_config()
    url = f"{BASE_URL}/{media_id}"
    headers = {"Authorization": f"Bearer {config['access_token']}"}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        return response.json().get("url")
    except Exception:
        return None


def log_message(direction, contact, text, message_id=""):
    """Log a WhatsApp message to the messages file."""
    entry = {
        "platform": "whatsapp",
        "direction": direction,
        "contact": contact,
        "text": text[:500],
        "message_id": message_id,
        "timestamp": datetime.now().isoformat(),
    }

    if os.path.exists(WHATSAPP_LOG):
        with open(WHATSAPP_LOG) as f:
            logs = json.load(f)
    else:
        logs = []

    logs.append(entry)
    logs = logs[-1000:]  # Keep last 1000 messages

    with open(WHATSAPP_LOG, "w") as f:
        json.dump(logs, f, indent=2)


def get_business_profile():
    """Get the WhatsApp Business profile info."""
    config = load_whatsapp_config()
    url = f"{BASE_URL}/{config['phone_number_id']}/whatsapp_business_profile"
    headers = {"Authorization": f"Bearer {config['access_token']}"}
    params = {"fields": "about,address,description,email,profile_picture_url,websites,vertical"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


# ─── Webhook Handler ───────────────────────────────────────
# The webhook receives incoming messages from WhatsApp.
# This needs a public URL — we'll use a lightweight Flask/FastAPI server.

def parse_webhook_message(body):
    """Parse an incoming webhook payload from WhatsApp."""
    messages = []

    try:
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})

                # Get contact info
                contacts = {c["wa_id"]: c.get("profile", {}).get("name", c["wa_id"])
                           for c in value.get("contacts", [])}

                for msg in value.get("messages", []):
                    sender_id = msg.get("from", "")
                    sender_name = contacts.get(sender_id, sender_id)

                    parsed = {
                        "platform": "whatsapp",
                        "message_id": msg.get("id", ""),
                        "from_number": sender_id,
                        "from_name": sender_name,
                        "timestamp": msg.get("timestamp", ""),
                        "type": msg.get("type", "text"),
                    }

                    if msg.get("type") == "text":
                        parsed["text"] = msg.get("text", {}).get("body", "")
                    elif msg.get("type") == "image":
                        parsed["text"] = "[Image]"
                        parsed["media_id"] = msg.get("image", {}).get("id")
                        parsed["caption"] = msg.get("image", {}).get("caption", "")
                    elif msg.get("type") == "audio":
                        parsed["text"] = "[Voice note]"
                        parsed["media_id"] = msg.get("audio", {}).get("id")
                    elif msg.get("type") == "document":
                        parsed["text"] = f"[Document: {msg.get('document', {}).get('filename', 'file')}]"
                        parsed["media_id"] = msg.get("document", {}).get("id")
                    elif msg.get("type") == "location":
                        loc = msg.get("location", {})
                        parsed["text"] = f"[Location: {loc.get('latitude')}, {loc.get('longitude')}]"
                    elif msg.get("type") == "reaction":
                        parsed["text"] = f"[Reacted: {msg.get('reaction', {}).get('emoji', '')}]"
                    else:
                        parsed["text"] = f"[{msg.get('type', 'unknown')} message]"

                    messages.append(parsed)

    except Exception as e:
        print(f"Webhook parse error: {e}", file=sys.stderr)

    return messages


# ─── CLI ───────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi WhatsApp Connector")
    parser.add_argument("--send", nargs=2, metavar=("NUMBER", "MESSAGE"), help="Send a message")
    parser.add_argument("--profile", action="store_true", help="Show business profile")
    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--log", action="store_true", help="Show recent message log")

    args = parser.parse_args()

    if args.send:
        number, message = args.send
        result = send_message(number, message)
        if result and result.get("success"):
            print(f"✅ Message sent to {number}")
        else:
            print(f"❌ Failed: {result}")

    elif args.profile:
        profile = get_business_profile()
        print(json.dumps(profile, indent=2))

    elif args.test:
        config = load_whatsapp_config()
        if not config["access_token"]:
            print("❌ No WhatsApp access token configured")
            print("Add these to config/api_keys.env:")
            print("  WHATSAPP_ACCESS_TOKEN=your_token")
            print("  WHATSAPP_PHONE_NUMBER_ID=your_phone_id")
            print("  WHATSAPP_BUSINESS_ACCOUNT_ID=your_account_id")
            return
        profile = get_business_profile()
        if "error" not in profile:
            print("✅ WhatsApp Business API connected!")
            print(json.dumps(profile, indent=2))
        else:
            print(f"❌ Connection failed: {profile}")

    elif args.log:
        if os.path.exists(WHATSAPP_LOG):
            with open(WHATSAPP_LOG) as f:
                logs = json.load(f)
            for msg in logs[-20:]:
                direction = "→" if msg["direction"] == "sent" else "←"
                print(f"  {direction} {msg['contact']}: {msg['text'][:80]} ({msg['timestamp'][:16]})")
        else:
            print("No messages logged yet.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
