#!/usr/bin/env python3
"""
Super Tobi — URL Resolver
Resolves web3.career and other aggregator URLs to direct ATS application URLs.
Uses HTTP HEAD/GET requests (no browser needed) to follow redirects and extract
the actual Greenhouse/Lever/Ashby/Recruitee/Workday URLs.
"""

import re
import requests
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# Known ATS domains
ATS_DOMAINS = [
    "greenhouse.io", "job-boards.greenhouse.io", "boards.greenhouse.io",
    "lever.co", "jobs.lever.co",
    "ashbyhq.com", "jobs.ashbyhq.com",
    "recruitee.com", "careers.",
    "workday.com", "myworkdayjobs.com",
    "smartrecruiters.com",
    "teamtailor.com",
    "breezy.hr",
    "applytojob.com",
    "workable.com",
]


def is_ats_url(url):
    """Check if a URL is a direct ATS application URL."""
    parsed = urlparse(url)
    return any(domain in parsed.netloc for domain in ATS_DOMAINS)


def resolve_web3career(url):
    """Extract direct apply URL from a web3.career job page.
    Strategy: extract company name from the URL, then query known ATS APIs directly.
    """
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        if r.status_code != 200:
            return None

        # Strategy 1: Direct ATS links in the HTML
        for domain in ATS_DOMAINS:
            pattern = rf'href="(https?://[^"]*{re.escape(domain)}[^"]*)"'
            matches = re.findall(pattern, r.text)
            for match in matches:
                if any(x in match.lower() for x in ["/jobs/", "/apply", "/application", "/o/", "/l/"]):
                    return match

        # Strategy 2: Extract company name and search ATS APIs directly
        # web3.career URLs: /role-name-company/id
        path = urlparse(url).path.strip("/")
        company_slug = _extract_company_from_w3c(path, r.text)
        if company_slug:
            direct = _search_ats_apis(company_slug)
            if direct:
                return direct

        # Strategy 3: Look for any ATS URL in page text
        for domain in ATS_DOMAINS:
            pattern = rf'(https?://[^\s"<>]*{re.escape(domain)}[^\s"<>]*)'
            matches = re.findall(pattern, r.text)
            for match in matches:
                if any(x in match.lower() for x in ["/jobs/", "/apply", "/o/", "/l/"]):
                    return match.rstrip(")")

        return None
    except Exception as e:
        print(f"    Resolver error for {url}: {e}")
        return None


def _extract_company_from_w3c(path, html):
    """Extract company slug from web3.career URL or page content."""
    # Try extracting from <title> or company name in HTML
    title_match = re.search(r'<title>([^<]+)</title>', html)
    if title_match:
        title = title_match.group(1)
        # "Role at Company - Web3.career" pattern
        at_match = re.search(r'at\s+([^-–|]+)', title, re.IGNORECASE)
        if at_match:
            return at_match.group(1).strip().lower().replace(" ", "").replace("-", "")

    # From URL path: /role-at-company/id or /role-company/id
    if "-at-" in path:
        company_part = path.split("-at-")[-1].split("/")[0]
        return company_part.replace("-", "")

    return None


def _search_ats_apis(company_slug):
    """Search known ATS platforms for a company's job board."""
    slug_variants = [
        company_slug,
        company_slug.replace("limited", "").replace("operations", ""),
        company_slug.replace("labs", ""),
    ]

    for slug in slug_variants:
        if not slug:
            continue
        # Greenhouse
        for prefix in ["job-boards.greenhouse.io", "boards.greenhouse.io"]:
            try:
                r = requests.get(f"https://{prefix}/{slug}", headers=HEADERS, timeout=5)
                if r.status_code == 200 and "greenhouse" in r.text.lower():
                    return f"https://{prefix}/{slug}"
            except Exception:
                pass

        # Ashby
        try:
            r = requests.get(f"https://jobs.ashbyhq.com/{slug}", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return f"https://jobs.ashbyhq.com/{slug}"
        except Exception:
            pass

        # Lever
        try:
            r = requests.get(f"https://jobs.lever.co/{slug}", headers=HEADERS, timeout=5)
            if r.status_code == 200:
                return f"https://jobs.lever.co/{slug}"
        except Exception:
            pass

    return None


def resolve_cryptocurrencyjobs(url):
    """Extract direct apply URL from cryptocurrencyjobs.co."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        for domain in ATS_DOMAINS:
            pattern = rf'href="(https?://[^"]*{re.escape(domain)}[^"]*)"'
            matches = re.findall(pattern, r.text)
            for match in matches:
                if any(x in match.lower() for x in ["/jobs/", "/apply", "/o/"]):
                    return match
        return None
    except Exception:
        return None


def resolve_remoteok(url):
    """RemoteOK links redirect to the actual job page."""
    try:
        r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.url != url and is_ats_url(r.url):
            return r.url
        # Try GET and look for apply link
        r = requests.get(url, headers=HEADERS, timeout=15)
        for domain in ATS_DOMAINS:
            pattern = rf'href="(https?://[^"]*{re.escape(domain)}[^"]*)"'
            matches = re.findall(pattern, r.text)
            for match in matches:
                return match
        return None
    except Exception:
        return None


def resolve_url(url):
    """Resolve any aggregator URL to a direct ATS URL."""
    if not url:
        return None

    # Already a direct ATS URL
    if is_ats_url(url):
        return url

    parsed = urlparse(url)
    hostname = parsed.netloc.lower()

    if "web3.career" in hostname:
        return resolve_web3career(url)
    elif "cryptocurrencyjobs" in hostname:
        return resolve_cryptocurrencyjobs(url)
    elif "remoteok" in hostname.lower():
        return resolve_remoteok(url)
    elif "himalayas.app" in hostname:
        # Himalayas has its own apply system
        return None
    else:
        # Try following redirects
        try:
            r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            if is_ats_url(r.url):
                return r.url
        except Exception:
            pass
        return None


def resolve_all_jobs(applications_file):
    """Resolve direct URLs for all discovered/blocked jobs in the tracker."""
    import json

    with open(applications_file) as f:
        apps = json.load(f)

    resolved = 0
    expired = 0

    for app in apps:
        if app.get("status") not in ("discovered", "blocked"):
            continue
        if app.get("direct_apply_url"):
            continue  # Already resolved

        url = app.get("url", "")
        if not url or is_ats_url(url):
            app["direct_apply_url"] = url
            continue

        print(f"  Resolving: {app.get('role', '?')} @ {app.get('company', '?')}...", end=" ", flush=True)
        direct = resolve_url(url)

        if direct:
            app["direct_apply_url"] = direct
            resolved += 1
            print(f"-> {direct[:60]}")
        else:
            print("no direct URL found")

    with open(applications_file, "w") as f:
        json.dump(apps, f, indent=2)

    print(f"\n  Resolved {resolved} direct URLs")
    return resolved


if __name__ == "__main__":
    import os, sys
    apps_file = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "career", "jobs", "applications.json"
    )
    resolve_all_jobs(apps_file)
