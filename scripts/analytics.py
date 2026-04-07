#!/usr/bin/env python3
"""
Super Tobi — Application Funnel Analytics
Tracks conversion rates, response times, and identifies what's working.
Inspired by AutoApply AI's funnel dashboard.

Answers:
- What's my application-to-interview conversion rate?
- Which job boards produce the most interviews?
- What score range gets the most responses?
- How long do companies take to respond?
- What's my daily/weekly application velocity?
"""

import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, date, timedelta

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPLICATIONS_FILE = os.path.join(BASE_DIR, "data", "career", "jobs", "applications.json")

console = Console()


def load_apps():
    with open(APPLICATIONS_FILE) as f:
        return json.load(f)


def funnel_report():
    """Show the full application funnel."""
    apps = load_apps()
    total = len(apps)

    statuses = Counter(a.get("status", "unknown") for a in apps)

    # Funnel stages
    discovered = statuses.get("discovered", 0)
    applied = statuses.get("applied", 0)
    interviewing = statuses.get("interviewing", 0) + statuses.get("interview", 0)
    offered = statuses.get("offered", 0)
    rejected = statuses.get("rejected", 0)
    blocked = statuses.get("blocked", 0)
    expired = statuses.get("expired", 0)
    action_needed = statuses.get("action_needed", 0)

    console.print(Panel.fit(
        f"[bold]Application Funnel[/bold]\n"
        f"Total tracked: [bold]{total}[/bold]",
        border_style="cyan"
    ))

    # Funnel bars
    max_width = 40
    stages = [
        ("Discovered", discovered, "yellow"),
        ("Applied", applied, "green"),
        ("Interviewing", interviewing, "magenta"),
        ("Offered", offered, "bold green"),
        ("Rejected", rejected, "red"),
        ("Blocked", blocked, "dim"),
        ("Expired", expired, "dim"),
        ("Action needed", action_needed, "bold yellow"),
    ]

    for label, count, color in stages:
        if count == 0 and label in ("Offered", "Interviewing"):
            bar_width = 0
        else:
            bar_width = int((count / max(total, 1)) * max_width)
        bar = "█" * bar_width + "░" * (max_width - bar_width)
        pct = (count / max(total, 1)) * 100
        console.print(f"  [{color}]{label:15s}[/] [{color}]{bar}[/] {count:>4} ({pct:.1f}%)")

    # Conversion rates
    console.print()
    if applied > 0:
        interview_rate = (interviewing / applied) * 100
        console.print(f"  📊 Application → Interview: [bold]{interview_rate:.1f}%[/bold]")
    if interviewing > 0:
        offer_rate = (offered / interviewing) * 100
        console.print(f"  📊 Interview → Offer: [bold]{offer_rate:.1f}%[/bold]")
    if applied > 0:
        rejection_rate = (rejected / applied) * 100
        console.print(f"  📊 Rejection rate: [red]{rejection_rate:.1f}%[/red]")
        block_rate = (blocked / total) * 100
        console.print(f"  📊 Block rate (automation): [dim]{block_rate:.1f}%[/dim]")


def board_performance():
    """Which job boards produce results?"""
    apps = load_apps()

    board_stats = defaultdict(lambda: {"total": 0, "applied": 0, "interview": 0, "rejected": 0})

    for a in apps:
        board = a.get("board", "Unknown")
        board_stats[board]["total"] += 1
        if a.get("status") == "applied":
            board_stats[board]["applied"] += 1
        elif a.get("status") in ("interviewing", "interview"):
            board_stats[board]["interview"] += 1
        elif a.get("status") == "rejected":
            board_stats[board]["rejected"] += 1

    table = Table(title="Job Board Performance", box=box.ROUNDED)
    table.add_column("Board", style="bold")
    table.add_column("Found", justify="right")
    table.add_column("Applied", justify="right", style="green")
    table.add_column("Interviews", justify="right", style="magenta")
    table.add_column("Rejected", justify="right", style="red")
    table.add_column("Hit Rate", justify="right")

    for board, stats in sorted(board_stats.items(), key=lambda x: -x[1]["total"]):
        hit_rate = ""
        if stats["applied"] > 0:
            rate = (stats["interview"] / stats["applied"]) * 100
            hit_rate = f"{rate:.0f}%"
        table.add_row(
            board,
            str(stats["total"]),
            str(stats["applied"]),
            str(stats["interview"]),
            str(stats["rejected"]),
            hit_rate,
        )

    console.print(table)


