#!/usr/bin/env python3
"""
Super Tobi — Greenhouse Email Verification
Polls Gmail for Greenhouse security codes and returns them.
Used by auto-apply to complete applications that require email verification.
"""

import base64
import os
import re
import time
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("gmail", "v1", credentials=creds)


def get_body(payload):
    """Recursively extract email body text."""
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="ignore")
    for part in payload.get("parts", []):
        result = get_body(part)
        if result:
            return result
    return ""


def extract_code_from_body(body):
    """Extract the verification code from a Greenhouse email body."""
    clean = re.sub(r"<[^>]+>", "\n", body)
    match = re.search(r"code.*?field.*?application[:\s]*\n\s*(\S+)", clean, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: look for an 8-char alphanumeric code on its own line
    for line in clean.splitlines():
        line = line.strip()
        if re.match(r"^[A-Za-z0-9]{8}$", line):
            return line
    return None


def get_verification_code(company, max_wait=120, poll_interval=10):
    """
    Poll Gmail for a Greenhouse verification code for a specific company.
    Waits up to max_wait seconds, polling every poll_interval seconds.
    Returns the code string or None.
    """
    service = get_gmail_service()
    query = f'subject:"security code" from:greenhouse subject:"{company}" newer_than:1h'

    elapsed = 0
    while elapsed < max_wait:
        try:
            results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
            messages = results.get("messages", [])

            if messages:
                full = service.users().messages().get(userId="me", id=messages[0]["id"], format="full").execute()
                body = get_body(full["payload"])
                code = extract_code_from_body(body)
                if code:
                    return code
        except Exception:
            pass

        time.sleep(poll_interval)
        elapsed += poll_interval

    return None


def get_all_pending_codes():
    """Get all recent verification codes (last hour) grouped by company."""
    service = get_gmail_service()
    query = 'subject:"security code" from:greenhouse newer_than:1h'

    results = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
    messages = results.get("messages", [])

    codes = {}
    for msg in messages:
        full = service.users().messages().get(userId="me", id=msg["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in full["payload"]["headers"]}
        subject = headers.get("Subject", "")
        company = subject.replace("Security code for your application to ", "")

        body = get_body(full["payload"])
        code = extract_code_from_body(body)

        if code and company not in codes:
            codes[company] = code

    return codes


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        company = sys.argv[1]
        print(f"Waiting for {company} verification code...")
        code = get_verification_code(company, max_wait=120)
        if code:
            print(f"Code: {code}")
        else:
            print("No code found within timeout.")
    else:
        codes = get_all_pending_codes()
        if codes:
            for company, code in codes.items():
                print(f"{company}: {code}")
        else:
            print("No pending verification codes in the last hour.")
