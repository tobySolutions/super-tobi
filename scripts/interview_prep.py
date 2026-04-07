#!/usr/bin/env python3
"""
Super Tobi — Interview Prep Engine
AI-powered mock interviews, question generation, and answer coaching.
Uses company intel + job description to generate targeted prep.
"""

import json
import os
import re
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")
INTEL_DIR = os.path.join(BASE_DIR, "data", "career", "intel")
PREP_DIR = os.path.join(BASE_DIR, "data", "career", "jobs", "interview_prep")
os.makedirs(PREP_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))


def _load_intel(company):
    slug = re.sub(r"[^a-z0-9]+", "_", company.lower()).strip("_")
    path = os.path.join(INTEL_DIR, f"{slug}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def generate_questions(app):
    """Generate likely interview questions for a specific role."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")
    jd = app.get("job_description", "")
    intel = _load_intel(company)

    intel_context = ""
    if intel:
        if intel.get("interview_prep"):
            snippets = [item.get("snippet", "")[:200] for item in intel["interview_prep"][:3]]
            intel_context += f"\nInterview intel from Reddit/Glassdoor:\n" + "\n".join(f"- {s}" for s in snippets)
        if intel.get("interview_notes"):
            intel_context += f"\nInterview notes:\n{intel['interview_notes'][:500]}"

    jd_section = f"\nJob description:\n{jd[:2000]}" if jd else ""

    prompt = f"""Generate 15 likely interview questions for:

Role: {role}
Company: {company}
{jd_section}
{intel_context}

Tobiloba's background:
- AI Researcher at Idyllic Labs (agent coordination, harness engineering)
- Solana developer (Anchor, Pinocchio, two Foundation grants)
- Full-stack (React/Next.js/TypeScript/Python/Rust)
- MCPGuard thesis (MCP security)
- Million.js contributor (16K+ stars, podcast features)
- Based in Lagos, Nigeria

Generate questions in these categories:
1. Technical (5 questions) — specific to the role's tech stack
2. System Design (3 questions) — relevant to the company's domain
3. Behavioral (4 questions) — STAR format expected
4. Culture Fit (3 questions) — specific to this company's values

For each question, provide:
- The question
- A brief hint on what they're looking for
- Which of Tobiloba's experiences to reference

Format as markdown with ## headers for each category."""

    return ask_claude(prompt, max_turns=1, timeout=60)


def mock_interview(app, question=None):
    """Run an interactive mock interview session."""
    from ai import ask_claude

    role = app.get("role", "Unknown")
    company = app.get("company", "Unknown")

    if question:
        # Score a specific answer
        prompt = f"""You are interviewing for {role} at {company}. 
The candidate (Tobiloba Adedeji) just answered this question:

Question: {question}

Score the answer on:
1. Relevance (does it address the question?)
2. Specificity (concrete examples vs vague statements?)
3. Impact (does it show measurable results?)
4. Structure (clear beginning, middle, end?)

Give an overall score out of 10 and specific improvement suggestions.
Keep it under 200 words."""

        return ask_claude(prompt, timeout=30)
    else:
        # Generate a single question and wait for answer
        prompt = f"""You are a senior interviewer at {company} hiring for {role}.
Ask ONE technical or behavioral interview question that would be typical for this role.
Make it specific to the company's domain.
Output ONLY the question, nothing else."""

        return ask_claude(prompt, timeout=15)


def prep_for_job(app_index):
    """Generate a full interview prep package for a specific job."""
    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    if app_index < 0 or app_index >= len(apps):
        print(f"Invalid index. You have {len(apps)} tracked jobs.")
        return

    app = apps[app_index]
    role = app.get("role", "?")
    company = app.get("company", "?")

    print(f"\n  🎯 Generating interview prep for: {role} @ {company}...")

    questions = generate_questions(app)

    # Save prep
    slug = re.sub(r"[^a-z0-9]+", "_", f"{company}_{role}".lower()).strip("_")
    filename = f"{slug}_{datetime.now().strftime('%Y%m%d')}.md"
    filepath = os.path.join(PREP_DIR, filename)

    with open(filepath, "w") as f:
        f.write(f"# Interview Prep: {role} @ {company}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(questions)

    print(f"\n{questions}")
    print(f"\n  💾 Saved: {filepath}")
    return filepath


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi — Interview Prep")
    parser.add_argument("--prep", type=int, metavar="INDEX", help="Generate full prep for job at index")
    parser.add_argument("--mock", type=int, metavar="INDEX", help="Start mock interview for job at index")
    parser.add_argument("--list-upcoming", action="store_true", help="List jobs in interview stage")
    args = parser.parse_args()

    if args.prep is not None:
        prep_for_job(args.prep)
    elif args.mock is not None:
        with open(APPLICATIONS_FILE) as f:
            apps = json.load(f)
        app = apps[args.mock]
        print(f"\n  🎤 Mock interview: {app.get('role','?')} @ {app.get('company','?')}\n")
        q = mock_interview(app)
        print(f"  Q: {q}\n")
        print("  (Type your answer, then run --mock again to get a new question)")
    elif args.list_upcoming:
        with open(APPLICATIONS_FILE) as f:
            apps = json.load(f)
        interviews = [(i, a) for i, a in enumerate(apps) if a.get("status") in ("interviewing", "interview")]
        if interviews:
            for i, a in interviews:
                print(f"  [{i}] {a.get('role','?'):40} @ {a.get('company','?')}")
        else:
            print("  No interviews scheduled yet.")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
