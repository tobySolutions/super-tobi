#!/usr/bin/env python3
"""
Super Tobi — Outreach Engine
Generates personalized cold outreach messages to hiring managers and recruiters.
Uses company intel + job context to craft messages that don't sound like spam.

Channels: LinkedIn DM, Email, Twitter DM
"""

import json
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")
INTEL_DIR = os.path.join(BASE_DIR, "data", "career", "intel")
OUTREACH_DIR = os.path.join(BASE_DIR, "data", "career", "jobs", "outreach")
os.makedirs(OUTREACH_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

PROFILE_HOOKS = {
    "ai": "I've been building AI agent infrastructure at Idyllic Labs — harness engineering, multi-agent coordination, and security layers like MCPGuard (my thesis at UNILAG).",
    "solana": "I've shipped two Solana Foundation grants (x402-nextjs template, framework-kit), built sol-fuzz (AI security scanner for Anchor programs), and graduated from Solana Turbine.",
    "rust": "I've built an HTTP server and a Unix shell from scratch in Rust, plus zero-allocation Solana programs with Pinocchio.",
    "frontend": "I contributed to Million.js (16K+ stars) and was on JS Party, JavaScript Jabber, and Front-End Fire for that work.",
    "devrel": "I've done DevRel at Gaia AI and Fleek, co-founded Solana Students Africa, and spoken at OSCAFEST, DevFest Lagos, and CityJS.",
    "fullstack": "I build full-stack — React/Next.js on the frontend, Python/TypeScript/Rust on the backend. 255+ open source repos.",
    "default": "I'm a software engineer with 4+ years of experience across AI agent infrastructure, Solana, and full-stack development. Featured on JS Party and JavaScript Jabber.",
}


def _pick_hook(role):
    """Pick the most relevant profile hook based on the role title."""
    role_lower = role.lower()
    if any(kw in role_lower for kw in ["ai", "ml", "machine learning", "agent", "llm"]):
        return PROFILE_HOOKS["ai"]
    elif any(kw in role_lower for kw in ["solana", "blockchain", "web3", "smart contract", "protocol"]):
        return PROFILE_HOOKS["solana"]
    elif any(kw in role_lower for kw in ["rust", "systems"]):
        return PROFILE_HOOKS["rust"]
    elif any(kw in role_lower for kw in ["frontend", "front-end", "react"]):
        return PROFILE_HOOKS["frontend"]
    elif any(kw in role_lower for kw in ["devrel", "developer relations", "advocate"]):
        return PROFILE_HOOKS["devrel"]
    elif any(kw in role_lower for kw in ["fullstack", "full stack", "full-stack"]):
        return PROFILE_HOOKS["fullstack"]
    return PROFILE_HOOKS["default"]


def _load_intel(company):
    """Load company intel if available."""
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    path = os.path.join(INTEL_DIR, f"{slug}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def generate_linkedin_message(app):
    """Generate a LinkedIn DM to a hiring manager."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")
    hook = _pick_hook(role)
    intel = _load_intel(company)

    intel_context = ""
    if intel and intel.get("talking_points"):
        intel_context = f"\nCompany context: {intel['talking_points'][:300]}"

    prompt = f"""Write a short LinkedIn DM (under 100 words) from Tobiloba Adedeji to the hiring manager for:

Role: {role}
Company: {company}

Tobiloba's relevant hook: {hook}
{intel_context}

Rules:
- Open with something specific about the company or role (not "I hope this finds you well")
- Mention ONE concrete thing Tobiloba has built that's directly relevant
- End with a soft ask (not "please give me a chance")
- Sound like a real person, not a recruiter bot
- NO emojis, NO "I'm passionate about", NO "I'd love to connect"
- Keep it to 3-4 sentences max

Output ONLY the message text:"""

    return ask_claude(prompt, timeout=30)


def generate_email(app):
    """Generate a cold email to a hiring manager."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")
    hook = _pick_hook(role)
    intel = _load_intel(company)

    intel_context = ""
    if intel and intel.get("talking_points"):
        intel_context = f"\nCompany context: {intel['talking_points'][:300]}"

    prompt = f"""Write a cold email (under 150 words) from Tobiloba Adedeji to the hiring manager for:

Role: {role}
Company: {company}

Tobiloba's relevant hook: {hook}
Portfolio: tobysolutions.dev
GitHub: github.com/tobySolutions
{intel_context}

Rules:
- Subject line should be specific, not "Application for [Role]"
- Open with a specific observation about the company's work
- Show don't tell — link to one relevant project
- End with a clear, low-friction next step
- Sound confident, not desperate
- NO "Dear Hiring Manager", use a natural greeting
- Keep it short — busy people skim

Output as:
Subject: [subject line]

[email body]"""

    return ask_claude(prompt, timeout=30)


def generate_followup(app, days_since):
    """Generate a follow-up message after applying."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")

    prompt = f"""Write a follow-up message (under 80 words) for a job application submitted {days_since} days ago:

Role: {role}
Company: {company}

Rules:
- Don't re-explain who you are or re-pitch
- Reference the application briefly
- Add ONE new piece of value (e.g., "I just shipped X which is relevant to Y")
- Ask if there's a timeline for the process
- Sound human, not automated
- 2-3 sentences max

Output ONLY the message:"""

    return ask_claude(prompt, timeout=30)


def generate_twitter_dm(app):
    """Generate a Twitter/X DM to a company or team member."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")
    hook = _pick_hook(role)

    prompt = f"""Write a Twitter DM (under 80 words) from @toby_solutions about a role at {company}:

Role: {role}
Hook: {hook}

Rules:
- Twitter DMs are casual — write like a text message, not an email
- Reference something specific they tweeted or shipped if possible
- One sentence about what you've built that's relevant
- End with "happy to share more" or similar
- NO formal language

Output ONLY the DM:"""

    return ask_claude(prompt, timeout=30)


