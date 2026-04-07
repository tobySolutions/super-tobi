#!/usr/bin/env python3
"""
Super Tobi — Resume Tailor
Generates role-specific, ATS-optimized resumes for each job application.
Inspired by AIHawk's dynamic resume generation (29K stars).

Features:
- ATS keyword extraction from job descriptions
- Resume scoring against JD before/after tailoring
- Markdown -> PDF generation
- Per-job resume versioning
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME_DIR = os.path.join(BASE_DIR, "data", "career", "resume")
TAILORED_DIR = os.path.join(RESUME_DIR, "tailored")
BASE_RESUME = os.path.join(RESUME_DIR, "current_resume.md")
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")

os.makedirs(TAILORED_DIR, exist_ok=True)

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))


# ─── ATS Keyword Extraction ───────────────────────────────

# Common technical keywords grouped by domain
KEYWORD_DOMAINS = {
    "ai_ml": [
        "machine learning", "deep learning", "neural network", "nlp", "natural language",
        "llm", "large language model", "transformer", "gpt", "claude", "openai",
        "tensorflow", "pytorch", "hugging face", "fine-tuning", "rag", "retrieval",
        "embeddings", "vector database", "inference", "model serving", "mlops",
        "ai agent", "autonomous agent", "multi-agent", "mcp", "model context protocol",
        "reinforcement learning", "computer vision", "prompt engineering",
    ],
    "blockchain": [
        "solana", "ethereum", "blockchain", "smart contract", "web3", "defi",
        "anchor", "rust", "pinocchio", "token", "nft", "dao", "protocol",
        "on-chain", "transaction", "validator", "consensus", "cryptography",
        "svm", "evm", "move", "staking", "amm", "dex",
    ],
    "backend": [
        "python", "rust", "go", "java", "node.js", "typescript", "javascript",
        "api", "rest", "graphql", "grpc", "microservices", "distributed systems",
        "database", "postgresql", "mongodb", "redis", "kafka", "rabbitmq",
        "docker", "kubernetes", "aws", "gcp", "azure", "ci/cd", "terraform",
        "system design", "scalability", "performance", "concurrency",
    ],
    "frontend": [
        "react", "next.js", "typescript", "javascript", "html", "css",
        "tailwind", "vue", "angular", "svelte", "astro", "webpack", "vite",
        "responsive", "accessibility", "ux", "ui", "component", "design system",
    ],
    "devrel": [
        "developer relations", "developer advocate", "developer experience",
        "documentation", "technical writing", "community", "open source",
        "content creation", "tutorial", "workshop", "conference", "hackathon",
        "sdk", "api documentation", "developer tools",
    ],
}


def extract_keywords_from_jd(job_description):
    """Extract relevant keywords from a job description."""
    jd_lower = job_description.lower()
    found = {}

    for domain, keywords in KEYWORD_DOMAINS.items():
        matched = []
        for kw in keywords:
            if kw in jd_lower:
                matched.append(kw)
        if matched:
            found[domain] = matched

    # Also extract years of experience requirements
    exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|exp)', jd_lower)
    if exp_match:
        found["years_required"] = int(exp_match.group(1))

    # Extract specific tools/frameworks not in our list
    tool_patterns = [
        r'\b(langchain|langgraph|crewai|autogen|dspy|llamaindex)\b',
        r'\b(supabase|firebase|prisma|drizzle|sqlalchemy)\b',
        r'\b(playwright|selenium|puppeteer|cypress)\b',
        r'\b(vercel|netlify|cloudflare|fly\.io|railway)\b',
    ]
    for pattern in tool_patterns:
        matches = re.findall(pattern, jd_lower)
        if matches:
            found.setdefault("tools", []).extend(matches)

    return found


def score_resume_against_jd(resume_text, job_description):
    """Score how well a resume matches a job description (0-100)."""
    keywords = extract_keywords_from_jd(job_description)
    resume_lower = resume_text.lower()

    total_keywords = 0
    matched_keywords = 0

    for domain, kws in keywords.items():
        if domain in ("years_required",):
            continue
        for kw in kws:
            total_keywords += 1
            if kw in resume_lower:
                matched_keywords += 1

    if total_keywords == 0:
        return 50  # No keywords found, neutral score

    base_score = (matched_keywords / total_keywords) * 100

    # Bonus for having many matches
    if matched_keywords >= 10:
        base_score = min(100, base_score + 10)

    return round(base_score)


def tailor_resume(job, job_description=None):
    """Generate a tailored resume for a specific job using Claude."""
    from ai import ask_claude

    role = job.get("role", job.get("title", "Unknown"))
    company = job.get("company", "Unknown")

    # Load base resume
    with open(BASE_RESUME) as f:
        base_resume = f.read()

    # Build tailoring prompt
    jd_section = ""
    if job_description:
        keywords = extract_keywords_from_jd(job_description)
        before_score = score_resume_against_jd(base_resume, job_description)
        jd_section = f"""
