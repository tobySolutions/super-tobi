#!/usr/bin/env python3
"""
Super Tobi — WhatsApp Webhook Server
Receives incoming WhatsApp messages via Meta's webhook system.
Integrates with the three-tier message handling:
- DIGEST: log and summarize
- AUTO-REPLY: generate AI reply and send back
- NEVER-REPLY: just notify Tobiloba via macOS notification + Telegram

Runs as a lightweight HTTP server on localhost.
Use ngrok or cloudflare tunnel to expose it to Meta's webhooks.
"""

import os
import sys
import json
import subprocess
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

from whatsapp_connector import parse_webhook_message, send_message, mark_as_read, log_message

DATA_DIR = os.path.join(BASE_DIR, "data")
SMART_CONFIG_FILE = os.path.join(DATA_DIR, "relationships", "smart_reply_config.json")

# Webhook verify token — set this to anything, just match it in Meta dashboard
VERIFY_TOKEN = "supertobi_webhook_2026"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("whatsapp-webhook")


def notify(title, message):
    """Send macOS notification."""
    script = f'display notification "{message}" with title "{title}" sound name "default"'
    subprocess.run(["osascript", "-e", script], capture_output=True)


def notify_telegram(message):
    """Forward notification to Telegram bot."""
    try:
        owner_file = os.path.join(BASE_DIR, "config", "telegram_owner.json")
        if os.path.exists(owner_file):
            with open(owner_file) as f:
                owner = json.load(f)
            chat_id = owner.get("owner_chat_id")
            if chat_id:
                env_file = os.path.join(BASE_DIR, "config", "api_keys.env")
                token = None
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("TELEGRAM_BOT_TOKEN=") and "#" not in line:
                            token = line.strip().split("=", 1)[1]
                if token:
                    import requests
                    requests.post(
                        f"https://api.telegram.org/bot{token}/sendMessage",
                        json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
                        timeout=10,
                    )
    except Exception as e:
        log.error(f"Telegram notify failed: {e}")


def load_smart_config():
    if os.path.exists(SMART_CONFIG_FILE):
        with open(SMART_CONFIG_FILE) as f:
            return json.load(f)
    return {"enabled": False, "auto_reply_contacts": [], "never_reply_contacts": []}


def get_contact_mode(phone_number, config):
    """Check which tier this contact belongs to."""
    for c in config.get("never_reply_contacts", []):
        if c.get("identifier", "") in phone_number or phone_number in c.get("identifier", ""):
            return "never", c.get("name", phone_number)

    for c in config.get("auto_reply_contacts", []):
        if c.get("identifier", "") in phone_number or phone_number in c.get("identifier", ""):
            return "auto", c.get("name", phone_number)

    return "digest", phone_number


def handle_incoming_message(msg):
    """Process an incoming WhatsApp message through the three-tier system."""
    config = load_smart_config()
    sender = msg.get("from_number", "")
    sender_name = msg.get("from_name", sender)
    text = msg.get("text", "")
    message_id = msg.get("message_id", "")

    mode, display_name = get_contact_mode(sender, config)

    # Log the message
    log_message("received", sender, text, message_id)

    log.info(f"[{mode.upper()}] {display_name}: {text[:80]}")

    if mode == "never":
        # Just notify — never reply
        notify(f"📱 WhatsApp from {display_name}", text[:100])
        notify_telegram(f"📱 *WhatsApp from {display_name}:*\n{text[:200]}")
        mark_as_read(message_id)

    elif mode == "auto":
        # AI-generated reply as Tobiloba using Claude Code
        try:
            sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
            from ai import ask_claude

            reply = ask_claude(
                f"You are Tobiloba replying to a WhatsApp message. Reply ONLY with the message text.\n"
                f"Be casual, warm, direct. Keep it short like real texting. "
                f"You're Nigerian, you might use pidgin naturally. NEVER sound like AI.\n\n"
                f"{display_name} said: {text}\n\n"
                f"Reply as Tobiloba:",
                timeout=20,
            )

            if reply and not reply.startswith("Error"):
                send_message(sender, reply)
                notify(f"🤖 Auto-replied to {display_name}", reply[:80])
                notify_telegram(
                    f"🤖 *WhatsApp auto-replied to {display_name}:*\n"
                    f"They said: \"{text[:100]}\"\n"
                    f"Super Tobi replied: \"{reply[:200]}\""
                )
            else:
                notify(f"📱 WhatsApp from {display_name}", text[:100])
                notify_telegram(f"📱 *WhatsApp from {display_name}:*\n{text[:200]}\n\n⚠️ AI reply failed: {reply}")

        except Exception as e:
            log.error(f"AI reply error: {e}")
            notify(f"📱 WhatsApp from {display_name}", text[:100])
            notify_telegram(f"📱 *WhatsApp from {display_name}:*\n{text[:200]}")

        mark_as_read(message_id)

    else:
        # Digest mode — just log and notify if seems important
        if any(w in text.lower() for w in ["urgent", "help", "asap", "?", "call"]):
            notify(f"📨 WhatsApp: {display_name}", text[:100])
            notify_telegram(f"📨 *WhatsApp from {display_name}:*\n{text[:200]}")
        mark_as_read(message_id)


class WebhookHandler(BaseHTTPRequestHandler):
    """Handle Meta webhook verification and incoming messages."""

    def do_GET(self):
        """Webhook verification — Meta sends a GET to verify the endpoint."""
        query = parse_qs(urlparse(self.path).query)

        mode = query.get("hub.mode", [None])[0]
        token = query.get("hub.verify_token", [None])[0]
        challenge = query.get("hub.challenge", [None])[0]

        if mode == "subscribe" and token == VERIFY_TOKEN:
            log.info("Webhook verified successfully!")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(challenge.encode())
        else:
            log.warning(f"Webhook verification failed. Token: {token}")
            self.send_response(403)
            self.end_headers()

    def do_POST(self):
        """Handle incoming webhook events (messages)."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        self.send_response(200)
        self.end_headers()

        try:
            data = json.loads(body)
            messages = parse_webhook_message(data)

            for msg in messages:
                handle_incoming_message(msg)

        except Exception as e:
            log.error(f"Webhook processing error: {e}")

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        pass


def main():
    port = 8091
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    log.info(f"WhatsApp webhook server running on port {port}")
    log.info(f"Verify token: {VERIFY_TOKEN}")
    log.info(f"Expose this with: ngrok http {port}")
    log.info("Or: cloudflared tunnel --url http://localhost:8091")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook server stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
