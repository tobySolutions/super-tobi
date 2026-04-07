#!/usr/bin/env python3
"""
Super Tobi — Entertainment System
Movies, music, football — recommendations and tracking.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
PREFS_FILE = DATA / "entertainment" / "preferences.json"
CLAUDE_CLI = "/Users/tobiloba/.local/bin/claude"

console = Console()


def load_prefs():
    try:
        with open(PREFS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "movie_genres": ["action", "thriller", "sci-fi", "drama"],
            "music_genres": ["afrobeats", "hip-hop", "r&b"],
            "football": {"leagues": ["EPL", "La Liga", "Champions League"], "teams": []},
            "watched_movies": [],
            "music_queue": [],
            "settings": {"movie_sources": ["TMDB"], "music_sources": ["Spotify charts"]},
        }


def save_prefs(data):
    PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PREFS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def ask_claude(prompt):
    """Use Claude CLI as fallback for API-gated features."""
    try:
        result = subprocess.run(
            [CLAUDE_CLI, "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.stdout.strip() if result.returncode == 0 else result.stderr.strip()
    except FileNotFoundError:
        return "Claude CLI not found. Install it or set TMDB_API_KEY."
    except subprocess.TimeoutExpired:
        return "Claude CLI timed out."


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MOVIES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_movies():
    prefs = load_prefs()
    genres = prefs.get("movie_genres", [])
    watched = prefs.get("watched_movies", [])
    watched_titles = [m.get("title", "").lower() for m in watched]

    api_key = os.environ.get("TMDB_API_KEY", "")

    if api_key:
        # --- Trending movies from TMDB ---
        try:
            resp = requests.get(
                "https://api.themoviedb.org/3/trending/movie/week",
                params={"api_key": api_key},
                timeout=10,
            )
            resp.raise_for_status()
            movies = resp.json().get("results", [])[:10]

            table = Table(title="Trending Movies This Week", box=box.ROUNDED)
            table.add_column("#", style="dim", width=3)
            table.add_column("Title", style="bold", max_width=40)
            table.add_column("Rating", justify="center")
            table.add_column("Release", style="dim")
            table.add_column("Watched", justify="center")

            for i, m in enumerate(movies, 1):
                title = m.get("title", "?")
                rating = m.get("vote_average", 0)
                release = m.get("release_date", "?")
                is_watched = "yes" if title.lower() in watched_titles else ""
                rating_color = "green" if rating >= 7 else "yellow" if rating >= 5 else "red"
                table.add_row(
                    str(i),
                    title,
                    f"[{rating_color}]{rating:.1f}[/]",
                    release,
                    f"[dim]{is_watched}[/]",
                )

            console.print(table)
        except Exception as e:
            console.print(f"[yellow]TMDB error: {e}[/]")
            _movies_via_claude(genres)

        # --- Genre-based recommendations ---
        try:
            GENRE_IDS = {
                "action": 28, "thriller": 53, "sci-fi": 878,
                "drama": 18, "comedy": 35, "crime": 80,
                "horror": 27, "romance": 10749, "animation": 16,
            }
            genre_ids = [str(GENRE_IDS[g]) for g in genres if g in GENRE_IDS]
            if genre_ids:
                resp = requests.get(
                    "https://api.themoviedb.org/3/discover/movie",
                    params={
                        "api_key": api_key,
                        "with_genres": ",".join(genre_ids[:3]),
                        "sort_by": "popularity.desc",
                        "vote_average.gte": 6.5,
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                recs = resp.json().get("results", [])[:8]

                rec_table = Table(
                    title=f"For You ({', '.join(genres[:3])})", box=box.ROUNDED
                )
                rec_table.add_column("#", style="dim", width=3)
                rec_table.add_column("Title", style="bold", max_width=40)
                rec_table.add_column("Rating", justify="center")
                rec_table.add_column("Overview", max_width=50, style="dim")

                for i, m in enumerate(recs, 1):
                    title = m.get("title", "?")
                    if title.lower() in watched_titles:
                        continue
                    rating = m.get("vote_average", 0)
                    overview = m.get("overview", "")[:80] + "..."
                    rating_color = "green" if rating >= 7 else "yellow"
                    rec_table.add_row(
                        str(i), title, f"[{rating_color}]{rating:.1f}[/]", overview
                    )

                console.print(rec_table)
        except Exception as e:
            console.print(f"[yellow]Genre recs error: {e}[/]")
    else:
        _movies_via_claude(genres)


def _movies_via_claude(genres):
    console.print("[dim]No TMDB_API_KEY set. Using Claude for recommendations...[/]\n")
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = (
        f"Give me 10 movie recommendations. Today is {today}. "
        f"My preferred genres: {', '.join(genres)}. "
        f"Include a mix of recent releases and hidden gems. "
        f"Format as a numbered list with: title (year) - brief reason to watch. "
        f"Keep it concise."
    )
    result = ask_claude(prompt)
    console.print(Panel(result, title="[bold]Movie Recommendations[/]", border_style="magenta"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MUSIC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_music():
    prefs = load_prefs()
    genres = prefs.get("music_genres", [])

    today = datetime.now().strftime("%Y-%m-%d")
    prompt = (
        f"Give me music recommendations. Today is {today}. "
        f"My preferred genres: {', '.join(genres)}. "
        f"Include: 5 new/recent releases, 5 hidden gems or deep cuts. "
        f"Format as a numbered list: artist - track (genre). "
        f"Keep it concise."
    )

    with console.status("[bold cyan]Getting music recommendations...[/]"):
        result = ask_claude(prompt)

    console.print(Panel(result, title="[bold]Music Recommendations[/]", border_style="green"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FOOTBALL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_football():
    prefs = load_prefs()
    football = prefs.get("football", {})
    leagues = football.get("leagues", [])
    teams = football.get("teams", [])

    api_key = os.environ.get("FOOTBALL_API_KEY", "")

    if api_key:
        _football_via_api(api_key, leagues, teams)
    else:
        _football_via_claude(leagues, teams)


def _football_via_api(api_key, leagues, teams):
    """Use football-data.org API."""
    LEAGUE_MAP = {
        "EPL": "PL",
        "La Liga": "PD",
        "Champions League": "CL",
        "Serie A": "SA",
        "Bundesliga": "BL1",
        "Ligue 1": "FL1",
    }

    headers = {"X-Auth-Token": api_key}

    for league_name in leagues:
        code = LEAGUE_MAP.get(league_name)
        if not code:
            continue

        try:
            resp = requests.get(
                f"https://api.football-data.org/v4/competitions/{code}/matches",
                headers=headers,
                params={"status": "SCHEDULED", "limit": 5},
                timeout=10,
            )
            resp.raise_for_status()
            matches = resp.json().get("matches", [])

            if matches:
                table = Table(title=f"{league_name} — Upcoming", box=box.ROUNDED)
                table.add_column("Date", style="dim")
                table.add_column("Home", style="bold")
                table.add_column("vs", justify="center", style="dim")
                table.add_column("Away", style="bold")

                for m in matches:
                    date_str = m.get("utcDate", "")[:10]
                    home = m.get("homeTeam", {}).get("shortName", "?")
                    away = m.get("awayTeam", {}).get("shortName", "?")
                    table.add_row(date_str, home, "vs", away)

                console.print(table)
        except Exception as e:
            console.print(f"[yellow]{league_name} API error: {e}[/]")


def _football_via_claude(leagues, teams):
    today = datetime.now().strftime("%Y-%m-%d")
    teams_str = f" My teams: {', '.join(teams)}." if teams else ""
    prompt = (
        f"Give me a football update. Today is {today}. "
        f"Leagues I follow: {', '.join(leagues)}.{teams_str} "
        f"Include: upcoming matches this week, recent scores/results, "
        f"and any big transfer/injury news. Keep it concise and structured."
    )

    with console.status("[bold cyan]Getting football updates...[/]"):
        result = ask_claude(prompt)

    console.print(Panel(result, title="[bold]Football Update[/]", border_style="green"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WATCH / RATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_watch(movie_name):
    prefs = load_prefs()
    entry = {
        "title": movie_name,
        "watched_date": datetime.now().strftime("%Y-%m-%d"),
        "rating": None,
    }
    prefs["watched_movies"].append(entry)
    save_prefs(prefs)
    console.print(f"[green]Marked as watched:[/] {movie_name}")


def cmd_rate(movie_name, rating):
    prefs = load_prefs()
    rating = int(rating)
    if rating < 1 or rating > 10:
        console.print("[red]Rating must be 1-10.[/]")
        return

    found = False
    for m in prefs["watched_movies"]:
        if m["title"].lower() == movie_name.lower():
            m["rating"] = rating
            found = True
            break

    if not found:
        # Add as watched + rated
        prefs["watched_movies"].append({
            "title": movie_name,
            "watched_date": datetime.now().strftime("%Y-%m-%d"),
            "rating": rating,
        })

    save_prefs(prefs)
    stars = "★" * rating + "☆" * (10 - rating)
    console.print(f"[green]Rated:[/] {movie_name} — {stars} ({rating}/10)")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DISCOVER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def cmd_discover(genre):
    prefs = load_prefs()
    watched = [m.get("title", "") for m in prefs.get("watched_movies", [])]
    watched_str = f" I've already seen: {', '.join(watched[-10:])}." if watched else ""

    prompt = (
        f"Recommend 10 great {genre} movies and shows I should watch. "
        f"Include a mix of classics, modern hits, and underrated picks.{watched_str} "
        f"Format: numbered list with title (year) - one line why it's worth watching."
    )

    with console.status(f"[bold cyan]Discovering {genre}...[/]"):
        result = ask_claude(prompt)

    console.print(
        Panel(result, title=f"[bold]Discover: {genre.title()}[/]", border_style="magenta")
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    parser = argparse.ArgumentParser(description="Super Tobi Entertainment System")
    parser.add_argument("--movies", action="store_true", help="Movie recommendations")
    parser.add_argument("--music", action="store_true", help="Music recommendations")
    parser.add_argument("--football", action="store_true", help="Football updates")
    parser.add_argument("--watch", metavar="MOVIE", help="Mark a movie as watched")
    parser.add_argument("--rate", nargs=2, metavar=("MOVIE", "RATING"), help="Rate a movie 1-10")
    parser.add_argument("--discover", metavar="GENRE", help="Discover content by genre")

    args = parser.parse_args()

    if args.movies:
        cmd_movies()
    elif args.music:
        cmd_music()
    elif args.football:
        cmd_football()
    elif args.watch:
        cmd_watch(args.watch)
    elif args.rate:
        cmd_rate(args.rate[0], args.rate[1])
    elif args.discover:
        cmd_discover(args.discover)
    else:
        # Default: show all
        console.print("[bold cyan]SUPER TOBI[/] [dim]Entertainment[/]\n")
        cmd_movies()
        console.print()
        cmd_music()
        console.print()
        cmd_football()


if __name__ == "__main__":
    main()
