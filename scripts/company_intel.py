#!/usr/bin/env python3
"""
Super Tobi -- Company Intelligence
Gathers Reddit, Glassdoor, and web intelligence about companies
to improve job applications with targeted insights.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from urllib.parse import quote_plus

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INTEL_DIR = os.path.join(DATA_DIR, "career", "intel")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "career", "jobs", "applications.json")
CLAUDE_PATH = "/Users/tobiloba/.local/bin/claude"

console = Console()

os.makedirs(INTEL_DIR, exist_ok=True)


def _load_brave_api_key():
    """Load Brave Search API key from environment or config file."""
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        env_file = os.path.join(BASE_DIR, "config", "api_keys.env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("BRAVE_API_KEY="):
                        api_key = line.strip().split("=", 1)[1]
                        break
    return api_key


def brave_search(query, count=10):
    """Run a Brave Search API query and return results."""
    api_key = _load_brave_api_key()
    if not api_key:
        console.print("[red]No BRAVE_API_KEY found in environment or config/api_keys.env[/]")
        return []
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    try:
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params={"q": query, "count": count},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        return r.json().get("web", {}).get("results", [])
    except Exception as e:
        console.print(f"[red]Brave search error:[/] {e}")
        return []


def slugify(name):
    """Convert company name to a file-safe slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def get_intel_path(company):
    """Get the path for a company's intel file."""
    return os.path.join(INTEL_DIR, f"{slugify(company)}.json")


def has_intel(company):
    """Check if intel already exists for a company."""
    return os.path.exists(get_intel_path(company))


def load_intel(company):
    """Load existing intel for a company."""
    path = get_intel_path(company)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_intel(company, data):
    """Save intel data for a company."""
    path = get_intel_path(company)
    data["company"] = company
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


# ---- Research Functions ----

def search_reddit_culture(company):
    """Search Reddit for company culture and work-life balance threads."""
    query = f'site:reddit.com "{company}" interview OR culture OR salary OR "work life balance"'
    results = brave_search(query, count=8)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", "")[:300],
        }
        for r in results
    ]


def search_glassdoor(company):
    """Search Glassdoor for company reviews, interview info, and salary data."""
    query = f'site:glassdoor.com "{company}" reviews OR interview OR salary'
    results = brave_search(query, count=8)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", "")[:300],
        }
        for r in results
    ]


def search_interview_prep(company):
    """Search Reddit for interview process details and coding challenge info."""
    query = f'site:reddit.com "{company}" interview process OR coding challenge OR system design'
    results = brave_search(query, count=8)
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", "")[:300],
        }
        for r in results
    ]


def research_company(company):
    """Full research pass on a company. Returns structured intel dict."""
    console.print(f"\n[bold cyan]Researching:[/] {company}\n")

    with console.status("[bold]Searching Reddit for culture info..."):
        reddit_culture = search_reddit_culture(company)
    console.print(f"  Reddit culture threads: {len(reddit_culture)}")

    with console.status("[bold]Searching Glassdoor..."):
        glassdoor = search_glassdoor(company)
    console.print(f"  Glassdoor results: {len(glassdoor)}")

    with console.status("[bold]Searching for interview prep..."):
        interview = search_interview_prep(company)
    console.print(f"  Interview prep threads: {len(interview)}")

    intel = {
        "company": company,
        "researched_date": datetime.now().strftime("%Y-%m-%d"),
        "reddit_culture": reddit_culture,
        "glassdoor": glassdoor,
        "interview_prep": interview,
    }

    path = save_intel(company, intel)
    console.print(f"\n[green]Intel saved:[/] {path}")

    # Display summary
    _display_intel(intel)
    return intel


def _display_intel(intel):
    """Display a nicely formatted intel report."""
    company = intel.get("company", "Unknown")

    # Reddit culture
    if intel.get("reddit_culture"):
        table = Table(title="Reddit -- Culture & Reviews", box=box.SIMPLE, show_lines=False)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("URL", style="dim", max_width=40)
        for r in intel["reddit_culture"][:5]:
            table.add_row(r["title"][:50], r["url"][:40])
        console.print(table)

    # Glassdoor
    if intel.get("glassdoor"):
        table = Table(title="Glassdoor -- Reviews & Salary", box=box.SIMPLE, show_lines=False)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("URL", style="dim", max_width=40)
        for r in intel["glassdoor"][:5]:
            table.add_row(r["title"][:50], r["url"][:40])
        console.print(table)

    # Interview prep
    if intel.get("interview_prep"):
        table = Table(title="Interview Prep", box=box.SIMPLE, show_lines=False)
        table.add_column("Title", style="bold", max_width=50)
        table.add_column("URL", style="dim", max_width=40)
        for r in intel["interview_prep"][:5]:
            table.add_row(r["title"][:50], r["url"][:40])
        console.print(table)

    # AI-generated insights
    if intel.get("cover_letter_hints"):
        console.print(Panel(intel["cover_letter_hints"], title="Cover Letter Hints", border_style="green"))
    if intel.get("interview_notes"):
        console.print(Panel(intel["interview_notes"], title="Interview Notes", border_style="cyan"))
    if intel.get("salary_range"):
        console.print(Panel(intel["salary_range"], title="Salary Intel", border_style="yellow"))
    if intel.get("talking_points"):
        console.print(Panel(intel["talking_points"], title="Key Talking Points", border_style="magenta"))


