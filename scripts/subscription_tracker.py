#!/usr/bin/env python3
"""
Super Tobi — Subscription Tracker
Scans Gmail for recurring charges and tracks subscription spending.
"""

import argparse
import json
import os
import re
import base64
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")
SUBS_FILE = os.path.join(BASE_DIR, "data", "finance", "subscriptions.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

console = Console()

# Known subscription services and their search patterns
SUBSCRIPTION_SERVICES = [
    {"name": "Netflix", "queries": ["from:netflix", "subject:netflix payment"]},
    {"name": "Spotify", "queries": ["from:spotify", "subject:spotify receipt"]},
    {"name": "GitHub", "queries": ["from:github subject:receipt", "from:github subject:payment"]},
    {"name": "Claude", "queries": ["from:anthropic subject:receipt", "from:anthropic subject:payment", "subject:claude pro"]},
    {"name": "ChatGPT", "queries": ["from:openai subject:receipt", "from:openai subject:payment"]},
    {"name": "AWS", "queries": ["from:aws subject:invoice", "from:amazon web services subject:payment"]},
    {"name": "Google One", "queries": ["from:google subject:storage", "from:google subject:google one"]},
    {"name": "Apple", "queries": ["from:apple subject:receipt", "from:apple.com subject:subscription"]},
    {"name": "YouTube Premium", "queries": ["from:youtube subject:receipt", "subject:youtube premium"]},
    {"name": "Vercel", "queries": ["from:vercel subject:invoice", "from:vercel subject:receipt"]},
    {"name": "Notion", "queries": ["from:notion subject:receipt", "from:notion subject:invoice"]},
    {"name": "Figma", "queries": ["from:figma subject:receipt", "from:figma subject:invoice"]},
    {"name": "Linear", "queries": ["from:linear subject:receipt", "from:linear subject:invoice"]},
    {"name": "Cursor", "queries": ["from:cursor subject:receipt", "from:cursor subject:payment"]},
    {"name": "Cloudflare", "queries": ["from:cloudflare subject:invoice", "from:cloudflare subject:receipt"]},
    {"name": "DigitalOcean", "queries": ["from:digitalocean subject:invoice"]},
    {"name": "Heroku", "queries": ["from:heroku subject:invoice", "from:heroku subject:receipt"]},
    {"name": "Slack", "queries": ["from:slack subject:receipt", "from:slack subject:invoice"]},
    {"name": "Zoom", "queries": ["from:zoom subject:receipt", "from:zoom subject:payment"]},
    {"name": "1Password", "queries": ["from:1password subject:receipt"]},
    {"name": "Grammarly", "queries": ["from:grammarly subject:receipt"]},
    {"name": "Domain/Hosting", "queries": ["subject:domain renewal", "subject:hosting invoice"]},
    {"name": "Twitter/X", "queries": ["from:twitter subject:receipt", "from:x.com subject:receipt", "subject:x premium"]},
]


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("gmail", "v1", credentials=creds)


def extract_amount(text):
    """Extract monetary amount from email text."""
    patterns = [
        r'\$\s?([\d,]+\.?\d*)',
        r'USD\s?([\d,]+\.?\d*)',
        r'NGN\s?([\d,]+\.?\d*)',
        r'₦\s?([\d,]+\.?\d*)',
        r'N\s?([\d,]+\.?\d*)',
        r'(?:total|amount|charged?|price)[\s:]*(?:\$|USD|NGN|₦|N)?\s*([\d,]+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                val = float(amount_str)
                if val > 0:
                    return val
            except ValueError:
                continue
    return None


def detect_currency(text):
    """Detect currency from email text."""
    if re.search(r'NGN|₦', text, re.IGNORECASE):
        return "NGN"
    return "USD"


def detect_frequency(text):
    """Detect billing frequency from email text."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["annual", "yearly", "per year", "/year", "/yr"]):
        return "yearly"
    return "monthly"


def get_message_body(service, msg_id):
    """Get the plain text body of an email."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    date_str = headers.get("Date", "")
    body = ""
    payload = msg["payload"]
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    return {"subject": subject, "date": date_str, "body": body, "snippet": msg.get("snippet", "")}


def load_subs():
    try:
        with open(SUBS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"subscriptions": [], "last_scan": None}


def save_subs(data):
    os.makedirs(os.path.dirname(SUBS_FILE), exist_ok=True)
    with open(SUBS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def cmd_scan():
    """Scan Gmail for recurring subscription charges."""
    console.print(Panel("[bold cyan]Scanning Gmail for subscriptions...[/]", border_style="cyan"))

    service = get_gmail_service()
    after_date = (datetime.now() - timedelta(days=90)).strftime("%Y/%m/%d")

    data = load_subs()
    existing_names = {s["name"].lower() for s in data["subscriptions"]}
    found = []

    for svc in SUBSCRIPTION_SERVICES:
        for query in svc["queries"]:
            full_query = f"{query} after:{after_date}"
            try:
                results = service.users().messages().list(userId="me", q=full_query, maxResults=5).execute()
                messages = results.get("messages", [])
                if messages:
                    # Get the most recent message for details
                    details = get_message_body(service, messages[0]["id"])
                    full_text = f"{details['subject']} {details['snippet']} {details['body']}"
                    amount = extract_amount(full_text)
                    currency = detect_currency(full_text)
                    frequency = detect_frequency(full_text)

                    sub_entry = {
                        "name": svc["name"],
                        "amount": amount,
                        "currency": currency,
                        "frequency": frequency,
                        "last_charge_date": details["date"],
                        "occurrences_found": len(messages),
                        "added": datetime.now().isoformat(),
                        "source": "gmail-scan",
                    }
                    found.append(sub_entry)

                    status = "[yellow]UPDATE[/]" if svc["name"].lower() in existing_names else "[green]NEW[/]"
                    amt_str = f"{currency} {amount:,.2f}" if amount else "amount unknown"
                    console.print(f"  {status} {svc['name']} — {amt_str} ({frequency})")
                    break  # Found for this service, move to next
            except Exception:
                continue

    if not found:
        console.print("\n[dim]No subscription emails found in the last 90 days.[/]")
        console.print("[dim]Try adding subscriptions manually with --add[/]")
        return

    # Merge: update existing, add new
    existing_map = {s["name"].lower(): i for i, s in enumerate(data["subscriptions"])}
    for sub in found:
        key = sub["name"].lower()
        if key in existing_map:
            idx = existing_map[key]
            if sub["amount"]:
                data["subscriptions"][idx]["amount"] = sub["amount"]
            data["subscriptions"][idx]["last_charge_date"] = sub["last_charge_date"]
            data["subscriptions"][idx]["currency"] = sub["currency"]
            data["subscriptions"][idx]["frequency"] = sub["frequency"]
        else:
            data["subscriptions"].append(sub)

    data["last_scan"] = datetime.now().isoformat()
    save_subs(data)

    console.print(f"\n[bold green]Found {len(found)} subscriptions. Data saved.[/]")


def cmd_list():
    """List all tracked subscriptions."""
    data = load_subs()
    subs = data.get("subscriptions", [])

    if not subs:
        console.print("[dim]No subscriptions tracked. Run --scan or --add to get started.[/]")
        return

    table = Table(title="Subscriptions", box=box.ROUNDED)
    table.add_column("Service", style="bold")
    table.add_column("Amount", justify="right")
    table.add_column("Frequency", justify="center")
    table.add_column("Monthly Cost", justify="right", style="cyan")
    table.add_column("Last Charge", style="dim")

    total_monthly = 0.0

    for sub in sorted(subs, key=lambda s: s.get("name", "")):
        amount = sub.get("amount")
        frequency = sub.get("frequency", "monthly")
        currency = sub.get("currency", "USD")

        if amount:
            monthly = amount / 12 if frequency == "yearly" else amount
            total_monthly += monthly
            amt_str = f"{currency} {amount:,.2f}"
            monthly_str = f"{currency} {monthly:,.2f}"
        else:
            amt_str = "[dim]unknown[/]"
            monthly_str = "[dim]—[/]"

        last_charge = sub.get("last_charge_date") or "—"
        if len(last_charge) > 20:
            last_charge = last_charge[:20]

        table.add_row(sub.get("name", "?"), amt_str, frequency, monthly_str, last_charge)

    console.print(table)
    console.print(f"\n[bold]Total monthly spend:[/] [bold cyan]~{subs[0].get('currency', 'USD') if subs else 'USD'} {total_monthly:,.2f}[/]")

    if data.get("last_scan"):
        console.print(f"[dim]Last scan: {data['last_scan'][:19]}[/]")


def cmd_add(name, amount, frequency):
    """Manually add a subscription."""
    if frequency not in ("monthly", "yearly"):
        console.print("[red]Frequency must be 'monthly' or 'yearly'[/]")
        return

    data = load_subs()
    sub = {
        "name": name,
        "amount": float(amount),
        "currency": "USD",
        "frequency": frequency,
        "last_charge_date": None,
        "added": datetime.now().isoformat(),
        "source": "manual",
    }
    data["subscriptions"].append(sub)
    save_subs(data)

    monthly = float(amount) / 12 if frequency == "yearly" else float(amount)
    console.print(f"[green]Added:[/] {name} — ${float(amount):,.2f} ({frequency}) = ${monthly:,.2f}/mo")


def cmd_remove(name):
    """Remove a subscription by name."""
    data = load_subs()
    original_len = len(data["subscriptions"])
    data["subscriptions"] = [s for s in data["subscriptions"] if s["name"].lower() != name.lower()]

    if len(data["subscriptions"]) < original_len:
        save_subs(data)
        console.print(f"[green]Removed:[/] {name}")
    else:
        console.print(f"[red]Not found:[/] {name}")
        console.print("[dim]Available subscriptions:[/]")
        for s in data["subscriptions"]:
            console.print(f"  - {s['name']}")


def cmd_total():
    """Show total monthly spend."""
    data = load_subs()
    subs = data.get("subscriptions", [])

    if not subs:
        console.print("[dim]No subscriptions tracked.[/]")
        return

    total_monthly = 0.0
    total_yearly = 0.0

    for sub in subs:
        amount = sub.get("amount", 0) or 0
        frequency = sub.get("frequency", "monthly")
        if frequency == "yearly":
            total_yearly += amount
            total_monthly += amount / 12
        else:
            total_monthly += amount
            total_yearly += amount * 12

    console.print(Panel(
        f"[bold]Monthly:[/]  [cyan]${total_monthly:,.2f}[/]\n"
        f"[bold]Yearly:[/]   [cyan]${total_yearly:,.2f}[/]\n"
        f"[dim]{len(subs)} active subscriptions[/]",
        title="[bold]Subscription Spend[/]",
        border_style="cyan",
    ))


def main():
    parser = argparse.ArgumentParser(description="Super Tobi Subscription Tracker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--scan", action="store_true", help="Scan Gmail for recurring charges")
    group.add_argument("--list", action="store_true", help="List all tracked subscriptions")
    group.add_argument("--add", nargs=3, metavar=("NAME", "AMOUNT", "FREQUENCY"), help="Add a subscription")
    group.add_argument("--remove", metavar="NAME", help="Remove a subscription")
    group.add_argument("--total", action="store_true", help="Show total monthly spend")

    args = parser.parse_args()

    if args.scan:
        cmd_scan()
    elif args.list:
        cmd_list()
    elif args.add:
        cmd_add(args.add[0], args.add[1], args.add[2])
    elif args.remove:
        cmd_remove(args.remove)
    elif args.total:
        cmd_total()


if __name__ == "__main__":
    main()