def outreach_for_job(app_index, channel="linkedin"):
    """Generate outreach for a specific application."""
    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    if app_index < 0 or app_index >= len(apps):
        print(f"Invalid index. You have {len(apps)} tracked jobs.")
        return

    app = apps[app_index]
    role = app.get("role", "?")
    company = app.get("company", "?")

    print(f"\n  Generating {channel} outreach for: {role} @ {company}...")

    if channel == "linkedin":
        msg = generate_linkedin_message(app)
    elif channel == "email":
        msg = generate_email(app)
    elif channel == "twitter":
        msg = generate_twitter_dm(app)
    elif channel == "followup":
        applied_date = app.get("applied_date", "")
        days = 0
        if applied_date:
            try:
                days = (datetime.now() - datetime.strptime(applied_date, "%Y-%m-%d")).days
            except ValueError:
                days = 7
        msg = generate_followup(app, days)
    else:
        print(f"Unknown channel: {channel}")
        return

    print(f"\n{'─' * 48}")
    print(msg)
    print(f"{'─' * 48}")

    # Save to outreach dir
    slug = re.sub(r"[^a-z0-9]+", "_", f"{company}_{role}".lower()).strip("_")
    filename = f"{slug}_{channel}_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(OUTREACH_DIR, filename)
    with open(filepath, "w") as f:
        f.write(f"# {channel.title()} — {role} @ {company}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(msg)

    print(f"\n  💾 Saved: {filepath}")
    return msg


def batch_followups(min_days=7, max_days=21):
    """Generate follow-ups for all applied jobs that haven't been followed up."""
    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    candidates = []
    for i, a in enumerate(apps):
        if a.get("status") != "applied":
            continue
        applied_date = a.get("applied_date", "")
        if not applied_date:
            continue
        try:
            days = (datetime.now() - datetime.strptime(applied_date, "%Y-%m-%d")).days
        except ValueError:
            continue
        if min_days <= days <= max_days and not a.get("follow_up_date"):
            candidates.append((i, a, days))

    if not candidates:
        print("No applications need follow-ups right now.")
        return

    print(f"  {len(candidates)} applications need follow-ups:\n")
    for i, (idx, app, days) in enumerate(candidates):
        print(f"  [{i+1}] {app.get('role','?'):40} @ {app.get('company','?'):20} ({days}d ago)")

    print(f"\n  Generating follow-up messages...\n")
    for idx, app, days in candidates:
        print(f"  → {app.get('role','?')} @ {app.get('company','?')} ({days}d)")
        try:
            outreach_for_job(idx, channel="followup")
        except Exception as e:
            print(f"    ❌ Error: {e}")
        print()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi — Outreach Engine")
    parser.add_argument("--linkedin", type=int, metavar="INDEX", help="Generate LinkedIn DM")
    parser.add_argument("--email", type=int, metavar="INDEX", help="Generate cold email")
    parser.add_argument("--twitter", type=int, metavar="INDEX", help="Generate Twitter DM")
    parser.add_argument("--followup", type=int, metavar="INDEX", help="Generate follow-up message")
    parser.add_argument("--batch-followups", action="store_true", help="Generate follow-ups for all overdue apps")
    parser.add_argument("--min-days", type=int, default=7, help="Min days since application for follow-up")
    parser.add_argument("--max-days", type=int, default=21, help="Max days since application for follow-up")
    args = parser.parse_args()

    if args.linkedin is not None:
        outreach_for_job(args.linkedin, "linkedin")
    elif args.email is not None:
        outreach_for_job(args.email, "email")
    elif args.twitter is not None:
        outreach_for_job(args.twitter, "twitter")
    elif args.followup is not None:
        outreach_for_job(args.followup, "followup")
    elif args.batch_followups:
        batch_followups(min_days=args.min_days, max_days=args.max_days)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