# ---- Prep Package ----

def prep_company(company, role):
    """Full application prep: research + AI-generated prep materials."""
    # Run research first
    intel = research_company(company)

    # Compile all snippets into context for Claude
    context_parts = []
    for section_key, section_label in [
        ("reddit_culture", "Reddit culture threads"),
        ("glassdoor", "Glassdoor reviews"),
        ("interview_prep", "Interview prep threads"),
    ]:
        items = intel.get(section_key, [])
        if items:
            context_parts.append(f"\n## {section_label}")
            for item in items[:5]:
                context_parts.append(f"- {item['title']}: {item['snippet']}")

    context = "\n".join(context_parts)

    prompt = f"""You are helping Tobiloba Adedeji prepare to apply for the role of {role} at {company}.

Here is intelligence gathered from Reddit and Glassdoor:
{context}

Tobiloba's background:
- AI Researcher at Idealik (Idyllic Labs)
- Solana builder (Anchor, Pinocchio, Rust), co-founder Solana Students Africa
- Two executed Solana Foundation grants
- Strong open source contributor, full-stack engineer (React, Next.js, TypeScript, Python)
- Website: tobysolutions.dev

Generate the following (use plain, direct language, no filler):

### COVER LETTER HINTS
3-5 bullet points on what to emphasize in a cover letter for this company, based on their culture and values.

### INTERVIEW NOTES
What to expect in the interview process based on the intel. Common question types, focus areas.

### SALARY RANGE
Any salary data found. If none, say "No salary data found in search results."

### TALKING POINTS
5 key talking points that connect Tobiloba's experience to what this company values.

Output each section with the ### header exactly as shown."""

    console.print("\n[bold cyan]Generating prep package with Claude...[/]")
    try:
        result = subprocess.run(
            [CLAUDE_PATH, "-p", prompt, "--max-turns", "3"],
            capture_output=True, text=True, timeout=120,
            cwd=BASE_DIR,
        )
        output = result.stdout.strip()
    except subprocess.TimeoutExpired:
        output = "Claude timed out generating prep package."
    except Exception as e:
        output = f"Error running Claude: {e}"

    # Parse the sections from Claude's output
    sections = {
        "cover_letter_hints": "",
        "interview_notes": "",
        "salary_range": "",
        "talking_points": "",
    }

    section_map = {
        "COVER LETTER HINTS": "cover_letter_hints",
        "INTERVIEW NOTES": "interview_notes",
        "SALARY RANGE": "salary_range",
        "TALKING POINTS": "talking_points",
    }

    current_key = None
    current_lines = []
    for line in output.split("\n"):
        matched = False
        for header, key in section_map.items():
            if header in line.upper():
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = key
                current_lines = []
                matched = True
                break
        if not matched and current_key:
            current_lines.append(line)
    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    # Save the AI-generated content into intel
    intel.update(sections)
    intel["prep_role"] = role
    intel["prep_date"] = datetime.now().strftime("%Y-%m-%d")
    path = save_intel(company, intel)

    console.print(f"\n[green]Prep package saved:[/] {path}")
    _display_intel(intel)
    return intel


# ---- Batch Research ----

def batch_research(min_score=50):
    """Research all discovered jobs with score >= min_score that lack intel."""
    if not os.path.exists(APPLICATIONS_FILE):
        console.print("[red]No applications file found.[/]")
        return

    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    # Find companies that need research
    companies_seen = set()
    targets = []
    for app in apps:
        if app.get("status") != "discovered":
            continue
        if app.get("score", 0) < min_score:
            continue
        company = app.get("company", "").strip()
        if not company or company == "Unknown":
            continue
        if company.lower() in companies_seen:
            continue
        if has_intel(company):
            continue
        companies_seen.add(company.lower())
        targets.append(company)

    if not targets:
        console.print("[dim]No companies need research (all top jobs already have intel, or none qualify).[/]")
        return

    console.print(f"[bold]Batch research: {len(targets)} companies to research[/]\n")
    for i, company in enumerate(targets, 1):
        console.print(f"\n[bold]({i}/{len(targets)})[/]")
        try:
            research_company(company)
        except Exception as e:
            console.print(f"[red]Error researching {company}:[/] {e}")


# ---- CLI ----

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi -- Company Intelligence")
    parser.add_argument("--research", metavar="COMPANY", help="Research a company")
    parser.add_argument("--prep", nargs=2, metavar=("COMPANY", "ROLE"), help="Full prep package for company + role")
    parser.add_argument("--batch", action="store_true", help="Batch research all top discovered jobs")
    parser.add_argument("--min-score", type=int, default=50, help="Minimum score for batch research (default: 50)")
    parser.add_argument("--show", metavar="COMPANY", help="Show existing intel for a company")

    args = parser.parse_args()

    if args.research:
        research_company(args.research)
    elif args.prep:
        prep_company(args.prep[0], args.prep[1])
    elif args.batch:
        batch_research(min_score=args.min_score)
    elif args.show:
        intel = load_intel(args.show)
        if intel:
            _display_intel(intel)
        else:
            console.print(f"[dim]No intel found for {args.show}. Run --research first.[/]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
