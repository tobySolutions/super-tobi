#!/usr/bin/env python3
"""
Super Tobi — Trading System (FOREX + Crypto)
Fetch prices, log trades, manage watchlist, set alerts.
"""

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
TRADING_FILE = DATA / "finance" / "trading.json"

console = Console()


def load_trading():
    try:
        with open(TRADING_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "watchlist": {"forex": [], "crypto": []},
            "trades": [],
            "strategies": [],
            "alerts": [],
            "settings": {
                "risk_per_trade_percent": 2,
                "max_daily_trades": 5,
                "preferred_timeframes": ["1h", "4h", "1d"],
            },
        }


def save_trading(data):
    TRADING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRADING_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRICES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CRYPTO_ID_MAP = {
    "SOL": "solana",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BONK": "bonk",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "MATIC": "matic-network",
    "ADA": "cardano",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "NEAR": "near",
    "ARB": "arbitrum",
    "OP": "optimism",
    "JUP": "jupiter-exchange-solana",
    "RAY": "raydium",
    "WIF": "dogwifcoin",
    "JTO": "jito-governance-token",
    "PYTH": "pyth-network",
}


def fetch_prices():
    data = load_trading()
    watchlist = data.get("watchlist", {})

    # --- Crypto prices via CoinGecko ---
    crypto_pairs = watchlist.get("crypto", [])
    crypto_symbols = []
    for pair in crypto_pairs:
        symbol = pair.split("/")[0].upper()
        crypto_symbols.append(symbol)

    coin_ids = [CRYPTO_ID_MAP[s] for s in crypto_symbols if s in CRYPTO_ID_MAP]
    crypto_prices = {}

    if coin_ids:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": ",".join(coin_ids),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            cg_data = resp.json()

            for symbol in crypto_symbols:
                cg_id = CRYPTO_ID_MAP.get(symbol)
                if cg_id and cg_id in cg_data:
                    price = cg_data[cg_id].get("usd", 0)
                    change = cg_data[cg_id].get("usd_24h_change", 0)
                    crypto_prices[f"{symbol}/USD"] = {
                        "price": price,
                        "change_24h": change,
                    }
        except Exception as e:
            console.print(f"[yellow]Crypto API error:[/] {e}")

    # --- Forex prices via exchangerate-api ---
    forex_pairs = watchlist.get("forex", [])
    forex_prices = {}

    if forex_pairs:
        try:
            resp = requests.get(
                "https://open.er-api.com/v6/latest/USD", timeout=10
            )
            resp.raise_for_status()
            rates = resp.json().get("rates", {})

            for pair in forex_pairs:
                parts = pair.split("/")
                if len(parts) != 2:
                    continue
                base, quote = parts[0].upper(), parts[1].upper()

                base_rate = rates.get(base, 0)
                quote_rate = rates.get(quote, 0)

                if base == "USD":
                    price = quote_rate
                elif quote == "USD":
                    price = 1 / base_rate if base_rate else 0
                else:
                    price = quote_rate / base_rate if base_rate else 0

                forex_prices[pair] = {"price": price, "change_24h": None}
        except Exception as e:
            console.print(f"[yellow]Forex API error:[/] {e}")

    # --- Display ---
    table = Table(title="Market Prices", box=box.ROUNDED)
    table.add_column("Pair", style="bold")
    table.add_column("Type", style="dim")
    table.add_column("Price", justify="right")
    table.add_column("24h Change", justify="right")

    for pair, info in sorted(crypto_prices.items()):
        price = info["price"]
        change = info["change_24h"]
        price_str = f"${price:,.6f}" if price < 0.01 else f"${price:,.2f}"
        if change is not None:
            color = "green" if change >= 0 else "red"
            change_str = f"[{color}]{change:+.2f}%[/]"
        else:
            change_str = "[dim]n/a[/]"
        table.add_row(pair, "[magenta]crypto[/]", price_str, change_str)

    for pair, info in sorted(forex_prices.items()):
        price = info["price"]
        price_str = f"{price:,.4f}" if price < 100 else f"{price:,.2f}"
        table.add_row(pair, "[cyan]forex[/]", price_str, "[dim]n/a[/]")

    console.print(table)

    # --- Check alerts ---
    alerts = data.get("alerts", [])
    triggered = []
    all_prices = {}
    for pair, info in crypto_prices.items():
        all_prices[pair.upper()] = info["price"]
    for pair, info in forex_prices.items():
        all_prices[pair.upper()] = info["price"]

    for alert in alerts:
        pair_key = alert["pair"].upper()
        if pair_key not in all_prices:
            continue
        current = all_prices[pair_key]
        if alert["direction"] == "above" and current >= alert["target_price"]:
            triggered.append(alert)
            console.print(
                f"[bold red]ALERT:[/] {alert['pair']} is ABOVE {alert['target_price']} (current: {current})"
            )
        elif alert["direction"] == "below" and current <= alert["target_price"]:
            triggered.append(alert)
            console.print(
                f"[bold red]ALERT:[/] {alert['pair']} is BELOW {alert['target_price']} (current: {current})"
            )

    if triggered:
        data["alerts"] = [a for a in alerts if a not in triggered]
        save_trading(data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRADE LOGGING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def log_trade(pair, side, entry, size, stoploss=None, takeprofit=None):
    data = load_trading()
    settings = data.get("settings", {})

    # Check daily trade limit
    today = datetime.now().strftime("%Y-%m-%d")
    today_trades = [
        t for t in data["trades"] if t.get("entry_time", "").startswith(today)
    ]
    max_daily = settings.get("max_daily_trades", 5)
    if len(today_trades) >= max_daily:
        console.print(
            f"[red]Daily trade limit reached ({max_daily}).[/] Override with care."
        )

    trade_id = str(uuid.uuid4())[:8]
    trade = {
        "id": trade_id,
        "pair": pair.upper(),
        "side": side.lower(),
        "entry_price": float(entry),
        "size": float(size),
        "stop_loss": float(stoploss) if stoploss else None,
        "take_profit": float(takeprofit) if takeprofit else None,
        "entry_time": datetime.now().isoformat(),
        "exit_price": None,
        "exit_time": None,
        "pnl": None,
        "status": "open",
    }

    data["trades"].append(trade)
    save_trading(data)

    # Calculate risk if stop loss provided
    risk_info = ""
    if stoploss:
        risk_per_unit = abs(float(entry) - float(stoploss))
        total_risk = risk_per_unit * float(size)
        risk_info = f"\n  Risk: ${total_risk:,.2f}"
        if takeprofit:
            reward_per_unit = abs(float(takeprofit) - float(entry))
            rr = reward_per_unit / risk_per_unit if risk_per_unit else 0
            risk_info += f" | R:R = 1:{rr:.1f}"

    console.print(
        Panel(
            f"[bold green]Trade logged[/]\n"
            f"  ID: {trade_id}\n"
            f"  {pair.upper()} {side.upper()} @ {float(entry):,.4f}\n"
            f"  Size: {float(size)}"
            f"{risk_info}",
            border_style="green",
        )
    )


def close_trade(trade_id, exit_price):
    data = load_trading()
    trade = None
    for t in data["trades"]:
        if t["id"] == trade_id and t["status"] == "open":
            trade = t
            break

    if not trade:
        console.print(f"[red]Trade {trade_id} not found or already closed.[/]")
        return

    exit_price = float(exit_price)
    entry_price = trade["entry_price"]
    size = trade["size"]

    if trade["side"] == "buy":
        pnl = (exit_price - entry_price) * size
    else:
        pnl = (entry_price - exit_price) * size

    trade["exit_price"] = exit_price
    trade["exit_time"] = datetime.now().isoformat()
    trade["pnl"] = round(pnl, 2)
    trade["status"] = "closed"

    save_trading(data)

    color = "green" if pnl >= 0 else "red"
    console.print(
        Panel(
            f"[bold {color}]Trade closed[/]\n"
            f"  ID: {trade_id}\n"
            f"  {trade['pair']} {trade['side'].upper()}\n"
            f"  Entry: {entry_price:,.4f} -> Exit: {exit_price:,.4f}\n"
            f"  P&L: [{color}]${pnl:+,.2f}[/]",
            border_style=color,
        )
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# JOURNAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def show_journal():
    data = load_trading()
    trades = data.get("trades", [])

    if not trades:
        console.print("[dim]No trades logged yet.[/]")
        return

    # Trade table
    table = Table(title="Trade Journal", box=box.ROUNDED)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Pair", style="bold")
    table.add_column("Side", justify="center")
    table.add_column("Entry", justify="right")
    table.add_column("Exit", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("P&L", justify="right")
    table.add_column("Status", justify="center")
    table.add_column("Date", style="dim")

    for t in reversed(trades[-20:]):
        side_color = "green" if t["side"] == "buy" else "red"
        entry_str = f"{t['entry_price']:,.4f}"
        exit_str = f"{t['exit_price']:,.4f}" if t["exit_price"] else "-"
        pnl_str = "-"
        if t["pnl"] is not None:
            pnl_color = "green" if t["pnl"] >= 0 else "red"
            pnl_str = f"[{pnl_color}]${t['pnl']:+,.2f}[/]"
        status_color = "yellow" if t["status"] == "open" else "dim"
        date_str = t.get("entry_time", "")[:10]
        table.add_row(
            t["id"],
            t["pair"],
            f"[{side_color}]{t['side'].upper()}[/]",
            entry_str,
            exit_str,
            f"{t['size']}",
            pnl_str,
            f"[{status_color}]{t['status']}[/]",
            date_str,
        )

    console.print(table)

    # Stats for closed trades
    closed = [t for t in trades if t["status"] == "closed"]
    if closed:
        wins = [t for t in closed if t.get("pnl", 0) > 0]
        losses = [t for t in closed if t.get("pnl", 0) <= 0]
        total_pnl = sum(t.get("pnl", 0) for t in closed)
        win_rate = len(wins) / len(closed) * 100 if closed else 0

        avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
        avg_rr = abs(avg_win / avg_loss) if avg_loss else 0

        stats_table = Table(title="Performance Stats", box=box.SIMPLE, show_header=False)
        stats_table.add_column("metric", style="bold")
        stats_table.add_column("value", justify="right")

        pnl_color = "green" if total_pnl >= 0 else "red"
        stats_table.add_row("Total Trades", str(len(closed)))
        stats_table.add_row("Win Rate", f"[{'green' if win_rate >= 50 else 'red'}]{win_rate:.1f}%[/]")
        stats_table.add_row("Total P&L", f"[{pnl_color}]${total_pnl:+,.2f}[/]")
        stats_table.add_row("Avg Win", f"[green]${avg_win:+,.2f}[/]")
        stats_table.add_row("Avg Loss", f"[red]${avg_loss:+,.2f}[/]")
        stats_table.add_row("Avg R:R", f"1:{avg_rr:.1f}")
        stats_table.add_row("Open Trades", str(len([t for t in trades if t["status"] == "open"])))

        console.print(stats_table)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# WATCHLIST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def manage_watchlist(action, pair):
    data = load_trading()
    pair = pair.upper()

    # Determine type
    crypto_symbols = set(CRYPTO_ID_MAP.keys())
    base = pair.split("/")[0] if "/" in pair else pair
    pair_type = "crypto" if base in crypto_symbols else "forex"

    current = data["watchlist"].get(pair_type, [])

    if action == "add":
        if pair in [p.upper() for p in current]:
            console.print(f"[yellow]{pair} already in {pair_type} watchlist.[/]")
            return
        current.append(pair)
        data["watchlist"][pair_type] = current
        save_trading(data)
        console.print(f"[green]Added {pair} to {pair_type} watchlist.[/]")

    elif action == "remove":
        upper_list = [p.upper() for p in current]
        if pair not in upper_list:
            console.print(f"[red]{pair} not in {pair_type} watchlist.[/]")
            return
        idx = upper_list.index(pair)
        current.pop(idx)
        data["watchlist"][pair_type] = current
        save_trading(data)
        console.print(f"[red]Removed {pair} from {pair_type} watchlist.[/]")

    # Show current watchlist
    console.print(f"\n[bold]Crypto:[/] {', '.join(data['watchlist'].get('crypto', []))}")
    console.print(f"[bold]Forex:[/]  {', '.join(data['watchlist'].get('forex', []))}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ALERTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def set_alert(pair, direction, price):
    data = load_trading()
    alert = {
        "pair": pair.upper(),
        "direction": direction.lower(),
        "target_price": float(price),
        "created": datetime.now().isoformat(),
    }
    data["alerts"].append(alert)
    save_trading(data)
    console.print(
        f"[green]Alert set:[/] {pair.upper()} {direction} {float(price):,.4f}"
    )

    # Show all active alerts
    if data["alerts"]:
        table = Table(title="Active Alerts", box=box.SIMPLE)
        table.add_column("Pair", style="bold")
        table.add_column("Direction")
        table.add_column("Target", justify="right")
        for a in data["alerts"]:
            table.add_row(a["pair"], a["direction"], f"{a['target_price']:,.4f}")
        console.print(table)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    parser = argparse.ArgumentParser(description="Super Tobi Trading System")
    parser.add_argument("--prices", action="store_true", help="Fetch current prices")
    parser.add_argument(
        "--log",
        nargs=4,
        metavar=("PAIR", "SIDE", "ENTRY", "SIZE"),
        help="Log a trade: pair side entry size",
    )
    parser.add_argument("--sl", type=float, help="Stop loss (use with --log)")
    parser.add_argument("--tp", type=float, help="Take profit (use with --log)")
    parser.add_argument(
        "--close",
        nargs=2,
        metavar=("TRADE_ID", "EXIT_PRICE"),
        help="Close a trade",
    )
    parser.add_argument("--journal", action="store_true", help="Show trade journal")
    parser.add_argument(
        "--watchlist",
        nargs=2,
        metavar=("ACTION", "PAIR"),
        help="Manage watchlist: add/remove pair",
    )
    parser.add_argument(
        "--alert",
        nargs=3,
        metavar=("PAIR", "DIRECTION", "PRICE"),
        help="Set price alert: pair above|below price",
    )

    args = parser.parse_args()

    if args.prices:
        fetch_prices()
    elif args.log:
        pair, side, entry, size = args.log
        log_trade(pair, side, entry, size, stoploss=args.sl, takeprofit=args.tp)
    elif args.close:
        trade_id, exit_price = args.close
        close_trade(trade_id, exit_price)
    elif args.journal:
        show_journal()
    elif args.watchlist:
        action, pair = args.watchlist
        manage_watchlist(action, pair)
    elif args.alert:
        pair, direction, price = args.alert
        set_alert(pair, direction, price)
    else:
        # Default: show prices
        fetch_prices()


if __name__ == "__main__":
    main()