JOB DESCRIPTION:
{job_description[:3000]}

EXTRACTED KEYWORDS TO EMPHASIZE:
{json.dumps(keywords, indent=2)}

CURRENT ATS SCORE: {before_score}/100 — aim for 80+
"""
    else:
        jd_section = f"Role: {role}\nCompany: {company}\n"

    prompt = f"""You are a professional resume writer optimizing for ATS (Applicant Tracking Systems).

TASK: Rewrite this resume to be tailored for the specific role below. 

RULES:
1. Keep ALL real experience and projects — do NOT fabricate anything
2. Reorder bullet points to prioritize relevant experience for this role
3. Add relevant keywords from the job description naturally into descriptions
4. Quantify achievements wherever possible (metrics, users, stars, etc.)
5. Keep it to 1 page (concise)
6. Use strong action verbs
7. Match the job title language (e.g., if JD says "Software Engineer" not "Developer")
8. Include a 2-line professional summary at the top tailored to THIS role
9. Output clean markdown format

{jd_section}

BASE RESUME:
{base_resume}

OUTPUT THE TAILORED RESUME IN MARKDOWN:"""

    tailored = ask_claude(prompt, max_turns=1, timeout=60)

    # Score the tailored version
    after_score = 0
    if job_description:
        after_score = score_resume_against_jd(tailored, job_description)

    # Save tailored resume
    slug = re.sub(r'[^a-z0-9]+', '_', f"{company}_{role}".lower()).strip('_')
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{slug}_{date_str}.md"
    filepath = os.path.join(TAILORED_DIR, filename)

    with open(filepath, 'w') as f:
        f.write(f"<!-- Tailored for: {role} @ {company} -->\n")
        f.write(f"<!-- Date: {datetime.now().strftime('%Y-%m-%d')} -->\n")
        if job_description:
            f.write(f"<!-- ATS Score: {before_score} -> {after_score} -->\n")
        f.write(f"\n{tailored}\n")

    print(f"  ✅ Tailored resume saved: {filepath}")
    if job_description:
        print(f"  📊 ATS Score: {before_score} → {after_score}")

    return filepath, tailored, after_score


def tailor_for_application(app_index):
    """Tailor resume for a specific application from the tracker."""
    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    if app_index < 0 or app_index >= len(apps):
        print(f"Invalid index. You have {len(apps)} tracked jobs.")
        return

    app = apps[app_index]
    jd = app.get("job_description", "")

    filepath, content, score = tailor_resume(app, jd if jd else None)

    # Update the application with the tailored resume path
    apps[app_index]["tailored_resume"] = filepath
    apps[app_index]["ats_score"] = score
    with open(APPLICATIONS_FILE, 'w') as f:
        json.dump(apps, f, indent=2)

    return filepath


def batch_tailor(min_score=40, max_count=10):
    """Tailor resumes for top discovered jobs."""
    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    candidates = [
        (i, a) for i, a in enumerate(apps)
        if a.get("status") == "discovered"
        and a.get("score", 0) >= min_score
        and not a.get("tailored_resume")
    ]
    candidates.sort(key=lambda x: -x[1].get("score", 0))

    print(f"Tailoring resumes for {min(max_count, len(candidates))} jobs...\n")

    for i, (idx, app) in enumerate(candidates[:max_count]):
        print(f"[{i+1}/{min(max_count, len(candidates))}] {app.get('role','?')} @ {app.get('company','?')}")
        try:
            tailor_for_application(idx)
        except Exception as e:
            print(f"  ❌ Error: {e}")
        print()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi — Resume Tailor")
    parser.add_argument("--tailor", type=int, metavar="INDEX", help="Tailor resume for job at index")
    parser.add_argument("--batch", action="store_true", help="Batch tailor for top jobs")
    parser.add_argument("--score", type=int, metavar="INDEX", help="Score current resume against job at index")
    parser.add_argument("--min-score", type=int, default=40, help="Min job score for batch")
    parser.add_argument("--max", type=int, default=10, help="Max resumes to generate")
    args = parser.parse_args()

    if args.tailor is not None:
        tailor_for_application(args.tailor)
    elif args.batch:
        batch_tailor(min_score=args.min_score, max_count=args.max)
    elif args.score is not None:
        with open(APPLICATIONS_FILE) as f:
            apps = json.load(f)
        with open(BASE_RESUME) as f:
            resume = f.read()
        jd = apps[args.score].get("job_description", "")
        if jd:
            score = score_resume_against_jd(resume, jd)
            keywords = extract_keywords_from_jd(jd)
            print(f"ATS Score: {score}/100")
            print(f"Keywords found: {json.dumps(keywords, indent=2)}")
        else:
            print("No job description stored. Run job_hunter with --fetch-jd first.")
    else:
        parser.print_help()
