#!/usr/bin/env python3
"""
Super Tobi — Job Hunter
Searches for jobs across multiple boards using direct HTTP requests,
then uses Claude Code CLI to analyze, score, and generate cover letters.
"""

import os
import sys
import json
import asyncio
import requests
from datetime import datetime
from urllib.parse import quote_plus

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
APPLICATIONS_FILE = os.path.join(DATA_DIR, "career", "jobs", "applications.json")

sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))

PROFILE = {
    "name": "Tobiloba Adedeji",
    "email": "adedejitobiloba7@gmail.com",
    "roles": [
        "AI Engineer", "ML Engineer", "Solana Developer", "Rust Developer",
        "Full Stack Engineer", "Frontend Engineer", "Backend Engineer", "AI Researcher",
    ],
    "skills": [
        "Python", "TypeScript", "JavaScript", "Rust",
        "AI/ML", "LLMs", "Claude API", "OpenAI",
        "Solana", "Anchor", "Pinocchio", "Web3",
        "React", "Next.js", "Node.js", "DevOps",
    ],
    "links": {
        "website": "https://tobysolutions.dev",
        "linkedin": "https://www.linkedin.com/in/tobiloba-adedeji",
        "github": "https://github.com/tobySolutions",
        "twitter": "https://twitter.com/toby_solutions",
    },
}


# ─── Job Board Scrapers ────────────────────────────────────

def search_remoteok(query):
    """Search RemoteOK API."""
    try:
        # Use single-word tags for better results
        tag = query.lower().split()[0]  # "AI engineer" -> "ai"
        url = f"https://remoteok.com/api?tag={quote_plus(tag)}"
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        # First element is metadata, skip it
        jobs = []
        for item in data[1:11]:
            if not item.get("position"):
                continue
            jobs.append({
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": "Remote",
                "url": item.get("url", f"https://remoteok.com/l/{item.get('id', '')}"),
                "salary": f"${item.get('salary_min', '')}–${item.get('salary_max', '')}" if item.get('salary_min') else "",
                "tags": item.get("tags", []),
                "description": item.get("description", "")[:200],
                "date": item.get("date", ""),
                "board": "RemoteOK",
            })
        return jobs
    except Exception as e:
        print(f"    RemoteOK error: {e}")
        return []


