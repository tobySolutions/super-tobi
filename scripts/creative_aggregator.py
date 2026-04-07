#!/usr/bin/env python3
"""
Super Tobi — Creative/Entertainment Industry Trends Aggregator

Aggregates signals from music, livestreaming, and movies/TV to generate
ideas for creators, artists, and people in the creative space.
"""

import argparse
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
TRENDS_FILE = DATA / "trends" / "creative_trends.json"
IDEAS_FILE = DATA / "ideas" / "backlog.json"
CLAUDE_CLI = "/Users/tobiloba/.local/bin/claude"

console = Console()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# UTILITIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def gen_id():
    return f"creative-{uuid.uuid4().hex[:8]}"


def ask_claude(prompt, timeout=90):
    """Use Claude CLI for AI analysis."""
    try:
        result = subprocess.run(
            [CLAUDE_CLI, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except FileNotFoundError:
        return "Claude CLI not found."
    except subprocess.TimeoutExpired:
        return "Claude CLI timed out."


def brave_search(query, count=5):
    """Search using Brave Search API if key is available."""
    api_key = os.environ.get("BRAVE_API_KEY", "")
    if not api_key:
        # Try loading from config
        keys_file = BASE / "config" / "api_keys.env"
        if keys_file.exists():
            for line in keys_file.read_text().splitlines():
                if line.startswith("BRAVE_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return None

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": api_key},
            params={"q": query, "count": count},
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for r in data.get("web", {}).get("results", []):
                results.append({
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", ""),
                })
            return results
    except Exception:
        pass
    return None


def tmdb_request(endpoint, params=None):
    """Make TMDB API request if key is available."""
    api_key = os.environ.get("TMDB_API_KEY", "")
    if not api_key:
        keys_file = BASE / "config" / "api_keys.env"
        if keys_file.exists():
            for line in keys_file.read_text().splitlines():
                if line.startswith("TMDB_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not api_key:
        return None

    try:
        base_url = "https://api.themoviedb.org/3"
        req_params = {"api_key": api_key}
        if params:
            req_params.update(params)
        resp = requests.get(f"{base_url}{endpoint}", params=req_params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SCAN — Fetch Creative Industry Trends
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def scan_music_trends():
    """Fetch music charts, genre trends, and music tech news."""
    console.print("\n[bold magenta]>> Scanning Music Trends...[/]")
    trends = []
    now = datetime.now().isoformat()

    # Try Brave Search for music trends
    queries = [
        "top music charts Billboard Spotify this week 2026",
        "trending music genres afrobeats hip-hop EDM 2026",
        "new music releases afrobeats R&B soul funk 2026",
        "AI music generation technology trends 2026",
    ]

    brave_results = []
    for q in queries:
        results = brave_search(q, count=3)
        if results:
            brave_results.extend(results)

    if brave_results:
        for r in brave_results:
            trends.append({
                "id": gen_id(),
                "source": "music",
                "title": r["title"],
                "description": r["description"],
                "url": r["url"],
                "category": "music",
                "relevance_tags": _extract_music_tags(r["title"] + " " + r["description"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(brave_results)} results from Brave Search")
    else:
        # Fallback to Claude CLI
        console.print("  [dim]No Brave API key — using Claude CLI...[/]")
        prompt = (
            "List the top 8 current trends in the music industry right now (March 2026). "
            "Cover: Billboard/Spotify chart trends, rising genres (especially afrobeats, hip-hop, EDM, R&B, "
            "classical crossover, funk, soul), notable new releases, and music tech innovations "
            "(AI music generation, DAW tools, distribution platforms). "
            "Return ONLY valid JSON array with objects: "
            '{"title": "...", "description": "...", "url": "", "tags": ["tag1", "tag2"]}'
        )
        with console.status("[bold cyan]  Asking Claude about music trends...[/]"):
            response = ask_claude(prompt)

        parsed = _parse_json_array(response)
        for item in parsed:
            trends.append({
                "id": gen_id(),
                "source": "music",
                "title": item.get("title", "Unknown"),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "category": "music",
                "relevance_tags": item.get("tags", ["music"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(parsed)} trends from Claude CLI")

    return trends


def scan_streaming_trends():
    """Fetch livestreaming and creator economy trends."""
    console.print("\n[bold blue]>> Scanning Streaming & Creator Economy...[/]")
    trends = []
    now = datetime.now().isoformat()

    queries = [
        "Twitch YouTube Kick trending categories livestreaming 2026",
        "creator economy news monetization tools 2026",
        "livestreaming technology trends platform updates 2026",
        "top creator news YouTube Twitch platform changes 2026",
    ]

    brave_results = []
    for q in queries:
        results = brave_search(q, count=3)
        if results:
            brave_results.extend(results)

    if brave_results:
        for r in brave_results:
            trends.append({
                "id": gen_id(),
                "source": "streaming",
                "title": r["title"],
                "description": r["description"],
                "url": r["url"],
                "category": "streaming",
                "relevance_tags": _extract_streaming_tags(r["title"] + " " + r["description"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(brave_results)} results from Brave Search")
    else:
        console.print("  [dim]No Brave API key — using Claude CLI...[/]")
        prompt = (
            "List the top 8 current trends in livestreaming and the creator economy (March 2026). "
            "Cover: trending categories on Twitch/YouTube/Kick, major platform changes, "
            "new monetization tools and features, creator economy statistics and shifts, "
            "livestreaming tech innovations. "
            "Return ONLY valid JSON array with objects: "
            '{"title": "...", "description": "...", "url": "", "tags": ["tag1", "tag2"]}'
        )
        with console.status("[bold cyan]  Asking Claude about streaming trends...[/]"):
            response = ask_claude(prompt)

        parsed = _parse_json_array(response)
        for item in parsed:
            trends.append({
                "id": gen_id(),
                "source": "streaming",
                "title": item.get("title", "Unknown"),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "category": "streaming",
                "relevance_tags": item.get("tags", ["streaming"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(parsed)} trends from Claude CLI")

    return trends


def scan_movie_trends():
    """Fetch movie and TV industry trends."""
    console.print("\n[bold yellow]>> Scanning Movies & TV...[/]")
    trends = []
    now = datetime.now().isoformat()

    # Try TMDB API first
    tmdb_data = tmdb_request("/trending/all/week")
    if tmdb_data and tmdb_data.get("results"):
        for item in tmdb_data["results"][:6]:
            media_type = item.get("media_type", "movie")
            title = item.get("title", item.get("name", "Unknown"))
            trends.append({
                "id": gen_id(),
                "source": "movies",
                "title": f"Trending: {title}",
                "description": item.get("overview", "")[:200],
                "url": f"https://www.themoviedb.org/{media_type}/{item.get('id', '')}",
                "category": "movies",
                "relevance_tags": [media_type, "trending"],
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(tmdb_data['results'][:6])} from TMDB API")

    # Also search for industry trends
    queries = [
        "box office trends upcoming movies 2026",
        "streaming platform exclusives Netflix Disney Apple 2026",
        "AI VFX virtual production film technology 2026",
    ]

    brave_results = []
    for q in queries:
        results = brave_search(q, count=3)
        if results:
            brave_results.extend(results)

    if brave_results:
        for r in brave_results:
            trends.append({
                "id": gen_id(),
                "source": "movies",
                "title": r["title"],
                "description": r["description"],
                "url": r["url"],
                "category": "movies",
                "relevance_tags": _extract_movie_tags(r["title"] + " " + r["description"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(brave_results)} from Brave Search")
    elif not tmdb_data:
        console.print("  [dim]No API keys — using Claude CLI...[/]")
        prompt = (
            "List the top 8 current trends in movies, TV, and the film industry (March 2026). "
            "Cover: upcoming major releases, box office trends, streaming platform exclusives, "
            "film tech trends (AI in VFX, virtual production, LED stages). "
            "Return ONLY valid JSON array with objects: "
            '{"title": "...", "description": "...", "url": "", "tags": ["tag1", "tag2"]}'
        )
        with console.status("[bold cyan]  Asking Claude about movie trends...[/]"):
            response = ask_claude(prompt)

        parsed = _parse_json_array(response)
        for item in parsed:
            trends.append({
                "id": gen_id(),
                "source": "movies",
                "title": item.get("title", "Unknown"),
                "description": item.get("description", ""),
                "url": item.get("url", ""),
                "category": "movies",
                "relevance_tags": item.get("tags", ["movies"]),
                "fetched_at": now,
            })
        console.print(f"  [green]+[/] {len(parsed)} trends from Claude CLI")

    return trends


def scan_cross_industry():
    """Identify cross-industry signals using Claude CLI."""
    console.print("\n[bold green]>> Scanning Cross-Industry Signals...[/]")
    trends = []
    now = datetime.now().isoformat()

    prompt = (
        "Identify 5-6 cross-industry signals where music, livestreaming, and film are converging "
        "right now (March 2026). Focus on: "
        "1) Where music + streaming + film overlap "
        "2) AI disruption in creative industries "
        "3) New distribution and monetization models "
        "4) Creator tool innovations that span multiple creative fields "
        "Return ONLY valid JSON array with objects: "
        '{"title": "...", "description": "...", "url": "", "tags": ["tag1", "tag2"]}'
    )
    with console.status("[bold cyan]  Analyzing cross-industry signals...[/]"):
        response = ask_claude(prompt)

    parsed = _parse_json_array(response)
    for item in parsed:
        trends.append({
            "id": gen_id(),
            "source": "creator_economy",
            "title": item.get("title", "Unknown"),
            "description": item.get("description", ""),
            "url": item.get("url", ""),
            "category": "creator_tools",
            "relevance_tags": item.get("tags", ["cross-industry"]),
            "fetched_at": now,
        })
    console.print(f"  [green]+[/] {len(parsed)} cross-industry signals")

    return trends


def cmd_scan():
    """Full creative industry trend scan."""
    console.print(Panel(
        "[bold]Creative Industry Trends Scan[/]\n[dim]Music | Streaming | Movies/TV | Creator Economy[/]",
        border_style="magenta",
    ))

    trends_data = load_json(TRENDS_FILE)
    if not trends_data:
        trends_data = {
            "last_updated": None,
            "sources": {
                "music": {"enabled": True, "genres": ["afrobeats", "hip-hop", "edm", "r&b"]},
                "streaming": {"enabled": True, "platforms": ["twitch", "youtube", "kick"]},
                "movies": {"enabled": True},
                "creator_economy": {"enabled": True},
            },
            "trends": [],
            "idea_pipeline": [],
        }

    all_trends = []

    sources = trends_data.get("sources", {})
    if sources.get("music", {}).get("enabled", True):
        all_trends.extend(scan_music_trends())
    if sources.get("streaming", {}).get("enabled", True):
        all_trends.extend(scan_streaming_trends())
    if sources.get("movies", {}).get("enabled", True):
        all_trends.extend(scan_movie_trends())
    if sources.get("creator_economy", {}).get("enabled", True):
        all_trends.extend(scan_cross_industry())

    # Merge: keep last 100 trends, newest first
    existing = trends_data.get("trends", [])
    existing_urls = {t.get("url") for t in existing if t.get("url")}
    new_trends = [t for t in all_trends if t.get("url") not in existing_urls or not t.get("url")]
    combined = new_trends + existing
    trends_data["trends"] = combined[:100]
    trends_data["last_updated"] = datetime.now().isoformat()

    save_json(TRENDS_FILE, trends_data)

    # Display summary
    console.print()
    summary = Table(title="Scan Summary", box=box.ROUNDED)
    summary.add_column("Source", style="bold")
    summary.add_column("New", justify="center")
    summary.add_column("Total", justify="center", style="dim")

    by_source = {}
    for t in new_trends:
        src = t.get("source", "unknown")
        by_source[src] = by_source.get(src, 0) + 1

    for src in ["music", "streaming", "movies", "creator_economy"]:
        total_for_src = sum(1 for t in combined[:100] if t.get("source") == src)
        summary.add_row(
            src.replace("_", " ").title(),
            f"[green]+{by_source.get(src, 0)}[/]",
            str(total_for_src),
        )

    console.print(summary)
    console.print(f"\n[dim]Saved to {TRENDS_FILE}[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DIGEST — AI-Powered Creative Industry Digest
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_digest():
    """Generate a creative industry digest using Claude CLI."""
    trends_data = load_json(TRENDS_FILE)
    trends = trends_data.get("trends", [])

    if not trends:
        console.print("[yellow]No trends found. Run --scan first.[/]")
        return

    console.print(Panel(
        "[bold]Creative Industry Digest[/]\n[dim]AI-generated analysis of current trends[/]",
        border_style="cyan",
    ))

    # Build context from trends
    music_trends = [t for t in trends if t.get("source") == "music"][:8]
    streaming_trends = [t for t in trends if t.get("source") == "streaming"][:8]
    movie_trends = [t for t in trends if t.get("source") == "movies"][:8]
    cross_trends = [t for t in trends if t.get("source") == "creator_economy"][:6]

    context_parts = []
    for label, items in [
        ("MUSIC", music_trends),
        ("STREAMING/CREATOR ECONOMY", streaming_trends),
        ("MOVIES/TV", movie_trends),
        ("CROSS-INDUSTRY", cross_trends),
    ]:
        if items:
            lines = [f"\n{label}:"]
            for t in items:
                lines.append(f"- {t['title']}: {t.get('description', '')[:120]}")
            context_parts.append("\n".join(lines))

    context = "\n".join(context_parts)

    prompt = (
        f"Based on these creative industry signals, write a concise digest for a tech-savvy "
        f"creator/builder (Tobiloba — AI researcher, full-stack dev, Solana builder based in Nigeria). "
        f"Structure the digest as:\n\n"
        f"1. **Top Music Trends** — Genres rising/falling, new tech, notable releases\n"
        f"2. **Livestreaming Landscape** — Platform changes, trending categories, creator shifts\n"
        f"3. **Movies & TV** — Industry shifts, streaming wars, film tech\n"
        f"4. **Creator Economy Opportunities** — New tools, monetization, platforms\n"
        f"5. **AI in Creative Work** — Where AI is changing music, video, streaming\n\n"
        f"Keep each section to 3-5 bullet points. Be specific and actionable.\n\n"
        f"Current signals:\n{context}"
    )

    with console.status("[bold cyan]Generating creative digest...[/]"):
        digest = ask_claude(prompt, timeout=120)

    console.print()
    console.print(Panel(
        digest,
        title="[bold magenta]Creative Industry Digest[/]",
        subtitle=f"[dim]{datetime.now().strftime('%Y-%m-%d %H:%M')}[/]",
        border_style="magenta",
        padding=(1, 2),
    ))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# IDEAS — Generate Creative Product Ideas
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_ideas():
    """Generate product ideas for the creative space."""
    trends_data = load_json(TRENDS_FILE)
    trends = trends_data.get("trends", [])

    if not trends:
        console.print("[yellow]No trends found. Run --scan first.[/]")
        return

    console.print(Panel(
        "[bold]Creative Industry Idea Generator[/]\n"
        "[dim]Products & tools for creators, musicians, filmmakers, streamers[/]",
        border_style="green",
    ))

    # Build context
    trend_summaries = []
    for t in trends[:20]:
        trend_summaries.append(f"- [{t.get('source')}] {t['title']}: {t.get('description', '')[:100]}")
    trend_context = "\n".join(trend_summaries)

    prompt = (
        f"Based on these creative industry trends, generate 7 product/tool/platform ideas "
        f"that serve creators, musicians, filmmakers, or streamers.\n\n"
        f"Builder profile: Tobiloba — AI researcher, full-stack dev (Python, TypeScript, React), "
        f"Solana/Rust builder, based in Nigeria. Has experience with LLMs, agents, and web3.\n\n"
        f"Each idea MUST:\n"
        f"- Serve a specific creative audience (musicians, streamers, filmmakers, etc.)\n"
        f"- Be buildable with AI + web tech (or Solana for web3 ideas)\n"
        f"- Have clear monetization (SaaS, marketplace, tools, tokens)\n"
        f"- Be MVP-able in 2-4 weeks\n\n"
        f"Return ONLY valid JSON array. Each object:\n"
        f'{{"title": "...", "description": "2-3 sentences", '
        f'"target_user": "who uses this", "tech_stack": ["tech1", "tech2"], '
        f'"monetization": "how it makes money", '
        f'"score": {{"skill_fit": 1-10, "market": 1-10, "money": 1-10, "speed": 1-10, "excitement": 1-10}}, '
        f'"tags": ["creative-tools", "tag2"]}}\n\n'
        f"Current trends:\n{trend_context}"
    )

    with console.status("[bold cyan]Generating creative product ideas...[/]"):
        response = ask_claude(prompt, timeout=120)

    parsed = _parse_json_array(response)

    if not parsed:
        console.print("[red]Failed to generate ideas. Try again.[/]")
        return

    # Score and display
    table = Table(title="Creative Product Ideas", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Idea", style="bold", max_width=25)
    table.add_column("Description", max_width=40)
    table.add_column("Audience", style="cyan", max_width=20)
    table.add_column("Score", justify="center", width=7)
    table.add_column("Monetization", style="green", max_width=20)

    ideas_to_save = []
    for i, idea in enumerate(parsed, 1):
        score = idea.get("score", {})
        total = sum(score.get(k, 0) for k in ["skill_fit", "market", "money", "speed", "excitement"])
        score["total"] = total

        color = "green" if total >= 35 else "yellow" if total >= 25 else "red"

        table.add_row(
            str(i),
            idea.get("title", "?"),
            idea.get("description", "")[:120],
            idea.get("target_user", "?"),
            f"[{color}]{total}/50[/]",
            idea.get("monetization", "?"),
        )

        # Prepare for saving
        ideas_to_save.append({
            "id": f"idea-creative-{uuid.uuid4().hex[:6]}",
            "title": idea.get("title", "Unknown"),
            "description": idea.get("description", ""),
            "target_user": idea.get("target_user", ""),
            "tech_stack": idea.get("tech_stack", []),
            "score": score,
            "status": "idea",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "tags": idea.get("tags", ["creative-tools"]),
            "monetization": idea.get("monetization", ""),
            "source": "creative-aggregator",
        })

    console.print()
    console.print(table)

    # Append to backlog
    backlog = []
    try:
        with open(IDEAS_FILE) as f:
            backlog = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        backlog = []

    existing_titles = {b.get("title", "").lower() for b in backlog}
    new_ideas = [idea for idea in ideas_to_save if idea["title"].lower() not in existing_titles]

    if new_ideas:
        backlog.extend(new_ideas)
        save_json(IDEAS_FILE, backlog)
        console.print(f"\n[green]+{len(new_ideas)} new ideas[/] saved to {IDEAS_FILE}")
    else:
        console.print(f"\n[dim]All ideas already in backlog.[/]")

    # Also store in creative trends pipeline
    trends_data["idea_pipeline"] = ideas_to_save + trends_data.get("idea_pipeline", [])
    trends_data["idea_pipeline"] = trends_data["idea_pipeline"][:30]
    save_json(TRENDS_FILE, trends_data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REPORT — Full Creative Industry Report
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_report():
    """Full creative industry report: scan + digest + ideas."""
    console.print(Panel(
        "[bold]Full Creative Industry Report[/]\n"
        "[dim]Scan + Digest + Ideas[/]",
        border_style="bold magenta",
        padding=(1, 2),
    ))

    cmd_scan()
    console.print("\n" + "=" * 60 + "\n")
    cmd_digest()
    console.print("\n" + "=" * 60 + "\n")
    cmd_ideas()

    console.print(Panel(
        "[bold green]Report complete.[/]\n"
        f"[dim]Trends: {TRENDS_FILE}\nIdeas: {IDEAS_FILE}[/]",
        border_style="green",
    ))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _parse_json_array(text):
    """Extract a JSON array from Claude's response."""
    if not text:
        return []

    # Try direct parse
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Try to find JSON array in the response
    start = text.find("[")
    if start == -1:
        return []

    # Find matching closing bracket
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return []
    return []


def _extract_music_tags(text):
    text_lower = text.lower()
    tags = []
    keywords = {
        "afrobeats": "afrobeats", "afropop": "afrobeats", "amapiano": "amapiano",
        "hip-hop": "hip-hop", "hip hop": "hip-hop", "rap": "hip-hop",
        "edm": "edm", "electronic": "edm",
        "r&b": "r&b", "rnb": "r&b",
        "classical": "classical", "funk": "funk", "soul": "soul",
        "ai music": "ai-music", "ai-generated": "ai-music",
        "spotify": "spotify", "apple music": "apple-music",
        "billboard": "charts", "chart": "charts",
        "distribution": "distribution", "daw": "music-tech",
    }
    for kw, tag in keywords.items():
        if kw in text_lower and tag not in tags:
            tags.append(tag)
    return tags or ["music"]


def _extract_streaming_tags(text):
    text_lower = text.lower()
    tags = []
    keywords = {
        "twitch": "twitch", "youtube": "youtube", "kick": "kick",
        "monetiz": "monetization", "revenue": "monetization",
        "creator": "creator-economy", "influencer": "creator-economy",
        "livestream": "livestreaming", "live stream": "livestreaming",
        "ai": "ai-tools", "subscription": "subscriptions",
        "tiktok": "tiktok", "shorts": "short-form",
    }
    for kw, tag in keywords.items():
        if kw in text_lower and tag not in tags:
            tags.append(tag)
    return tags or ["streaming"]


def _extract_movie_tags(text):
    text_lower = text.lower()
    tags = []
    keywords = {
        "vfx": "vfx", "visual effects": "vfx",
        "ai": "ai-film", "virtual production": "virtual-production",
        "box office": "box-office", "streaming": "streaming-wars",
        "netflix": "netflix", "disney": "disney", "apple": "apple-tv",
        "anime": "anime", "horror": "horror", "sci-fi": "sci-fi",
        "marvel": "marvel", "dc": "dc",
    }
    for kw, tag in keywords.items():
        if kw in text_lower and tag not in tags:
            tags.append(tag)
    return tags or ["movies"]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(description="Creative Industry Trends Aggregator")
    parser.add_argument("--scan", action="store_true", help="Scan for creative industry trends")
    parser.add_argument("--digest", action="store_true", help="AI-generated creative digest")
    parser.add_argument("--ideas", action="store_true", help="Generate creative product ideas")
    parser.add_argument("--report", action="store_true", help="Full report: scan + digest + ideas")

    args = parser.parse_args()

    if args.report:
        cmd_report()
    elif args.scan:
        cmd_scan()
    elif args.digest:
        cmd_digest()
    elif args.ideas:
        cmd_ideas()
    else:
        # Default: scan
        cmd_scan()


if __name__ == "__main__":
    main()
