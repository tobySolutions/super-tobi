#!/usr/bin/env python3
"""
Super Tobi — Nigerian Tax Tracker
Calculates estimated tax liability using Nigerian PIT brackets,
tracks income, and monitors filing deadlines.
"""

import argparse
import json
import os
from datetime import datetime, date

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAX_FILE = os.path.join(BASE_DIR, "data", "finance", "tax_info.json")

console = Console()


def load_tax():
    try:
        with open(TAX_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        console.print("[red]Tax info file not found or corrupted.[/]")
        return None


def save_tax(data):
    os.makedirs(os.path.dirname(TAX_FILE), exist_ok=True)
    with open(TAX_FILE, "w") as f:
        json.dump(data, f, indent=2)


def calculate_tax(annual_income, brackets):
    """Calculate Nigerian PIT using graduated brackets."""
    tax = 0.0
    breakdown = []

    for bracket in brackets:
        bmin = bracket["min"]
        bmax = bracket["max"]
        rate = bracket["rate"] / 100

        if annual_income <= bmin:
            break

        if bmax is None:
            taxable = annual_income - bmin
        else:
            taxable = min(annual_income, bmax) - bmin

        if taxable > 0:
            bracket_tax = taxable * rate
            tax += bracket_tax
            breakdown.append({
                "range": f"₦{bmin:,.0f} - {'₦' + f'{bmax:,.0f}' if bmax else '∞'}",
                "rate": f"{bracket['rate']}%",
                "taxable": taxable,
                "tax": bracket_tax,
            })

    # 5% surcharge for income above ₦25M
    surcharge = 0.0
    if annual_income > 25_000_000:
        surcharge = tax * 0.05

    return tax, surcharge, breakdown


def cmd_status():
    """Show current tax situation."""
    data = load_tax()
    if not data:
        return

    console.print(Panel(
        f"[bold]Tax Year:[/] {data['tax_year']}\n"
        f"[bold]Filing Status:[/] {data['filing_status']}\n"
        f"[bold]TIN:[/] {data.get('tin') or '[yellow]Not set[/]'}",
        title="[bold cyan]Tax Profile[/]",
        border_style="cyan",
    ))

    # Income streams
    table = Table(title="Income Streams", box=box.ROUNDED)
    table.add_column("Source", style="bold")
    table.add_column("Type", style="dim")
    table.add_column("Annual Estimate", justify="right")

    total_income = 0.0
    for stream in data.get("income_streams", []):
        est = stream.get("annual_estimate")
        if est:
            total_income += est
            est_str = f"[green]₦{est:,.0f}[/]"
        else:
            est_str = "[yellow]Not set[/]"
        table.add_row(stream["source"], stream["type"], est_str)

    console.print(table)

    # Estimated tax
    if total_income > 0:
        brackets = data.get("tax_brackets", [])
        tax, surcharge, _ = calculate_tax(total_income, brackets)
        total_tax = tax + surcharge
        effective_rate = (total_tax / total_income) * 100

        console.print(Panel(
            f"[bold]Estimated Annual Income:[/]  [green]₦{total_income:,.0f}[/]\n"
            f"[bold]Base Tax:[/]                 [red]₦{tax:,.0f}[/]\n"
            f"[bold]Surcharge (>₦25M):[/]       [red]₦{surcharge:,.0f}[/]\n"
            f"[bold]Total Estimated Tax:[/]      [bold red]₦{total_tax:,.0f}[/]\n"
            f"[bold]Effective Rate:[/]           [yellow]{effective_rate:.1f}%[/]",
            title="[bold yellow]Tax Estimate[/]",
            border_style="yellow",
        ))

    # Deadlines
    cmd_deadlines_inline(data)

    # Notes
    if data.get("notes"):
        console.print(f"\n[dim]Note: {data['notes']}[/]")


def cmd_estimate(annual_income):
    """Calculate estimated tax for a given income."""
    data = load_tax()
    if not data:
        return

    income = float(annual_income)
    brackets = data.get("tax_brackets", [])
    tax, surcharge, breakdown = calculate_tax(income, brackets)
    total_tax = tax + surcharge

    table = Table(title=f"Tax Estimate for ₦{income:,.0f}", box=box.ROUNDED)
    table.add_column("Bracket", style="bold")
    table.add_column("Rate", justify="center")
    table.add_column("Taxable Amount", justify="right")
    table.add_column("Tax", justify="right", style="red")

    for b in breakdown:
        table.add_row(
            b["range"],
            b["rate"],
            f"₦{b['taxable']:,.0f}",
            f"₦{b['tax']:,.0f}",
        )

    if surcharge > 0:
        table.add_row("", "", "", "")
        table.add_row("[bold]Surcharge (5%)[/]", "5%", f"on ₦{tax:,.0f}", f"₦{surcharge:,.0f}")

    console.print(table)

    effective_rate = (total_tax / income * 100) if income > 0 else 0
    monthly_tax = total_tax / 12

    console.print(Panel(
        f"[bold]Gross Income:[/]      [green]₦{income:,.0f}[/]\n"
        f"[bold]Total Tax:[/]         [bold red]₦{total_tax:,.0f}[/]\n"
        f"[bold]Monthly Tax:[/]       [red]₦{monthly_tax:,.0f}[/]\n"
        f"[bold]Take-home:[/]         [green]₦{income - total_tax:,.0f}[/]\n"
        f"[bold]Effective Rate:[/]    [yellow]{effective_rate:.1f}%[/]",
        title="[bold]Summary[/]",
        border_style="green",
    ))


def cmd_deadlines():
    """Show upcoming tax deadlines."""
    data = load_tax()
    if not data:
        return
    cmd_deadlines_inline(data)


def cmd_deadlines_inline(data):
    """Show deadlines from loaded data."""
    today = date.today()
    deadlines = data.get("key_dates", [])

    table = Table(title="Tax Deadlines", box=box.ROUNDED)
    table.add_column("Event", style="bold")
    table.add_column("Deadline")
    table.add_column("Status", justify="center")

    for dl in deadlines:
        event = dl["event"]
        deadline_str = dl["deadline"]

        if "each month" in deadline_str.lower():
            # Calculate next monthly deadline
            day_num = 10  # 10th of each month
            if today.day <= day_num:
                next_deadline = date(today.year, today.month, day_num)
            else:
                month = today.month + 1
                year = today.year
                if month > 12:
                    month = 1
                    year += 1
                next_deadline = date(year, month, day_num)
            days_until = (next_deadline - today).days
            deadline_display = next_deadline.isoformat()
        else:
            try:
                next_deadline = date.fromisoformat(deadline_str)
                days_until = (next_deadline - today).days
                deadline_display = deadline_str
            except ValueError:
                days_until = None
                deadline_display = deadline_str

        if days_until is not None:
            if days_until < 0:
                status = f"[bold red]OVERDUE by {abs(days_until)}d[/]"
            elif days_until == 0:
                status = "[bold red]TODAY[/]"
            elif days_until <= 7:
                status = f"[yellow]{days_until} days[/]"
            elif days_until <= 30:
                status = f"[cyan]{days_until} days[/]"
            else:
                status = f"[dim]{days_until} days[/]"
        else:
            status = "[dim]—[/]"

        table.add_row(event, deadline_display, status)

    console.print(table)


def cmd_log(source, amount):
    """Log income from a source."""
    data = load_tax()
    if not data:
        return

    amount = float(amount)
    found = False

    for stream in data.get("income_streams", []):
        if stream["source"].lower() == source.lower():
            current = stream.get("annual_estimate") or 0
            stream["annual_estimate"] = current + amount
            found = True
            console.print(f"[green]Logged:[/] ₦{amount:,.0f} to {stream['source']}")
            console.print(f"[dim]New annual estimate: ₦{stream['annual_estimate']:,.0f}[/]")
            break

    if not found:
        # Add as new income stream
        data["income_streams"].append({
            "source": source,
            "type": "other",
            "annual_estimate": amount,
        })
        console.print(f"[green]Added new income stream:[/] {source} — ₦{amount:,.0f}")

    save_tax(data)


def main():
    parser = argparse.ArgumentParser(description="Super Tobi Nigerian Tax Tracker")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--status", action="store_true", help="Current tax situation")
    group.add_argument("--estimate", metavar="INCOME", help="Estimate tax for annual income")
    group.add_argument("--deadlines", action="store_true", help="Upcoming tax deadlines")
    group.add_argument("--log", nargs=2, metavar=("SOURCE", "AMOUNT"), help="Log income")

    args = parser.parse_args()

    if args.status:
        cmd_status()
    elif args.estimate:
        cmd_estimate(args.estimate)
    elif args.deadlines:
        cmd_deadlines()
    elif args.log:
        cmd_log(args.log[0], args.log[1])


if __name__ == "__main__":
    main()
