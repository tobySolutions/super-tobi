#!/usr/bin/env python3
"""
Super Tobi — Tech Trends Aggregator

Aggregates signals from AI research, AI development, and Solana/crypto,
then pipes them into the ideas system to generate product ideas.

Sources: ArXiv, GitHub Trending, Hacker News, Brave Search, Twitter
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
TRENDS_FILE = DATA / "trends" / "tech_trends.json"
IDEAS_FILE = DATA / "ideas" / "backlog.json"
CONFIG = BASE / "config"
SCRIPTS = BASE / "scripts"
CLAUDE_CLI = Path("/Users/tobiloba/.local/bin/claude")

console = Console()


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_trends():
    data = load_json(TRENDS_FILE)
    if not data:
        data = {
            "last_updated": None,
            "sources": {},
            "trends": [],
            "idea_pipeline": [],
        }
    return data


def get_brave_api_key():
    """Load BRAVE_API_KEY from environment or config/api_keys.env."""
    key = os.environ.get("BRAVE_API_KEY")
    if key:
        return key
    env_file = CONFIG / "api_keys.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("BRAVE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def make_trend_entry(source, title, description, url, tags, engagement=0):
    return {
        "id": f"trend-{uuid.uuid4().hex[:8]}",
        "source": source,
        "title": title,
        "description": description,
        "url": url,
        "relevance_tags": tags,
        "engagement": engagement,
        "fetched_at": datetime.now().isoformat(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SOURCE FETCHERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def fetch_arxiv():
    """Fetch recent papers from ArXiv in AI-related categories."""
    console.print("  [cyan]ArXiv[/] — fetching recent AI papers...")
    trends = []
    categories = ["cs.AI", "cs.CL", "cs.LG", "cs.MA"]

    for cat in categories:
        try:
            url = (
                f"http://export.arxiv.org/api/query?"
                f"search_query=cat:{cat}&sortBy=submittedDate"
                f"&sortOrder=descending&max_results=10"
            )
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()

            # Parse Atom XML
            import xml.etree.ElementTree as ET

            root = ET.fromstring(resp.text)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                summary = entry.find("atom:summary", ns)
                link = entry.find("atom:id", ns)
                published = entry.find("atom:published", ns)
                authors = entry.findall("atom:author/atom:name", ns)

                title_text = title.text.strip().replace("\n", " ") if title is not None else "Untitled"
                summary_text = summary.text.strip()[:300] if summary is not None else ""
                link_text = link.text.strip() if link is not None else ""
                author_list = [a.text for a in authors[:3]]

                # Tag based on content
                tags = [cat.lower()]
                title_lower = title_text.lower()
                if any(kw in title_lower for kw in ["agent", "multi-agent", "agentic"]):
                    tags.append("ai-agents")
                if any(kw in title_lower for kw in ["language model", "llm", "transformer"]):
                    tags.append("llm")
                if any(kw in title_lower for kw in ["reinforcement", "rl"]):
                    tags.append("reinforcement-learning")
                if "reasoning" in title_lower:
                    tags.append("reasoning")

                trends.append(make_trend_entry(
                    source="arxiv",
                    title=title_text,
                    description=f"{', '.join(author_list)}. {summary_text}",
                    url=link_text,
                    tags=list(set(tags)),
                ))

        except Exception as e:
            console.print(f"    [yellow]Warning: ArXiv {cat} failed: {e}[/]")

    console.print(f"    [green]{len(trends)} papers fetched[/]")
    return trends


def fetch_github():
    """Fetch trending repos from GitHub for relevant topics."""
    console.print("  [cyan]GitHub[/] — fetching trending repos...")
    trends = []
    topics = ["ai-agents", "solana", "rust", "llm", "mcp"]
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    for topic in topics:
        try:
            url = (
                f"https://api.github.com/search/repositories?"
                f"q=topic:{topic}+created:>{week_ago}&sort=stars&order=desc"
            )
            headers = {"Accept": "application/vnd.github.v3+json"}
            # Use GitHub token if available
            gh_token = os.environ.get("GITHUB_TOKEN")
            if gh_token:
                headers["Authorization"] = f"token {gh_token}"

            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for repo in data.get("items", [])[:10]:
                tags = [topic]
                lang = repo.get("language", "")
                if lang:
                    tags.append(lang.lower())

                trends.append(make_trend_entry(
                    source="github",
                    title=repo.get("full_name", ""),
                    description=repo.get("description", "") or "No description",
                    url=repo.get("html_url", ""),
                    tags=tags,
                    engagement=repo.get("stargazers_count", 0),
                ))

        except Exception as e:
            console.print(f"    [yellow]Warning: GitHub {topic} failed: {e}[/]")

    # Deduplicate by URL
    seen = set()
    unique = []
    for t in trends:
        if t["url"] not in seen:
            seen.add(t["url"])
            unique.append(t)

    console.print(f"    [green]{len(unique)} repos fetched[/]")
    return unique


def fetch_hackernews():
    """Fetch top HN stories filtered for AI/ML/Solana/crypto/Rust keywords."""
    console.print("  [cyan]Hacker News[/] — fetching top stories...")
    trends = []
    keywords = [
        "ai", "artificial intelligence", "machine learning", "ml",
        "llm", "gpt", "claude", "openai", "anthropic", "agent",
        "solana", "crypto", "blockchain", "web3", "defi",
        "rust", "mcp", "model context protocol",
    ]

    try:
        resp = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=15
        )
        resp.raise_for_status()
        story_ids = resp.json()[:100]  # Check top 100

        for sid in story_ids:
            try:
                item_resp = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                    timeout=10,
                )
                item = item_resp.json()
                if not item or item.get("type") != "story":
                    continue

                title = item.get("title", "")
                title_lower = title.lower()

                # Filter for relevant keywords
                matched_tags = []
                for kw in keywords:
                    if kw in title_lower:
                        matched_tags.append(kw)

                if not matched_tags:
                    continue

                # Normalize tags
                tag_map = {
                    "artificial intelligence": "ai",
                    "machine learning": "ml",
                    "gpt": "llm",
                    "openai": "llm",
                    "anthropic": "ai",
                    "claude": "ai",
                    "blockchain": "crypto",
                    "web3": "crypto",
                    "defi": "crypto",
                    "model context protocol": "mcp",
                }
                normalized = list(set(
                    tag_map.get(t, t) for t in matched_tags
                ))

                trends.append(make_trend_entry(
                    source="hackernews",
                    title=title,
                    description=f"Score: {item.get('score', 0)} | Comments: {item.get('descendants', 0)}",
                    url=item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                    tags=normalized,
                    engagement=item.get("score", 0),
                ))

            except Exception:
                continue

    except Exception as e:
        console.print(f"    [yellow]Warning: HN failed: {e}[/]")

    console.print(f"    [green]{len(trends)} relevant stories found[/]")
    return trends


def fetch_brave_search():
    """Search Brave for AI/Solana development trends."""
    api_key = get_brave_api_key()
    if not api_key:
        console.print("  [dim]Brave Search[/] — skipped (no BRAVE_API_KEY)")
        return []

    console.print("  [cyan]Brave Search[/] — searching trends...")
    trends = []
    queries = [
        "AI agents 2026",
        "Solana development tools",
        "LLM infrastructure startups",
        "MCP protocol AI",
        "Rust AI development",
    ]

    for query in queries:
        try:
            resp = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 5},
                headers={
                    "Accept": "application/json",
                    "Accept-Encoding": "gzip",
                    "X-Subscription-Token": api_key,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for result in data.get("web", {}).get("results", []):
                tags = []
                title_lower = result.get("title", "").lower()
                if "ai" in title_lower or "agent" in title_lower:
                    tags.append("ai-agents")
                if "solana" in title_lower:
                    tags.append("solana")
                if "rust" in title_lower:
                    tags.append("rust")
                if "llm" in title_lower or "language model" in title_lower:
                    tags.append("llm")
                if "mcp" in title_lower:
                    tags.append("mcp")
                if not tags:
                    # Derive from query
                    if "solana" in query.lower():
                        tags.append("solana")
                    elif "ai" in query.lower() or "llm" in query.lower():
                        tags.append("ai")
                    elif "mcp" in query.lower():
                        tags.append("mcp")
                    elif "rust" in query.lower():
                        tags.append("rust")

                trends.append(make_trend_entry(
                    source="brave",
                    title=result.get("title", ""),
                    description=result.get("description", "")[:300],
                    url=result.get("url", ""),
                    tags=tags,
                ))

        except Exception as e:
            console.print(f"    [yellow]Warning: Brave '{query}' failed: {e}[/]")

    console.print(f"    [green]{len(trends)} results found[/]")
    return trends


def fetch_twitter():
    """Reuse the twitter_feed module to search for relevant trends."""
    console.print("  [cyan]Twitter[/] — searching trends...")
    trends = []

    try:
        sys.path.insert(0, str(SCRIPTS))
        from twitter_feed import search_twitter, load_api_key

        api_key = load_api_key()
        if not api_key:
            console.print("    [yellow]No Twitter API key found[/]")
            return []

        search_queries = [
            "AI agents",
            "Solana development",
            "MCP protocol",
            "LLM infrastructure",
            "Rust AI",
        ]

        for query in search_queries:
            try:
                results = search_twitter(api_key, query, max_results=5)
                for tweet in results:
                    tags = []
                    text = tweet.get("text", "").lower()
                    if "agent" in text or "ai" in text:
                        tags.append("ai-agents")
                    if "solana" in text:
                        tags.append("solana")
                    if "mcp" in text:
                        tags.append("mcp")
                    if "rust" in text:
                        tags.append("rust")
                    if "llm" in text:
                        tags.append("llm")
                    if not tags:
                        tags.append(query.lower().replace(" ", "-"))

                    trends.append(make_trend_entry(
                        source="twitter",
                        title=tweet.get("text", "")[:120],
                        description=f"@{tweet.get('author', {}).get('userName', 'unknown')} | Likes: {tweet.get('likeCount', 0)} | RTs: {tweet.get('retweetCount', 0)}",
                        url=f"https://twitter.com/{tweet.get('author', {}).get('userName', '_')}/status/{tweet.get('id', '')}",
                        tags=tags,
                        engagement=tweet.get("likeCount", 0),
                    ))
            except Exception as e:
                console.print(f"    [yellow]Twitter search '{query}' failed: {e}[/]")

    except ImportError:
        console.print("    [yellow]twitter_feed module not available[/]")
    except Exception as e:
        console.print(f"    [yellow]Twitter failed: {e}[/]")

    console.print(f"    [green]{len(trends)} tweets found[/]")
    return trends


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMANDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_scan():
    """Fetch from ALL sources and save to tech_trends.json."""
    console.print(Panel(
        "[bold]Scanning all sources for tech trends...[/]",
        border_style="cyan",
    ))

    all_trends = []

    all_trends.extend(fetch_arxiv())
    all_trends.extend(fetch_github())
    all_trends.extend(fetch_hackernews())
    all_trends.extend(fetch_brave_search())
    all_trends.extend(fetch_twitter())

    # Load existing and merge (keep last 500, newest first)
    data = load_trends()
    existing_urls = {t["url"] for t in data.get("trends", [])}
    new_trends = [t for t in all_trends if t["url"] not in existing_urls]

    data["trends"] = new_trends + data.get("trends", [])
    data["trends"] = data["trends"][:500]  # Cap at 500
    data["last_updated"] = datetime.now().isoformat()
    save_json(TRENDS_FILE, data)

    # Summary table
    table = Table(title="Scan Results", box=box.ROUNDED)
    table.add_column("Source", style="bold")
    table.add_column("New", justify="right")
    table.add_column("Total", justify="right", style="dim")

    source_counts = {}
    for t in all_trends:
        src = t["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    new_counts = {}
    for t in new_trends:
        src = t["source"]
        new_counts[src] = new_counts.get(src, 0) + 1

    for src in ["arxiv", "github", "hackernews", "brave", "twitter"]:
        table.add_row(
            src,
            f"[green]{new_counts.get(src, 0)}[/]",
            str(source_counts.get(src, 0)),
        )

    table.add_row(
        "[bold]Total[/]",
        f"[bold green]{len(new_trends)}[/]",
        f"[bold]{len(all_trends)}[/]",
    )

    console.print(table)
    console.print(f"\n[dim]Saved to {TRENDS_FILE}[/]")
    console.print(f"[dim]Total trends in database: {len(data['trends'])}[/]")


def cmd_digest():
    """Use Claude CLI to analyze trends and produce a structured digest."""
    data = load_trends()
    trends = data.get("trends", [])
    if not trends:
        console.print("[red]No trends found. Run --scan first.[/]")
        return

    console.print(Panel(
        "[bold]Generating AI-powered trends digest...[/]",
        border_style="magenta",
    ))

    # Prepare trends summary for Claude
    recent = trends[:100]  # Most recent 100
    trends_text = ""

    for t in recent:
        trends_text += f"- [{t['source']}] {t['title']}"
        if t.get("engagement"):
            trends_text += f" (engagement: {t['engagement']})"
        trends_text += f"\n  Tags: {', '.join(t.get('relevance_tags', []))}\n"
        if t.get("description"):
            trends_text += f"  {t['description'][:150]}\n"
        trends_text += "\n"

    prompt = f"""Analyze these tech trends and produce a structured digest for Tobiloba, an AI researcher and Solana developer.

