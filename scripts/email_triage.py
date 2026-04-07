#!/usr/bin/env python3
"""
Super Tobi — Email Triage System
Scans Gmail, categorizes emails, detects job rejections/responses,
and surfaces important items.
"""

import os
import json
import re
import base64
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")
TRIAGE_FILE = os.path.join(BASE_DIR, "data", "email_triage.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ── Categories ──

CATEGORIES = {
    "job_rejection": {
        "queries": [
            'subject:"not moving forward"',
            'subject:"unfortunately"',
            'subject:"after careful consideration"',
            'subject:"we regret"',
            'subject:"not selected"',
            'subject:"application update"',
            'subject:"your application" "decided not"',
            'subject:"your application" "other candidates"',
            'subject:"position has been filled"',
            'subject:"will not be moving"',
            'from:greenhouse.io subject:"update"',
            'from:lever.co subject:"update"',
            'from:ashbyhq.com subject:"update"',
            'from:workable.com subject:"update"',
        ],
        "keywords": [
            "not moving forward", "unfortunately", "after careful consideration",
            "regret to inform", "not selected", "decided not to proceed",
            "other candidates", "position has been filled", "will not be",
            "we have decided", "not a fit", "pursued other candidates",
            "close your application", "decided to move forward with",
        ],
        "priority": "high",
    },
    "job_response": {
        "queries": [
            'subject:"interview" (schedule OR invitation OR availability)',
            'subject:"next steps" (application OR role OR position)',
            'subject:"coding challenge" OR subject:"take-home"',
            'subject:"assessment" (invitation OR complete)',
            'subject:"offer" (congratulations OR pleased)',
            'from:greenhouse.io subject:"interview"',
            'from:lever.co subject:"interview"',
            'from:calendly.com',
        ],
        "keywords": [
            "schedule an interview", "next steps", "coding challenge",
            "take-home", "assessment", "we'd like to", "move forward with you",
            "congratulations", "pleased to offer", "excited to invite",
            "availability for", "meet with our team",
        ],
        "priority": "urgent",
    },
    "recruiter": {
        "queries": [
            'subject:"opportunity" (engineer OR developer OR role)',
            'subject:"interested in" (role OR position OR opportunity)',
            'from:linkedin.com subject:"job"',
            'subject:"reaching out" (role OR position)',
        ],
        "keywords": [
            "reaching out", "opportunity", "perfect fit", "your profile",
            "interested in connecting", "role that matches",
        ],
        "priority": "high",
    },
    "github": {
        "queries": [
            'from:notifications@github.com',
        ],
        "keywords": [],
        "priority": "low",
    },
    "finance": {
        "queries": [
            'from:gtbank subject:"alert"',
            'from:guaranty subject:"notification"',
            'subject:"transaction" alert',
            'subject:"payment" (received OR confirmed)',
        ],
        "keywords": [
            "debit", "credit", "transaction", "transfer", "payment",
        ],
        "priority": "medium",
    },
}


def get_gmail_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def get_message_body(msg):
    """Extract plain text body from Gmail message."""
    payload = msg.get("payload", {})
    body = ""

    if payload.get("body", {}).get("data"):
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    elif payload.get("parts"):
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                body += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
            elif part.get("parts"):
                for subpart in part["parts"]:
                    if subpart.get("mimeType") == "text/plain" and subpart.get("body", {}).get("data"):
                        body += base64.urlsafe_b64decode(subpart["body"]["data"]).decode("utf-8", errors="replace")

    return body[:3000]  # Limit body size


def categorize_email(subject, sender, body):
    """Categorize an email based on subject, sender, and body content."""
    text = f"{subject} {sender} {body}".lower()

    for cat_name, cat_config in CATEGORIES.items():
        for kw in cat_config.get("keywords", []):
            if kw.lower() in text:
                return cat_name, cat_config["priority"]

    return "other", "low"


def match_to_application(subject, sender, body, apps):
    """Try to match an email to a tracked job application."""
    text = f"{subject} {sender} {body}".lower()

    matches = []
    for app in apps:
        company = app.get("company", "").lower()
        role = app.get("role", "").lower()

        if not company or company == "unknown":
            continue

        # Check if company name appears in the email
        if company in text:
            # Bonus if role also appears
            role_words = [w for w in role.split() if len(w) > 3]
            role_match = any(w.lower() in text for w in role_words)
            matches.append((app, role_match))

    if matches:
        # Prefer matches where role also matched
        role_matches = [m for m in matches if m[1]]
        if role_matches:
            return role_matches[0][0]
        return matches[0][0]

    return None


def update_application_status(app_id, new_status, note, apps):
    """Update a job application's status."""
    for app in apps:
        if app.get("id") == app_id:
            old_status = app.get("status")
            if old_status in ("applied", "action_needed", "discovered"):
                app["status"] = new_status
                timestamp = datetime.now().strftime("%Y-%m-%d")
                existing_notes = app.get("notes", "")
                app["notes"] = f"{existing_notes}\n{timestamp}: {note}".strip()
                return True
    return False


def triage(days=7, verbose=True):
    """Run email triage for the last N days."""
    service = get_gmail_service()

    # Load applications for matching
    apps = []
    if os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE) as f:
            apps = json.load(f)

    # Load existing triage to avoid re-processing
    existing_ids = set()
    if os.path.exists(TRIAGE_FILE):
        with open(TRIAGE_FILE) as f:
            existing = json.load(f)
            existing_ids = {e.get("id") for e in existing}
    else:
        existing = []

    results = {
        "rejections": [],
        "responses": [],
        "recruiter": [],
        "important": [],
        "new_triaged": 0,
    }

    # Search for job-related emails
    after_date = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")

    # Combined search queries for efficiency
    search_queries = [
        f'after:{after_date} (subject:"application" OR subject:"interview" OR subject:"not moving" OR subject:"unfortunately" OR subject:"next steps" OR subject:"opportunity" OR subject:"offer")',
        f'after:{after_date} (from:greenhouse.io OR from:lever.co OR from:ashbyhq.com OR from:workable.com OR from:recruitee.com)',
        f'after:{after_date} (from:linkedin.com subject:"job" OR subject:"role" OR subject:"position")',
        f'after:{after_date} subject:"coding challenge" OR subject:"take-home" OR subject:"assessment"',
    ]

    all_message_ids = set()
    for query in search_queries:
        try:
            resp = service.users().messages().list(
                userId="me", q=query, maxResults=50
            ).execute()
            for m in resp.get("messages", []):
                all_message_ids.add(m["id"])
        except Exception as e:
            if verbose:
                print(f"  Query error: {e}")

    if verbose:
        print(f"  Found {len(all_message_ids)} emails to triage")

    apps_modified = False

    for msg_id in all_message_ids:
        if msg_id in existing_ids:
            continue

        try:
            msg = service.users().messages().get(
                userId="me", id=msg_id, format="full"
            ).execute()

            headers = {h["name"]: h["value"] for h in msg["payload"].get("headers", [])}
            subject = headers.get("Subject", "")
            sender = headers.get("From", "")
            date = headers.get("Date", "")
            body = get_message_body(msg)

            category, priority = categorize_email(subject, sender, body)

            # Try to match to an application
            matched_app = match_to_application(subject, sender, body, apps)

            entry = {
                "id": msg_id,
                "subject": subject[:100],
                "from": sender[:100],
                "date": date,
                "category": category,
                "priority": priority,
                "matched_application": matched_app.get("id") if matched_app else None,
                "matched_company": matched_app.get("company") if matched_app else None,
                "triaged_at": datetime.now().isoformat(),
            }
            existing.append(entry)
            results["new_triaged"] += 1

            # Update application status if matched
            if matched_app and category == "job_rejection":
                updated = update_application_status(
                    matched_app["id"], "rejected",
                    f"Rejection email received: {subject[:60]}",
                    apps
                )
                if updated:
                    apps_modified = True
                    results["rejections"].append({
                        "company": matched_app.get("company"),
                        "role": matched_app.get("role"),
                        "subject": subject[:80],
                    })
                    if verbose:
                        print(f"  ❌ REJECTION: {matched_app.get('company')} — {matched_app.get('role', '')[:40]}")

            elif matched_app and category == "job_response":
                updated = update_application_status(
                    matched_app["id"], "responded",
                    f"Response received: {subject[:60]}",
                    apps
                )
                if updated:
                    apps_modified = True
                    results["responses"].append({
                        "company": matched_app.get("company"),
                        "role": matched_app.get("role"),
                        "subject": subject[:80],
                    })
                    if verbose:
                        print(f"  📩 RESPONSE: {matched_app.get('company')} — {subject[:50]}")

            elif category == "recruiter":
                results["recruiter"].append({
                    "from": sender[:50],
                    "subject": subject[:80],
                })
                if verbose:
                    print(f"  🤝 RECRUITER: {sender[:40]} — {subject[:40]}")

            elif priority in ("urgent", "high"):
                results["important"].append({
                    "from": sender[:50],
                    "subject": subject[:80],
                    "category": category,
                })

        except Exception as e:
            if verbose:
                print(f"  Error processing {msg_id}: {e}")

    # Save updated data
    with open(TRIAGE_FILE, "w") as f:
        json.dump(existing, f, indent=2)

    if apps_modified:
        with open(APPLICATIONS_FILE, "w") as f:
            json.dump(apps, f, indent=2)

    return results


