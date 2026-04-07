#!/usr/bin/env python3
"""
Super Tobi — Auto Apply
Applies to jobs using Claude Code CLI + Playwright with isolated browser contexts.
Resolves URLs first, then sends each application as a separate Claude task.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")
RESUME_PATH = os.path.join(BASE_DIR, "data", "career", "resume", "Tobiloba_Adedeji_Resume.pdf")
CLAUDE_PATH = "/Users/tobiloba/.local/bin/claude"
LOG_FILE = os.path.join(BASE_DIR, "logs", "auto_apply.log")

APPLICANT = """
- Name: Tobiloba Adedeji
- Email: adedejitobiloba7@gmail.com
- Phone: +2348029603888
- Location: Lagos, Nigeria
- Current Company: Idyllic Labs (AI Researcher)
- LinkedIn: https://www.linkedin.com/in/tobiloba-adedeji
- GitHub: https://github.com/tobySolutions
- Portfolio: https://tobysolutions.dev
- Twitter: https://twitter.com/toby_solutions
- Resume: {resume}
- Years of experience: 4+
- Education: University of Ilorin, Computer Science
- Work authorization: Will need sponsorship
- How did you hear: Job board
""".format(resume=RESUME_PATH)


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def load_apps():
    with open(APPLICATIONS_FILE) as f:
        return json.load(f)


def save_apps(apps):
    with open(APPLICATIONS_FILE, "w") as f:
        json.dump(apps, f, indent=2)


def get_apply_url(job):
    """Get the best URL to apply to."""
    return job.get("direct_apply_url") or job.get("url", "")


def _get_company_intel_context(company):
    """Load company intel if available and format it for the cover letter prompt."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    intel_path = os.path.join(BASE_DIR, "data", "career", "intel", f"{slug}.json")
    if not os.path.exists(intel_path):
        return ""
    try:
        with open(intel_path) as f:
            intel = json.load(f)
    except (json.JSONDecodeError, IOError):
        return ""

    parts = []
    if intel.get("cover_letter_hints"):
        parts.append(f"COVER LETTER INSIGHTS (from company research):\n{intel['cover_letter_hints']}")
    if intel.get("talking_points"):
        parts.append(f"KEY TALKING POINTS:\n{intel['talking_points']}")
    if intel.get("interview_notes"):
        parts.append(f"COMPANY CULTURE NOTES:\n{intel['interview_notes']}")

    # Also include raw snippets for extra context
    for section_key, label in [
        ("reddit_culture", "Reddit insights"),
        ("glassdoor", "Glassdoor insights"),
    ]:
        items = intel.get(section_key, [])
        if items:
            snippets = [f"- {item.get('snippet', '')[:150]}" for item in items[:3] if item.get("snippet")]
            if snippets:
                parts.append(f"{label}:\n" + "\n".join(snippets))

    if not parts:
        return ""
    return "\n\n".join(parts)


def _quick_research(company):
    """Run a quick research pass if no intel exists for a company."""
    import re
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    intel_path = os.path.join(BASE_DIR, "data", "career", "intel", f"{slug}.json")
    if os.path.exists(intel_path):
        return  # already have intel

    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
        from company_intel import research_company
        log(f"    Running quick research on {company}...")
        research_company(company)
    except Exception as e:
        log(f"    Quick research failed for {company}: {e}")


def apply_to_job(job):
    """Apply to a single job using Claude CLI with Playwright."""
    url = get_apply_url(job)
    role = job.get("role", "Unknown")
    company = job.get("company", "Unknown")

    # Check for company intel; run quick research if missing
    _quick_research(company)
    intel_context = _get_company_intel_context(company)

    # Generate a role-specific cover letter hint
    title_lower = role.lower()
    if any(kw in title_lower for kw in ["ai", "ml", "machine learning", "inference"]):
        cover_hint = "Highlight AI research at Idyllic Labs, LLM experience, Claude API, published research on AI agent architectures."
    elif any(kw in title_lower for kw in ["solana", "rust", "smart contract", "blockchain", "protocol"]):
        cover_hint = "Highlight Solana development with Anchor/Pinocchio, two executed Solana Foundation grants, Sol-Fuzz security scanner, TX-Indexer."
    elif any(kw in title_lower for kw in ["frontend", "fullstack", "full stack", "full-stack"]):
        cover_hint = "Highlight React/Next.js/TypeScript expertise, full-stack projects, tobysolutions.dev portfolio."
    elif any(kw in title_lower for kw in ["backend", "systems", "platform"]):
        cover_hint = "Highlight Python/TypeScript/Rust, distributed systems, API design, DevOps experience."
    else:
        cover_hint = "Highlight versatile engineering background spanning AI, blockchain, and full-stack development."

    # Append company-specific intel to the cover letter hint
    if intel_context:
        cover_hint += f"\n\nCOMPANY-SPECIFIC INTELLIGENCE:\n{intel_context}"

    prompt = f"""Apply to this job using Playwright browser automation. Use an ISOLATED browser context (do not reuse sessions).

URL: {url}
Role: {role}
Company: {company}

Steps:
1. Navigate to the URL
2. Find and click the "Apply" button if needed
3. Fill ALL form fields with the applicant details below
4. Upload the resume PDF
5. Write a 2-3 sentence cover letter if there's a field: {cover_hint}
6. Submit the form
7. If Greenhouse asks for an email verification code after submission:
   a. Wait 30 seconds for the email to arrive
   b. Run this command to get the code: /Users/tobiloba/super-tobi/.venv/bin/python /Users/tobiloba/super-tobi/scripts/greenhouse_verify.py "{company}"
   c. Enter the code in the verification field and resubmit
8. Take a screenshot to verify submission

APPLICANT DETAILS:
{APPLICANT}

IMPORTANT RULES:
- If the page is expired, 404, or says "no longer accepting applications", respond with EXACTLY: EXPIRED
- If a video recording is required, respond with EXACTLY: VIDEO_REQUIRED
- If login is required and you can't proceed, respond with EXACTLY: LOGIN_REQUIRED
- If Cloudflare blocks you, respond with EXACTLY: CLOUDFLARE_BLOCKED
- If the application is successfully submitted, respond with EXACTLY: APPLIED
- If blocked for any other reason, respond with EXACTLY: BLOCKED - <reason>
- Your response should START with one of these status words on the first line.
"""

    try:
        result = subprocess.run(
            [CLAUDE_PATH, "-p", prompt, "--max-turns", "30"],
            capture_output=True,
            text=True,
            timeout=300,  # 5 min max per application
            cwd=BASE_DIR,
        )
        output = result.stdout.strip()
        first_line = output.split("\n")[0].strip() if output else "BLOCKED - no output"
        return first_line, output
    except subprocess.TimeoutExpired:
        return "BLOCKED - timeout", ""
    except Exception as e:
        return f"BLOCKED - {e}", ""


