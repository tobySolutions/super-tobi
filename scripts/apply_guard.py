#!/usr/bin/env python3
"""
Super Tobi — Apply Guard
Checks if a job has already been applied to before attempting.
Updates tracker after successful application.
"""

import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")


def load_apps():
    with open(APPLICATIONS_FILE) as f:
        return json.load(f)


def save_apps(apps):
    with open(APPLICATIONS_FILE, "w") as f:
        json.dump(apps, f, indent=2)


def check_already_applied(company, role=None, url=None):
    """Check if we already applied to this company/role. Returns the entry if found."""
    apps = load_apps()
    company_lower = company.lower().strip()

    for a in apps:
        # Check by URL
        if url and a.get("url", "").strip() == url.strip():
            if a.get("status") in ("applied", "rejected", "responded"):
                return a

        # Check by company + role
        if a.get("company", "").lower().strip() == company_lower:
            if role and a.get("role", "").lower().strip() == role.lower().strip():
                if a.get("status") in ("applied", "rejected", "responded"):
                    return a

    return None


def mark_applied(company, role, url=None, notes=""):
    """Mark a job as applied in the tracker."""
    apps = load_apps()
    today = datetime.now().strftime("%Y-%m-%d")
    updated = False

    for a in apps:
        match = False
        if url and a.get("url", "").strip() == url.strip():
            match = True
        elif (a.get("company", "").lower().strip() == company.lower().strip() and
              a.get("role", "").lower().strip() == role.lower().strip()):
            match = True

        if match and a.get("status") in ("action_needed", "discovered", "blocked"):
            a["status"] = "applied"
            a["applied_date"] = today
            a["notes"] = (a.get("notes", "") + f"\n{today}: {notes}").strip()
            updated = True
            print(f"✅ Updated: {a['company']} — {a['role']} → applied")
            break

    if not updated:
        # Add new entry
        entry = {
            "id": f"job-{len(apps)+1:04d}",
            "type": "job",
            "company": company,
            "role": role,
            "url": url or "",
            "location": "",
            "salary": "",
            "score": 0,
            "board": "Manual",
            "status": "applied",
            "discovered_date": today,
            "applied_date": today,
            "follow_up_date": None,
            "notes": notes,
        }
        apps.append(entry)
        print(f"✅ New entry: {company} — {role} → applied")

    save_apps(apps)


def mark_blocked(company, role, reason, url=None):
    """Mark a job as blocked."""
    apps = load_apps()
    today = datetime.now().strftime("%Y-%m-%d")

    for a in apps:
        match = False
        if url and a.get("url", "").strip() == url.strip():
            match = True
        elif (a.get("company", "").lower().strip() == company.lower().strip() and
              a.get("role", "").lower().strip() == role.lower().strip()):
            match = True

        if match and a.get("status") in ("action_needed", "discovered"):
            a["status"] = "blocked"
            a["notes"] = (a.get("notes", "") + f"\n{today}: {reason}").strip()
            print(f"⚠️ Blocked: {a['company']} — {a['role']} ({reason})")
            break

    save_apps(apps)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: apply_guard.py check <company> [role]")
        print("       apply_guard.py applied <company> <role> [notes]")
        print("       apply_guard.py blocked <company> <role> <reason>")
        sys.exit(1)

    action = sys.argv[1]
    if action == "check":
        company = sys.argv[2]
        role = sys.argv[3] if len(sys.argv) > 3 else None
        existing = check_already_applied(company, role)
        if existing:
            print(f"⛔ ALREADY {existing['status'].upper()}: {existing['company']} — {existing['role']}")
            print(f"   Applied: {existing.get('applied_date', '?')}")
            sys.exit(1)
        else:
            print(f"✅ Clear to apply: {company}" + (f" — {role}" if role else ""))
            sys.exit(0)
    elif action == "applied":
        company = sys.argv[2]
        role = sys.argv[3]
        notes = sys.argv[4] if len(sys.argv) > 4 else "Applied via Playwright automation"
        mark_applied(company, role, notes=notes)
    elif action == "blocked":
        company = sys.argv[2]
        role = sys.argv[3]
        reason = sys.argv[4] if len(sys.argv) > 4 else "Unknown"
        mark_blocked(company, role, reason)