TRENDS DATA:
{trends_text}

Produce a digest with exactly these sections:

## Top 5 AI Research Trends
(Focus on breakthroughs, new architectures, agents, reasoning)

## Top 5 Developer Tool Trends
(Focus on new tools, frameworks, infrastructure, developer experience)

## Top 5 Solana/Crypto Trends
(Focus on Solana ecosystem, DeFi, blockchain development)

## Emerging Patterns & Opportunities
(Cross-cutting themes, gaps in the market, convergence points)

Be specific and actionable. Reference actual papers/repos/stories from the data."""

    try:
        result = subprocess.run(
            [str(CLAUDE_CLI), "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=str(BASE),
        )

        if result.returncode == 0 and result.stdout.strip():
            digest = result.stdout.strip()
            console.print(Panel(
                digest,
                title="[bold magenta]Trends Digest[/]",
                border_style="magenta",
                padding=(1, 2),
            ))

            # Save digest
            digest_file = DATA / "trends" / "latest_digest.md"
            digest_file.write_text(
                f"# Tech Trends Digest — {datetime.now().strftime('%Y-%m-%d')}\n\n{digest}\n"
            )
            console.print(f"\n[dim]Saved to {digest_file}[/]")
        else:
            console.print(f"[red]Claude CLI error:[/] {result.stderr[:300]}")

    except FileNotFoundError:
        console.print("[red]Claude CLI not found at /Users/tobiloba/.local/bin/claude[/]")
    except subprocess.TimeoutExpired:
        console.print("[red]Claude CLI timed out (120s)[/]")
    except Exception as e:
        console.print(f"[red]Error running digest: {e}[/]")


def cmd_ideas():
    """Generate product/startup ideas from trends + Tobiloba's skills."""
    data = load_trends()
    trends = data.get("trends", [])
    if not trends:
        console.print("[red]No trends found. Run --scan first.[/]")
        return

    console.print(Panel(
        "[bold]Generating product ideas from trends...[/]",
        border_style="green",
    ))

    # Build trends summary
    recent = trends[:80]
    trends_summary = "\n".join(
        f"- [{t['source']}] {t['title']} (tags: {', '.join(t.get('relevance_tags', []))})"
        for t in recent
    )

    # Load existing ideas for context
    existing_ideas = load_json(IDEAS_FILE)
    if isinstance(existing_ideas, list):
        existing_titles = [i.get("title", "") for i in existing_ideas]
    else:
        existing_titles = []

    prompt = f"""You are a startup idea generator for Tobiloba, who has these skills:
- AI/ML Engineering (LLMs, agents, fine-tuning, RAG)
- Solana/Rust development (smart contracts, DeFi)
- Full-stack web development (React, Next.js, Node.js, Python)
- Open source contributor
- DevTools builder

His existing ideas (avoid duplicates): {', '.join(existing_titles[:10])}

Based on these current tech trends:
{trends_summary}

Generate 5-10 product/startup ideas that:
1. Sit at the intersection of current trends and Tobiloba's skills
2. Have clear target users
3. Can be MVPd in 2-4 weeks
4. Are monetizable

For EACH idea, output EXACTLY this JSON format (output a JSON array, nothing else):
[
  {{
    "title": "Product Name",
    "description": "2-3 sentence description",
    "target_user": "Who would use this",
    "tech_stack": ["tech1", "tech2"],
    "trend_signals": ["which trends inspired this"],
    "score": {{
      "skill_fit": 1-10,
      "market": 1-10,
      "money": 1-10,
      "speed": 1-10,
      "excitement": 1-10,
      "total": sum of above
    }},
    "mvp_weeks": 2-4
  }}
]

Output ONLY the JSON array. No markdown, no explanation."""

    try:
        result = subprocess.run(
            [str(CLAUDE_CLI), "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=str(BASE),
        )

        if result.returncode != 0 or not result.stdout.strip():
            console.print(f"[red]Claude CLI error:[/] {result.stderr[:300]}")
            return

        # Parse the JSON from Claude's output
        output = result.stdout.strip()
        # Try to extract JSON array from the output
        json_start = output.find("[")
        json_end = output.rfind("]") + 1
        if json_start == -1 or json_end == 0:
            console.print("[red]Could not parse ideas from Claude output[/]")
            console.print(f"[dim]{output[:500]}[/]")
            return

        ideas = json.loads(output[json_start:json_end])

        # Display ideas
        table = Table(title="Generated Product Ideas", box=box.ROUNDED, show_lines=True)
        table.add_column("#", style="dim", width=3)
        table.add_column("Idea", style="bold", max_width=25)
        table.add_column("Description", max_width=40)
        table.add_column("Target", max_width=20)
        table.add_column("Score", justify="center", width=7)
        table.add_column("MVP", justify="center", width=5)

        for i, idea in enumerate(ideas, 1):
            score = idea.get("score", {})
            total = score.get("total", sum(
                score.get(k, 0) for k in ["skill_fit", "market", "money", "speed", "excitement"]
            ))
            score_color = "green" if total >= 35 else "yellow" if total >= 25 else "red"

            table.add_row(
                str(i),
                idea.get("title", "?"),
                idea.get("description", "")[:100],
                idea.get("target_user", "")[:40],
                f"[{score_color}]{total}/50[/]",
                f"{idea.get('mvp_weeks', '?')}w",
            )

        console.print(table)

        # Append to backlog
        existing = load_json(IDEAS_FILE)
        if not isinstance(existing, list):
            existing = []

        now = datetime.now().strftime("%Y-%m-%d")
        for idea in ideas:
            idea["id"] = f"idea-{uuid.uuid4().hex[:6]}"
            idea["status"] = "backlog"
            idea["created"] = now
            idea["source"] = "trends-aggregator"
            existing.append(idea)

        save_json(IDEAS_FILE, existing)
        console.print(f"\n[green]{len(ideas)} ideas added to backlog[/]")
        console.print(f"[dim]Total ideas in backlog: {len(existing)}[/]")

        # Also save to idea_pipeline in trends file
        data["idea_pipeline"] = ideas + data.get("idea_pipeline", [])
        data["idea_pipeline"] = data["idea_pipeline"][:50]  # Cap
        save_json(TRENDS_FILE, data)

    except json.JSONDecodeError as e:
        console.print(f"[red]JSON parse error: {e}[/]")
        console.print(f"[dim]Raw output: {output[:500]}[/]")
    except FileNotFoundError:
        console.print("[red]Claude CLI not found at /Users/tobiloba/.local/bin/claude[/]")
    except subprocess.TimeoutExpired:
        console.print("[red]Claude CLI timed out (120s)[/]")
    except Exception as e:
        console.print(f"[red]Error generating ideas: {e}[/]")


def cmd_report():
    """Full report: scan + digest + ideas in one go."""
    console.print(Panel(
        "[bold cyan]FULL TRENDS REPORT[/]\n[dim]scan -> digest -> ideas[/]",
        border_style="cyan",
    ))
    console.print()

    cmd_scan()
    console.print()
    cmd_digest()
    console.print()
    cmd_ideas()

    console.print()
    console.print(Panel(
        "[bold green]Report complete.[/]",
        border_style="green",
    ))


def cmd_show():
    """Show current trends summary (default when no subcommand)."""
    data = load_trends()
    trends = data.get("trends", [])

    if not trends:
        console.print("[dim]No trends yet. Run:[/] supertobi trends scan")
        return

    last_updated = data.get("last_updated", "never")
    console.print(f"[dim]Last updated: {last_updated}[/]\n")

    # Source breakdown
    source_counts = {}
    for t in trends:
        src = t["source"]
        source_counts[src] = source_counts.get(src, 0) + 1

    summary = Table(title="Trends Overview", box=box.ROUNDED)
    summary.add_column("Source", style="bold")
    summary.add_column("Count", justify="right")

    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        summary.add_row(src, str(count))
    summary.add_row("[bold]Total[/]", f"[bold]{len(trends)}[/]")
    console.print(summary)

    # Top trends by engagement
    console.print()
    top = sorted(
        [t for t in trends if t.get("engagement", 0) > 0],
        key=lambda x: x["engagement"],
        reverse=True,
    )[:15]

    if top:
        top_table = Table(title="Top Trends by Engagement", box=box.ROUNDED, show_lines=False)
        top_table.add_column("Source", style="dim", width=10)
        top_table.add_column("Title", max_width=55)
        top_table.add_column("Engagement", justify="right", style="green")
        top_table.add_column("Tags", style="cyan", max_width=25)

        for t in top:
            top_table.add_row(
                t["source"],
                t["title"][:55],
                str(t["engagement"]),
                ", ".join(t.get("relevance_tags", [])[:3]),
            )

        console.print(top_table)

    # Ideas pipeline
    pipeline = data.get("idea_pipeline", [])
    if pipeline:
        console.print(f"\n[bold]Idea Pipeline:[/] {len(pipeline)} ideas generated")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    parser = argparse.ArgumentParser(description="Super Tobi Tech Trends Aggregator")
    parser.add_argument("--scan", action="store_true", help="Fetch from all sources")
    parser.add_argument("--digest", action="store_true", help="AI analysis of trends")
    parser.add_argument("--ideas", action="store_true", help="Generate product ideas from trends")
    parser.add_argument("--report", action="store_true", help="Full report: scan + digest + ideas")
    parser.add_argument("--show", action="store_true", help="Show current trends summary")

    args = parser.parse_args()

    if args.scan:
        cmd_scan()
    elif args.digest:
        cmd_digest()
    elif args.ideas:
        cmd_ideas()
    elif args.report:
        cmd_report()
    else:
        cmd_show()


if __name__ == "__main__":
    main()