def run(max_apps=10, min_score=20):
    """Run the auto-apply cycle."""
    from url_resolver import resolve_url, is_ats_url

    apps = load_apps()

    # Get candidates: discovered jobs, sorted by score
    candidates = [
        (i, app) for i, app in enumerate(apps)
        if app.get("status") == "discovered"
        and app.get("score", 0) >= min_score
    ]
    candidates.sort(key=lambda x: -x[1].get("score", 0))

    # Track companies we've already applied to or been blocked at
    already_touched = set()
    for a in apps:
        if a.get("status") in ("applied", "blocked", "rejected", "expired"):
            key = (a.get("company", "").lower().strip(), a.get("role", "").lower().strip())
            already_touched.add(key)

    # Also track companies with any application to avoid duplicate company spam
    companies_applied = set()
    for a in apps:
        if a.get("status") == "applied":
            companies_applied.add(a.get("company", "").lower().strip())

    log(f"Auto-apply starting: {len(candidates)} candidates, max {max_apps} applications")
    log(f"  Already touched: {len(already_touched)} company/role combos")

    applied = 0
    for idx, app in candidates:
        if applied >= max_apps:
            break

        url = get_apply_url(app)
        if not url:
            log(f"  SKIP (no URL): {app.get('role')} @ {app.get('company')}")
            continue

        # Skip if we already tried this exact company+role
        key = (app.get("company", "").lower().strip(), app.get("role", "").lower().strip())
        if key in already_touched:
            log(f"  SKIP (already tried): {app.get('role')} @ {app.get('company')}")
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + " Duplicate - already applied or attempted").strip()
            save_apps(apps)
            continue

        # Skip location-locked roles
        location = app.get("location", "").lower()
        notes = app.get("notes", "").lower()
        role_text = (app.get("role", "") + " " + location + " " + notes).lower()
        location_blocked = ["india-only", "india only", "us only", "us-only",
                           "must reside in", "security clearance", "no visa sponsorship",
                           "singapore only", "onsite only"]
        if any(kw in role_text for kw in location_blocked):
            log(f"  SKIP (location-locked): {app.get('role')} @ {app.get('company')} [{location}]")
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + " Auto-skipped: location-locked").strip()
            save_apps(apps)
            continue

        # Resolve URL if needed
        if not is_ats_url(url) and not app.get("direct_apply_url"):
            log(f"  Resolving URL for {app.get('role')} @ {app.get('company')}...")
            direct = resolve_url(url)
            if direct:
                app["direct_apply_url"] = direct
                save_apps(apps)
                log(f"    -> {direct[:70]}")
            else:
                log(f"    -> no direct URL, using original")

        role = app.get("role", "?")
        company = app.get("company", "?")
        score = app.get("score", 0)
        log(f"  APPLYING [{score}%]: {role} @ {company}")

        status, output = apply_to_job(app)
        log(f"    Result: {status}")

        if "APPLIED" in status:
            apps[idx]["status"] = "applied"
            apps[idx]["applied_date"] = datetime.now().strftime("%Y-%m-%d")
            applied += 1
        elif "EXPIRED" in status:
            apps[idx]["status"] = "expired"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + f" Auto-expired {datetime.now().strftime('%Y-%m-%d')}").strip()
        elif "VIDEO_REQUIRED" in status:
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + " Video recording required — apply manually").strip()
        elif "LOGIN_REQUIRED" in status:
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + " Login required — apply manually").strip()
        elif "CLOUDFLARE" in status:
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + " Cloudflare blocked — apply manually").strip()
        else:
            apps[idx]["status"] = "blocked"
            apps[idx]["notes"] = (apps[idx].get("notes", "") + f" Auto-apply failed: {status}").strip()

        save_apps(apps)

    log(f"Auto-apply complete: {applied} applied out of {min(max_apps, len(candidates))} attempted")
    return applied


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi Auto Apply")
    parser.add_argument("--max", type=int, default=10, help="Max applications to submit")
    parser.add_argument("--min-score", type=int, default=20, help="Minimum job score to apply")
    args = parser.parse_args()
    run(max_apps=args.max, min_score=args.min_score)