def search_web3career():
    """Scrape Web3.career for Solana jobs via HTML parsing."""
    import re
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get("https://web3.career/solana-jobs", headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        jobs = []
        # Pattern: <a href="/job-slug/id"><h2>Title</h2></a>
        links = re.findall(r'href="(/[^"]+)"[^>]*>\s*<h2[^>]*>([^<]+)</h2>', r.text)
        for path, title in links[:15]:
            # Extract company from URL slug: "title-at-company/id"
            company = "Unknown"
            if "-at-" in path:
                company = path.split("-at-")[-1].split("/")[0].replace("-", " ").title()
            jobs.append({
                "title": title.strip(),
                "company": company,
                "location": "Remote",
                "url": f"https://web3.career{path}",
                "salary": "",
                "description": "",
                "board": "Web3Career",
            })
        return jobs
    except Exception as e:
        print(f"    Web3Career error: {e}")
        return []


def search_himalayas(query):
    """Search Himalayas.app API for remote jobs."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get(f"https://himalayas.app/jobs/api?q={quote_plus(query)}&limit=10", headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for item in data.get("jobs", []):
            salary = ""
            if item.get("minSalary") and item.get("maxSalary"):
                currency = item.get("currency", "USD")
                salary = f"{currency} {item['minSalary']:,}–{item['maxSalary']:,}"
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("companyName", ""),
                "location": "Remote",
                "url": f"https://himalayas.app/companies/{item.get('companySlug', '')}/jobs/{item.get('slug', '')}",
                "salary": salary,
                "description": item.get("excerpt", "")[:200],
                "board": "Himalayas",
            })
        return jobs
    except Exception as e:
        print(f"    Himalayas error: {e}")
        return []


def search_google_jobs(query, location="Lagos Nigeria"):
    """Search for local jobs via Brave Search (pulls Google Jobs results)."""
    try:
        api_key = os.environ.get("BRAVE_API_KEY", "")
        if not api_key:
            # Try loading from config
            env_file = os.path.join(BASE_DIR, "config", "api_keys.env")
            if os.path.exists(env_file):
                with open(env_file) as f:
                    for line in f:
                        if line.startswith("BRAVE_API_KEY="):
                            api_key = line.strip().split("=", 1)[1]
                            break
        if not api_key:
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        }
        search_query = f"{query} jobs in {location} site:linkedin.com OR site:indeed.com OR site:glassdoor.com"
        r = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers=headers,
            params={"q": search_query, "count": 10},
            timeout=15,
        )
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for item in data.get("web", {}).get("results", [])[:10]:
            title = item.get("title", "")
            # Skip non-job results
            if not any(kw in title.lower() for kw in ["engineer", "developer", "analyst", "scientist", "architect", "designer", "manager"]):
                continue
            # Try to split "Role - Company" or "Role at Company"
            company = ""
            role = title
            if " - " in title:
                parts = title.split(" - ", 1)
                role = parts[0].strip()
                company = parts[1].strip()
            elif " at " in title.lower():
                idx = title.lower().index(" at ")
                role = title[:idx].strip()
                company = title[idx+4:].strip()

            jobs.append({
                "title": role,
                "company": company or "Unknown",
                "location": location,
                "url": item.get("url", ""),
                "salary": "",
                "description": item.get("description", "")[:200],
                "board": "Google/Brave",
            })
        return jobs
    except Exception as e:
        print(f"    Google Jobs error: {e}")
        return []


def search_cryptojobslist(query):
    """Search CryptoJobsList."""
    try:
        url = f"https://cryptojobslist.com/api/jobs?query={quote_plus(query)}&limit=10"
        headers = {"User-Agent": "SuperTobi/1.0"}
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        jobs = []
        for item in data.get("jobs", data if isinstance(data, list) else [])[:10]:
            jobs.append({
                "title": item.get("title", ""),
                "company": item.get("company", {}).get("name", "") if isinstance(item.get("company"), dict) else item.get("company", ""),
                "location": item.get("location", "Remote"),
                "url": item.get("url", ""),
                "salary": item.get("salary", ""),
                "description": item.get("description", "")[:200],
                "board": "CryptoJobsList",
            })
        return jobs
    except Exception as e:
        print(f"    CryptoJobsList error: {e}")
        return []


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


def _brave_search(query, count=10):
    """Run a Brave Search API query and return raw results."""
    api_key = _load_brave_api_key()
    if not api_key:
        return []
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }
    r = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers=headers,
        params={"q": query, "count": count},
        timeout=15,
    )
    if r.status_code != 200:
        return []
    return r.json().get("web", {}).get("results", [])


# Company career page domains used by search_big_tech
BIG_TECH_SITES = {
    # FAANG+
    "Google": "careers.google.com",
    "Meta": "metacareers.com",
    "Amazon": "amazon.jobs",
    "Apple": "jobs.apple.com",
    "Microsoft": "careers.microsoft.com",
    "Netflix": "jobs.netflix.com",
    # AI leaders
    "Anthropic": "jobs.ashbyhq.com/anthropic",
    "OpenAI": "openai.com/careers",
    "Cohere": "jobs.lever.co/cohere",
    "Mistral": "mistral.ai/careers",
    "Stability AI": "stability.ai/careers",
    "Hugging Face": "apply.workable.com/huggingface",
    "DeepMind": "deepmind.google/careers",
    # Crypto / Web3
    "Coinbase": "coinbase.com/careers",
    "Ripple": "ripple.com/careers",
    "Circle": "circle.com/careers",
    "Consensys": "consensys.io/careers",
    "Alchemy": "alchemy.com/careers",
    "Helius": "helius.dev",
    "Jito Labs": "jito.network",
    # Top startups
    "Stripe": "stripe.com/jobs",
    "Vercel": "vercel.com/careers",
    "Supabase": "supabase.com/careers",
    "Railway": "railway.app/careers",
    "Fly.io": "fly.io/jobs",
    "Render": "render.com/careers",
    "Replit": "replit.com/site/careers",
}


def search_big_tech(query):
    """Search career pages of major tech, AI, crypto, and startup companies via Brave Search."""
    try:
        # Build site: clauses in batches to stay within query length limits
        sites = list(BIG_TECH_SITES.values())
        all_jobs = []

        # Split into chunks of 8 sites per query to avoid URL length issues
        for i in range(0, len(sites), 8):
            chunk = sites[i:i + 8]
            site_clause = " OR ".join(f"site:{s}" for s in chunk)
            search_query = f"({site_clause}) {query}"
            results = _brave_search(search_query, count=10)

            for item in results:
                title = item.get("title", "")
                url = item.get("url", "")
                description = item.get("description", "")

                # Figure out which company this belongs to
                company = "Unknown"
                for name, domain in BIG_TECH_SITES.items():
                    if domain.split("/")[0] in url:
                        company = name
                        break

                # Try to clean the title (remove trailing " - Company" patterns)
                role = title
                for sep in [" - ", " | ", " at "]:
                    if sep in title:
                        role = title.split(sep)[0].strip()
                        break

                all_jobs.append({
                    "title": role,
                    "company": company,
                    "location": "Remote",
                    "url": url,
                    "salary": "",
                    "description": description[:200],
                    "board": "BigTech",
                })

        return all_jobs
    except Exception as e:
        print(f"    Big Tech search error: {e}")
        return []


def search_fortune500(query):
    """Search broader Fortune 500 and enterprise company job boards via Brave Search."""
    try:
        search_query = f'{query} remote engineer site:careers.* OR site:jobs.* "fortune 500" OR "enterprise"'
        results = _brave_search(search_query, count=10)

        jobs = []
        for item in results:
            title = item.get("title", "")
            url = item.get("url", "")
            description = item.get("description", "")

            # Skip results that clearly are not job listings
            if not any(kw in title.lower() for kw in [
                "engineer", "developer", "scientist", "architect",
                "analyst", "designer", "manager", "lead", "director",
            ]):
                continue

            # Parse company and role from title
            company = ""
            role = title
            for sep in [" - ", " | ", " at "]:
                if sep.lower() in title.lower():
                    idx = title.lower().index(sep.lower())
                    role = title[:idx].strip()
                    company = title[idx + len(sep):].strip()
                    break

            # Try extracting company from URL domain
            if not company:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
                # careers.ibm.com -> IBM
                parts = domain.replace("www.", "").split(".")
                if len(parts) >= 2:
                    company = parts[1] if parts[0] in ("careers", "jobs") else parts[0]
                    company = company.title()

            jobs.append({
                "title": role,
                "company": company or "Unknown",
                "location": "Remote",
                "url": url,
                "salary": "",
                "description": description[:200],
                "board": "Fortune500",
            })

        return jobs
    except Exception as e:
        print(f"    Fortune 500 search error: {e}")
        return []


def search_via_claude(query, boards_hint="LinkedIn, Wellfound, Indeed, Arc.dev"):
    """Use Claude CLI to search the web for jobs."""
    from ai import ask_claude
    try:
        result = ask_claude(
            f"Use web search to find current remote job postings matching: {query}\n"
            f"Search across: {boards_hint}\n"
            f"Find 5-10 real, currently open positions. For each provide:\n"
            f"- title, company, location, url, salary (if shown), board (which site)\n"
            f"Return ONLY a JSON array of objects with those keys. No markdown, no explanation.\n"
            f"If you cannot find jobs, return [].",
            timeout=90,
        )
        cleaned = result.strip()
        # Remove markdown code fences
        if "```" in cleaned:
            # Find the JSON array between code fences
            import re
            match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)
            else:
                cleaned = cleaned.split("```")[1] if len(cleaned.split("```")) > 1 else cleaned
                cleaned = cleaned.strip()
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:].strip()
        # Try to extract JSON array from response
        if not cleaned.startswith("["):
            import re
            match = re.search(r'\[.*\]', cleaned, re.DOTALL)
            if match:
                cleaned = match.group(0)
            else:
                return []
        jobs = json.loads(cleaned)
        return jobs if isinstance(jobs, list) else []
    except Exception as e:
        print(f"    Claude search error: {e}")
        return []


def search_twitter_jobs(query):
    """Search Twitter/X for job postings."""
    try:
        sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
        from twitter_feed import twitter_request
        import time
        time.sleep(2)

        # Search for job posts — people often tweet "hiring", "we're looking for", "open role"
        search_query = f"{query} (hiring OR \"looking for\" OR \"open role\" OR \"join us\" OR \"apply\") -is:retweet"
        result = twitter_request("tweet/advanced_search", {
            "query": search_query,
            "queryType": "Top",
        })
        if not result:
            return []

        jobs = []
        for t in result.get("tweets", [])[:10]:
            text = t.get("text", "")
            author = t.get("author", {})
            author_name = author.get("name", "") if isinstance(author, dict) else str(author)
            url = t.get("url", "")

            # Extract any links from the tweet (likely application URLs)
            import re
            links = re.findall(r'https?://\S+', text)
            apply_url = ""
            for link in links:
                if any(d in link for d in ["greenhouse", "lever", "ashby", "careers", "jobs", "apply", "wellfound"]):
                    apply_url = link
                    break
            if not apply_url and links:
                apply_url = links[0]

            jobs.append({
                "title": text[:80].replace("\n", " "),
                "company": author_name,
                "location": "Remote",
                "url": apply_url or url,
                "salary": "",
                "description": text[:200],
                "board": "Twitter/X",
            })
        return jobs
    except Exception as e:
        print(f"    Twitter jobs error: {e}")
        return []


# ─── Scoring & Analysis ───────────────────────────────────

def score_job(job):
    """Score a job match 0-100. Penalizes location-locked roles heavily."""
    score = 0
    title = job.get("title", "").lower()
    location = job.get("location", "").lower()
    text = (title + " " + job.get("description", "") + " " + " ".join(job.get("tags", []))).lower()

    # Role match
    role_keywords = ["engineer", "developer", "researcher", "architect", "scientist"]
    tech_keywords = ["software", "ai", "ml", "machine learning", "data", "backend", "frontend",
                     "fullstack", "full stack", "full-stack", "solana", "rust", "blockchain",
                     "web3", "crypto", "python", "typescript", "devops", "platform", "protocol",
                     "devrel", "developer relations", "developer advocate"]

    has_role = any(kw in title for kw in role_keywords)
    has_tech = any(kw in title for kw in tech_keywords)

    if has_role and has_tech:
        score += 30
    elif has_role:
        score += 15
    elif has_tech:
        score += 10

    # Irrelevant roles
    irrelevant = ["coordinator", "analyst", "customer service", "patient", "travel",
                  "accounting", "nurse", "medical", "sales", "marketing manager",
                  "recruiter", "hr ", "legal", "compliance officer", "financial crimes",
                  "hardware engineer", "mechanical", "electrical engineer", "civil"]
    if any(kw in title for kw in irrelevant):
        return 0

    # Location: remote-friendly is critical. Tobiloba is in Nigeria.
    if "remote" in location or "worldwide" in location or "global" in location or "anywhere" in location:
        score += 15
    elif any(loc in location for loc in ["nigeria", "lagos", "africa", "abuja", "naija"]):
        score += 20  # Boost local Nigerian jobs
    elif any(loc in location for loc in ["india only", "singapore", "sydney", "australia", "japan", "korea"]):
        score -= 20
    elif location and "remote" not in text:
        score -= 10

    # Hard location/auth restrictions in description
    restricted = ["us citizen", "u.s. citizen", "united states only", "us only",
                  "security clearance", "must be authorized to work in the u",
                  "must reside in", "this role is onsite", "no visa sponsorship",
                  "india-only", "india only"]
    if any(kw in text for kw in restricted):
        score -= 25

    # Seniority stretch (4 years experience vs principal/director expectations)
    if any(kw in title for kw in ["principal", "director", "vp ", "head of"]):
        score -= 10
    if "staff" in title:
        score -= 5

    # Skill match
    matched_skills = sum(1 for s in PROFILE["skills"] if s.lower() in text)
    score += min(matched_skills * 5, 30)

    if job.get("salary"):
        score += 5

    # Strong signals for Tobiloba's strengths
    for boost in ["solana", "rust", "web3", "blockchain", "llm", "claude", "ai agent",
                  "mcp", "anchor", "developer relations", "devrel", "open source"]:
        if boost in text:
            score += 10

    for avoid in ["unpaid", "intern", "volunteer"]:
        if avoid in text:
            score -= 30
    if "junior" in title:
        score -= 15

    return max(0, min(100, score))


def log_application(job, status="discovered"):
    """Log a job to applications tracker."""
    if os.path.exists(APPLICATIONS_FILE):
        with open(APPLICATIONS_FILE) as f:
            apps = json.load(f)
    else:
        apps = []

    # Check for duplicates: same URL or same company+role combo
    existing_urls = {a.get("url", "") for a in apps}
    if job.get("url", "") in existing_urls and job.get("url"):
        return None

    existing_keys = {
        (a.get("company", "").lower().strip(), a.get("role", a.get("title", "")).lower().strip())
        for a in apps
    }
    new_key = (job.get("company", "").lower().strip(), job.get("title", "").lower().strip())
    if new_key in existing_keys and new_key != ("", ""):
        return None

    entry = {
        "id": f"job-{len(apps)+1:04d}",
        "type": "job",
        "company": job.get("company", "Unknown"),
        "role": job.get("title", "Unknown"),
        "url": job.get("url", ""),
        "location": job.get("location", ""),
        "salary": job.get("salary", ""),
        "score": score_job(job),
        "board": job.get("board", ""),
        "status": status,
        "discovered_date": datetime.now().strftime("%Y-%m-%d"),
        "applied_date": None,
        "follow_up_date": None,
        "notes": "",
    }

    apps.append(entry)
    with open(APPLICATIONS_FILE, "w") as f:
        json.dump(apps, f, indent=2)

    return entry


# ─── Main Hunt ─────────────────────────────────────────────

def hunt(queries=None):
    """Run a full job hunt."""
    if queries is None:
        queries = [
            "AI engineer", "Solana developer", "Rust developer", "fullstack engineer",
            "software engineer Lagos Nigeria", "backend engineer Nigeria remote",
        ]

    print("╔══════════════════════════════════════════════╗")
    print("║       💼 SUPER TOBI — JOB HUNT STARTING      ║")
    print("╠══════════════════════════════════════════════╣")

    all_jobs = []

    for query in queries:
        print(f"\n  🔍 Searching: {query}")

        # RemoteOK (has free API)
        print(f"    📋 RemoteOK...", end=" ", flush=True)
        jobs = search_remoteok(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Web3Career
        print(f"    📋 Web3Career...", end=" ", flush=True)
        jobs = search_web3career()
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # CryptoJobsList
        print(f"    📋 CryptoJobsList...", end=" ", flush=True)
        jobs = search_cryptojobslist(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Himalayas
        print(f"    📋 Himalayas...", end=" ", flush=True)
        jobs = search_himalayas(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Google Jobs (local, via Brave Search)
        print(f"    📋 Google Jobs (Lagos)...", end=" ", flush=True)
        jobs = search_google_jobs(query, "Lagos Nigeria")
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Nigerian job boards (Jobberman, MyJobMag, etc.)
        print(f"    📋 Nigerian Jobs...", end=" ", flush=True)
        jobs = search_google_jobs(query, "Nigeria site:jobberman.com OR site:myjobmag.com OR site:ngcareers.com OR site:hotnigeranjobs.com")
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Twitter/X job posts
        print(f"    📋 Twitter/X...", end=" ", flush=True)
        jobs = search_twitter_jobs(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Big Tech career pages
        print(f"    📋 Big Tech...", end=" ", flush=True)
        jobs = search_big_tech(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Fortune 500 / enterprise
        print(f"    📋 Fortune 500...", end=" ", flush=True)
        jobs = search_fortune500(query)
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

        # Search via Claude (uses web search)
        print(f"    📋 LinkedIn/Wellfound/Indeed...", end=" ", flush=True)
        jobs = search_via_claude(f"{query} remote", "LinkedIn, Wellfound, Indeed, Arc.dev, Built In")
        all_jobs.extend(jobs)
        print(f"✅ {len(jobs)}" if jobs else "—")

    # Score and sort
    for job in all_jobs:
        job["score"] = score_job(job)
    all_jobs.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate by title+company
    seen = set()
    unique_jobs = []
    for job in all_jobs:
        key = (job.get("title", "").lower(), job.get("company", "").lower())
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)
    all_jobs = unique_jobs

    # Log top matches (only score > 0)
    logged = 0
    for job in all_jobs[:30]:
        if job.get("score", 0) > 0 and log_application(job):
            logged += 1

    # Display results
    print(f"\n{'═' * 48}")
    print(f"  📊 Total unique matches: {len(all_jobs)}")
    print(f"  💾 New jobs logged: {logged}")
    if all_jobs:
        print(f"  ⭐ Top score: {all_jobs[0]['score']}%")
    print(f"{'═' * 48}")

    print("\n  🏆 TOP MATCHES\n")
    for i, job in enumerate(all_jobs[:15], 1):
        score = job["score"]
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        print(f"  #{i:2d} {job.get('title', '?')}")
        print(f"      🏢 {job.get('company', '?')}  📍 {job.get('location', '?')}")
        if job.get("salary"):
            print(f"      💰 {job['salary']}")
        print(f"      📊 [{bar}] {score}%  📋 {job.get('board', '?')}")
        print(f"      🔗 {job.get('url', 'no url')}")
        print()

    print("╚══════════════════════════════════════════════╝")
    return all_jobs


def generate_cover_letter(job_index):
    """Generate a cover letter for a specific job from the tracker."""
    from ai import ask_claude

    with open(APPLICATIONS_FILE) as f:
        apps = json.load(f)

    if job_index < 0 or job_index >= len(apps):
        print(f"Invalid job index. You have {len(apps)} tracked jobs.")
        return

    job = apps[job_index]
    print(f"\n  Generating cover letter for: {job['role']} @ {job['company']}...")

    letter = ask_claude(
        f"Write a short cover letter (under 200 words) for Tobiloba Adedeji applying to:\n"
        f"Role: {job['role']}\nCompany: {job['company']}\n\n"
        f"Tobiloba's background:\n"
        f"- AI Researcher at Idealik\n"
        f"- Solana builder (Anchor, Pinocchio, Rust), co-founder Solana Students Africa\n"
        f"- Strong open source contributor, full-stack engineer\n"
        f"- Website: tobysolutions.dev\n\n"
        f"Rules: Sound like a real person. Be direct and confident. No generic filler.\n"
        f"Output ONLY the cover letter.",
        timeout=30,
    )

    print(f"\n{'─' * 48}")
    print(letter)
    print(f"{'─' * 48}")
    return letter


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi Job Hunter")
    parser.add_argument("--hunt", action="store_true", help="Run full job hunt")
    parser.add_argument("--query", nargs="+", help="Custom search queries")
    parser.add_argument("--list", action="store_true", help="Show tracked applications")
    parser.add_argument("--cover-letter", type=int, metavar="INDEX", help="Generate cover letter for job at index")
    parser.add_argument("--test", action="store_true", help="Test AI connection")

    args = parser.parse_args()

    if args.hunt or args.query:
        queries = args.query or ["AI engineer", "Solana developer", "Rust developer", "fullstack engineer"]
        hunt(queries)
    elif args.list:
        if os.path.exists(APPLICATIONS_FILE):
            with open(APPLICATIONS_FILE) as f:
                apps = json.load(f)
            if apps:
                for i, a in enumerate(apps):
                    score = a.get("score", 0)
                    print(f"  [{i}] {a['role']:30s} @ {a['company']:20s} 📊{score}% [{a['status']}] {a['board']}")
            else:
                print("No applications tracked yet. Run --hunt first.")
        else:
            print("No applications file. Run --hunt first.")
    elif args.cover_letter is not None:
        generate_cover_letter(args.cover_letter)
    elif args.test:
        from ai import ask_claude
        result = ask_claude("Say 'Job hunter ready' and nothing else.", timeout=15)
        print(f"✅ AI engine: {result}" if "ready" in result.lower() else f"⚠️ {result}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