def score_analysis():
    """What score ranges get responses?"""
    apps = load_apps()

    ranges = {
        "0-20": {"applied": 0, "response": 0},
        "21-40": {"applied": 0, "response": 0},
        "41-60": {"applied": 0, "response": 0},
        "61-80": {"applied": 0, "response": 0},
        "81-100": {"applied": 0, "response": 0},
    }

    for a in apps:
        score = a.get("score", 0)
        if a.get("status") not in ("applied", "interviewing", "interview", "rejected", "offered"):
            continue

        if score <= 20:
            key = "0-20"
        elif score <= 40:
            key = "21-40"
        elif score <= 60:
            key = "41-60"
        elif score <= 80:
            key = "61-80"
        else:
            key = "81-100"

        ranges[key]["applied"] += 1
        if a.get("status") in ("interviewing", "interview", "offered"):
            ranges[key]["response"] += 1

    table = Table(title="Score Range → Response Rate", box=box.ROUNDED)
    table.add_column("Score Range", style="bold")
    table.add_column("Applied", justify="right")
    table.add_column("Responded", justify="right", style="green")
    table.add_column("Rate", justify="right")

    for range_name, stats in ranges.items():
        rate = ""
        if stats["applied"] > 0:
            rate = f"{(stats['response'] / stats['applied']) * 100:.0f}%"
        table.add_row(range_name, str(stats["applied"]), str(stats["response"]), rate)

    console.print(table)


def velocity():
    """Application velocity — daily/weekly trends."""
    apps = load_apps()
    today = date.today()

    daily = Counter()
    for a in apps:
        d = a.get("applied_date") or a.get("discovered_date", "")
        if d:
            try:
                day = datetime.strptime(d, "%Y-%m-%d").date()
                if (today - day).days <= 30:
                    daily[d] += 1
            except ValueError:
                pass

    if not daily:
        console.print("[dim]No application data in the last 30 days.[/dim]")
        return

    # Last 14 days sparkline
    console.print(Panel.fit("[bold]Application Velocity (last 14 days)[/bold]", border_style="cyan"))
    for i in range(13, -1, -1):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        count = daily.get(d, 0)
        day_name = (today - timedelta(days=i)).strftime("%a %m/%d")
        bar = "█" * count
        color = "green" if count >= 3 else "yellow" if count >= 1 else "dim"
        console.print(f"  {day_name}  [{color}]{bar or '·':20s}[/] {count}")

    # Weekly totals
    this_week = sum(daily.get((today - timedelta(days=i)).strftime("%Y-%m-%d"), 0) for i in range(7))
    last_week = sum(daily.get((today - timedelta(days=i)).strftime("%Y-%m-%d"), 0) for i in range(7, 14))
    console.print(f"\n  This week: [bold]{this_week}[/bold]  |  Last week: {last_week}")


def rejection_analysis():
    """Analyze rejection patterns."""
    apps = load_apps()
    rejected = [a for a in apps if a.get("status") == "rejected"]

    if not rejected:
        console.print("[dim]No rejections recorded yet.[/dim]")
        return

    console.print(Panel.fit(f"[bold red]Rejection Analysis ({len(rejected)} total)[/bold red]", border_style="red"))

    # By company
    companies = Counter(a.get("company", "Unknown") for a in rejected)
    for company, count in companies.most_common(10):
        console.print(f"  {company}: {count}")

    # Common patterns in notes
    notes = [a.get("notes", "") for a in rejected if a.get("notes")]
    if notes:
        console.print(f"\n  [dim]Notes from rejections:[/dim]")
        for note in notes[:5]:
            console.print(f"    • {note[:80]}")


def full_report():
    """Run all analytics."""
    funnel_report()
    console.print()
    board_performance()
    console.print()
    score_analysis()
    console.print()
    velocity()
    console.print()
    rejection_analysis()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi — Application Analytics")
    parser.add_argument("--funnel", action="store_true", help="Application funnel")
    parser.add_argument("--boards", action="store_true", help="Board performance")
    parser.add_argument("--scores", action="store_true", help="Score range analysis")
    parser.add_argument("--velocity", action="store_true", help="Application velocity")
    parser.add_argument("--rejections", action="store_true", help="Rejection analysis")
    parser.add_argument("--full", action="store_true", help="Full report")
    args = parser.parse_args()

    if args.funnel:
        funnel_report()
    elif args.boards:
        board_performance()
    elif args.scores:
        score_analysis()
    elif args.velocity:
        velocity()
    elif args.rejections:
        rejection_analysis()
    elif args.full:
        full_report()
    else:
        full_report()


if __name__ == "__main__":
    main()
