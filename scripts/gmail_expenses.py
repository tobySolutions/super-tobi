#!/usr/bin/env python3
"""
Super Tobi — Gmail Expense Scanner
Scans Gmail for transaction/expense notification emails and extracts amounts.
Works with Nigerian bank alerts (GTBank), payment confirmations, etc.
"""

import os
import json
import re
import base64
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")
TRANSACTIONS_FILE = os.path.join(BASE_DIR, "data", "finance", "transactions.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Search queries for financial emails
EXPENSE_QUERIES = [
    "from:gtbank subject:alert",
    "from:gtbank subject:debit",
    "from:gtbank subject:credit",
    "subject:transaction alert",
    "subject:debit alert",
    "subject:payment confirmation",
    "subject:receipt",
    "from:guaranty subject:notification",
]


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("gmail", "v1", credentials=creds)


def extract_amount(text):
    """Try to extract NGN or USD amounts from email text."""
    patterns = [
        r'NGN\s?([\d,]+\.?\d*)',
        r'N\s?([\d,]+\.?\d*)',
        r'₦\s?([\d,]+\.?\d*)',
        r'USD\s?([\d,]+\.?\d*)',
        r'\$\s?([\d,]+\.?\d*)',
        r'Amount:\s*(?:NGN|N|₦)?\s*([\d,]+\.?\d*)',
        r'(?:debit|credit)(?:ed)?.*?(?:NGN|N|₦)?\s*([\d,]+\.?\d*)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount_str = match.group(1).replace(",", "")
            try:
                return float(amount_str)
            except ValueError:
                continue
    return None


def extract_transaction_type(text):
    """Determine if debit or credit."""
    text_lower = text.lower()
    # Known expense sources — receipts from these are always expenses
    if any(w in text_lower for w in ["chowdeck", "grey"]):
        return "expense"
    if any(w in text_lower for w in ["debit", "spent", "paid", "purchase", "withdrawal", "transfer to"]):
        return "expense"
    if any(w in text_lower for w in ["credit", "received", "deposit", "transfer from", "salary"]):
        return "income"
    return "expense"  # default to expense


def extract_category(text):
    """Auto-categorize based on known merchants."""
    text_lower = text.lower()
    if "chowdeck" in text_lower:
        return "food"
    if "grey" in text_lower:
        return "fintech"
    if "solana foundation" in text_lower:
        return "crypto"
    return "auto-detected"


def get_message_body(service, msg_id):
    """Get the plain text body of an email."""
    msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()

    headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
    subject = headers.get("Subject", "")
    date = headers.get("Date", "")
    sender = headers.get("From", "")

    # Extract body
    body = ""
    payload = msg["payload"]

    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    return {
        "subject": subject,
        "date": date,
        "sender": sender,
        "body": body,
        "snippet": msg.get("snippet", ""),
    }


def scan_expenses(days_back=30, verbose=True):
    """Scan Gmail for expense emails from the last N days."""
    service = get_gmail_service()

    after_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y/%m/%d")

    all_messages = []

    for query in EXPENSE_QUERIES:
        full_query = f"{query} after:{after_date}"
        try:
            results = service.users().messages().list(userId="me", q=full_query, maxResults=20).execute()
            messages = results.get("messages", [])
            all_messages.extend(messages)
        except Exception as e:
            if verbose:
                print(f"  Query failed: {query} — {e}")

    # Deduplicate by message ID
    seen = set()
    unique_messages = []
    for msg in all_messages:
        if msg["id"] not in seen:
            seen.add(msg["id"])
            unique_messages.append(msg)

    if verbose:
        print(f"Found {len(unique_messages)} financial emails from the last {days_back} days\n")

    transactions = []

    for msg in unique_messages:
        try:
            details = get_message_body(service, msg["id"])
            full_text = f"{details['subject']} {details['snippet']} {details['body']}"

            amount = extract_amount(full_text)
            tx_type = extract_transaction_type(full_text)

            if amount and amount > 0:
                category = extract_category(full_text)
                tx = {
                    "date": details["date"],
                    "type": tx_type,
                    "amount": amount,
                    "currency": "NGN",
                    "category": category,
                    "description": details["subject"][:100],
                    "source": "gmail-scan",
                }
                transactions.append(tx)

                if verbose:
                    icon = "📥" if tx_type == "income" else "📤"
                    print(f"  {icon} ₦{amount:,.2f} — {tx_type} — {details['subject'][:60]}")
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Could not parse message: {e}")

    return transactions


def main():
    print("Super Tobi — Gmail Expense Scanner")
    print("=" * 40)

    transactions = scan_expenses(days_back=30)

    if not transactions:
        print("\nNo financial transactions found in recent emails.")
        print("This could mean:")
        print("  - GTBank alerts go to a different email")
        print("  - Email format doesn't match expected patterns")
        print("  - No transactions in the last 30 days")
        return

    # Load existing transactions
    with open(TRANSACTIONS_FILE) as f:
        existing = json.load(f)

    # Append new (avoiding duplicates by description + date)
    existing_keys = {(t.get("description", ""), t.get("date", "")) for t in existing}
    new_count = 0
    for tx in transactions:
        key = (tx["description"], tx["date"])
        if key not in existing_keys:
            existing.append(tx)
            new_count += 1

    with open(TRANSACTIONS_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    total_expenses = sum(t["amount"] for t in transactions if t["type"] == "expense")
    total_income = sum(t["amount"] for t in transactions if t["type"] == "income")

    print(f"\n{'=' * 40}")
    print(f"📊 Summary (last 30 days)")
    print(f"  Income:   ₦{total_income:,.2f}")
    print(f"  Expenses: ₦{total_expenses:,.2f}")
    print(f"  New transactions logged: {new_count}")


if __name__ == "__main__":
    main()