def report(results, verbose=True):
    """Print triage report."""
    if not verbose:
        return

    print("\n╔══════════════════════════════════════════════╗")
    print("║       📧 SUPER TOBI — EMAIL TRIAGE            ║")
    print("╠══════════════════════════════════════════════╣")

    print(f"\n  📊 Triaged {results['new_triaged']} new emails")

    if results["rejections"]:
        print(f"\n  ❌ REJECTIONS ({len(results['rejections'])})")
        for r in results["rejections"]:
            print(f"    • {r['company']} — {r.get('role', '')[:40]}")

    if results["responses"]:
        print(f"\n  📩 RESPONSES ({len(results['responses'])})")
        for r in results["responses"]:
            print(f"    • {r['company']} — {r['subject'][:50]}")

    if results["recruiter"]:
        print(f"\n  🤝 RECRUITER OUTREACH ({len(results['recruiter'])})")
        for r in results["recruiter"]:
            print(f"    • {r['from'][:30]} — {r['subject'][:40]}")

    if results["important"]:
        print(f"\n  ⚡ IMPORTANT ({len(results['important'])})")
        for r in results["important"]:
            print(f"    • [{r['category']}] {r['from'][:30]} — {r['subject'][:40]}")

    if not any([results["rejections"], results["responses"], results["recruiter"], results["important"]]):
        print("\n  ✅ Nothing urgent in your inbox")

    print("\n╚══════════════════════════════════════════════╝")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi Email Triage")
    parser.add_argument("--days", type=int, default=30, help="How many days back to scan")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    args = parser.parse_args()

    print("  🔍 Scanning Gmail...")
    results = triage(days=args.days, verbose=not args.quiet)
    report(results, verbose=not args.quiet)

    # Return summary for daemon integration
    return results


if __name__ == "__main__":
    main()
