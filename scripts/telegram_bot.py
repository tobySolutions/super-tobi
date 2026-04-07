#!/usr/bin/env python3
"""
Super Tobi — Telegram Bot
Runs as a persistent bot that:
- Receives messages and forwards summaries to Tobiloba
- Can auto-reply based on rules
- Accepts commands from Tobiloba to control Super Tobi remotely

Commands (from Tobiloba only):
  /status — system status
  /messages — recent messages across all platforms
  /reply <platform> <contact> <message> — send a reply
  /workout — today's workout
  /remind — upcoming reminders
"""

import os
import sys
import json
import asyncio
import logging
import subprocess
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("super-tobi-telegram")

# Load config
OWNER_CHAT_ID = None  # Will be set on first /start from Tobiloba


def get_token():
    env_file = os.path.join(CONFIG_DIR, "api_keys.env")
    with open(env_file) as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN=") and "#" not in line:
                return line.strip().split("=", 1)[1]
    return None


def save_owner_id(chat_id):
    global OWNER_CHAT_ID
    OWNER_CHAT_ID = chat_id
    owner_file = os.path.join(CONFIG_DIR, "telegram_owner.json")
    with open(owner_file, "w") as f:
        json.dump({"owner_chat_id": chat_id}, f)


def load_owner_id():
    global OWNER_CHAT_ID
    owner_file = os.path.join(CONFIG_DIR, "telegram_owner.json")
    if os.path.exists(owner_file):
        with open(owner_file) as f:
            data = json.load(f)
            OWNER_CHAT_ID = data.get("owner_chat_id")
    return OWNER_CHAT_ID


def is_owner(update: Update) -> bool:
    return update.effective_chat.id == OWNER_CHAT_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if OWNER_CHAT_ID is None:
        save_owner_id(chat_id)
        await update.message.reply_text(
            "⚡ Super Tobi activated!\n\n"
            f"Your chat ID ({chat_id}) is now registered as the owner.\n\n"
            "Available commands:\n"
            "/status — System dashboard\n"
            "/messages — Recent messages\n"
            "/workout — Today's workout\n"
            "/remind — Upcoming reminders\n"
            "/finance — Financial summary"
        )
    elif is_owner(update):
        await update.message.reply_text("⚡ Super Tobi is running. Use /status for dashboard.")
    else:
        await update.message.reply_text("👋 Hey! This is Tobiloba's personal assistant bot.")


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    # Build quick status
    try:
        with open(os.path.join(DATA_DIR, "health", "log.json")) as f:
            health_log = json.load(f)
        workout_streak = len(health_log)
    except Exception:
        workout_streak = 0

    try:
        with open(os.path.join(DATA_DIR, "career", "jobs", "applications.json")) as f:
            apps = json.load(f)
        open_apps = len([a for a in apps if a.get("status") in ("applied", "interviewing")])
    except Exception:
        open_apps = 0

    try:
        with open(os.path.join(DATA_DIR, "ideas", "backlog.json")) as f:
            ideas = json.load(f)
        idea_count = len(ideas)
    except Exception:
        idea_count = 0

    msg = (
        "⚡ *SUPER TOBI STATUS*\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"💪 Workout streak: {workout_streak} days\n"
        f"💼 Open applications: {open_apps}\n"
        f"💡 Ideas in backlog: {idea_count}\n"
        f"🤖 Daemon: Running\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def workout_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    try:
        from datetime import datetime
        with open(os.path.join(DATA_DIR, "health", "plan.json")) as f:
            plan = json.load(f)
        day = datetime.now().strftime("%A").lower()
        today = plan.get("schedule", {}).get(day, {})
        focus = today.get("focus", "Rest")
        exercises = today.get("exercises", [])

        msg = f"💪 *{focus}*\n━━━━━━━━━━━━━━━━━━━\n"
        for ex in exercises:
            name = ex.get("name", "")
            sets = ex.get("sets", "")
            reps = ex.get("reps", ex.get("duration", ""))
            msg += f"▪️ {name}: {sets}x{reps}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error loading workout: {e}")


async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    try:
        from datetime import date, timedelta
        with open(os.path.join(DATA_DIR, "relationships", "birthdays.json")) as f:
            birthdays = json.load(f)

        today = date.today()
        upcoming = []
        for person in birthdays:
            if person.get("date") == "FILL-IN":
                continue
            month, day_num = person["date"].split("-")
            try:
                bday = date(today.year, int(month), int(day_num))
                if bday < today:
                    bday = date(today.year + 1, int(month), int(day_num))
                days_until = (bday - today).days
                if days_until <= 30:
                    upcoming.append((days_until, person["name"], person["date"]))
            except ValueError:
                continue

        upcoming.sort()
        msg = "📅 *Upcoming Birthdays*\n━━━━━━━━━━━━━━━━━━━\n"
        if upcoming:
            for days, name, dt in upcoming:
                if days == 0:
                    msg += f"🎂 *TODAY* — {name}\n"
                else:
                    msg += f"▪️ In {days} days — {name} ({dt})\n"
        else:
            msg += "No birthdays in the next 30 days."

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def finance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    try:
        with open(os.path.join(DATA_DIR, "finance", "transactions.json")) as f:
            txs = json.load(f)

        total_expenses = sum(t["amount"] for t in txs if t["type"] == "expense")
        total_income = sum(t["amount"] for t in txs if t["type"] == "income")
        food = sum(t["amount"] for t in txs if t.get("category") == "food")

        msg = (
            "💰 *Financial Summary*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📥 Income: ₦{total_income:,.0f}\n"
            f"📤 Expenses: ₦{total_expenses:,.0f}\n"
            f"🍔 Food: ₦{food:,.0f}\n"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def messages_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    try:
        # Pull WhatsApp message log
        whatsapp_log = os.path.join(DATA_DIR, "whatsapp_messages.json")
        wa_msgs = []
        if os.path.exists(whatsapp_log):
            with open(whatsapp_log) as f:
                wa_msgs = json.load(f)
            wa_msgs = [m for m in wa_msgs if m.get("direction") == "received"][-10:]

        # Pull Telegram messages (from the bot's own log)
        msg_log = os.path.join(DATA_DIR, "messages_log.json")
        tg_msgs = []
        if os.path.exists(msg_log):
            with open(msg_log) as f:
                tg_msgs = json.load(f)
            tg_msgs = tg_msgs[-10:]

        msg = "📨 *MESSAGE DIGEST*\n━━━━━━━━━━━━━━━━━━━\n\n"

        if wa_msgs:
            msg += "📱 *WhatsApp*\n"
            for m in wa_msgs[-5:]:
                msg += f"  {m.get('contact', '?')}: {m.get('text', '')[:60]}\n"
            msg += "\n"

        if tg_msgs:
            msg += "✈️ *Telegram*\n"
            for m in tg_msgs[-5:]:
                contact = m.get("contact", m.get("from_name", "?"))
                msg += f"  {contact}: {m.get('text', '')[:60]}\n"
            msg += "\n"

        if not wa_msgs and not tg_msgs:
            msg += "No new messages. Inbox zero! 🎉\n"

        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def twitter_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update):
        return

    await update.message.reply_text("🐦 Pulling your Twitter feed...")

    try:
        result = subprocess.run(
            [os.path.join(BASE_DIR, ".venv", "bin", "python"),
             os.path.join(BASE_DIR, "scripts", "twitter_feed.py"), "--my-tweets"],
            capture_output=True, text=True, timeout=30,
        )
        output = result.stdout.strip()
        if output:
            # Telegram has 4096 char limit
            if len(output) > 4000:
                output = output[:4000] + "\n..."
            await update.message.reply_text(f"```\n{output}\n```", parse_mode="Markdown")
        else:
            await update.message.reply_text("No tweets found or API error.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-command messages — log them and auto-reply using AI."""
    if is_owner(update):
        await update.message.reply_text(
            "💭 Got it. Commands:\n"
            "/status /workout /remind /finance /messages /twitter"
        )
    else:
        sender = update.effective_user.first_name or "Someone"
        text = update.message.text or ""

        # Notify Tobiloba
        if OWNER_CHAT_ID:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=f"📨 *New Telegram message from {sender}:*\n{text}",
                parse_mode="Markdown",
            )

        # Check if this contact is on auto-reply list
        smart_config_file = os.path.join(DATA_DIR, "relationships", "smart_reply_config.json")
        auto_reply = False
        if os.path.exists(smart_config_file):
            with open(smart_config_file) as f:
                config = json.load(f)
            for c in config.get("auto_reply_contacts", []):
                if sender.lower() in c.get("name", "").lower() or c.get("identifier", "") in str(update.effective_user.id):
                    auto_reply = True
                    break

        if auto_reply:
            # Generate AI reply as Tobiloba
            try:
                sys.path.insert(0, os.path.join(BASE_DIR, "scripts"))
                from ai import ask_claude

                reply = ask_claude(
                    f"You are Tobiloba replying to a Telegram message. Reply ONLY with the message text.\n"
                    f"Be casual, warm, direct. Keep it short like real texting. "
                    f"You're Nigerian, you might use pidgin naturally. NEVER sound like AI.\n\n"
                    f"{sender} said: {text}\n\n"
                    f"Reply as Tobiloba:",
                    timeout=20,
                )
                await update.message.reply_text(reply)

                # Notify owner what was auto-replied
                if OWNER_CHAT_ID:
                    await context.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=f"🤖 *Auto-replied to {sender}:*\n_{reply}_",
                        parse_mode="Markdown",
                    )
            except Exception as e:
                await update.message.reply_text("Hey! Tobi will get back to you soon 🤙")
                log.error(f"AI reply failed: {e}")
        else:
            # Default — acknowledge, don't AI reply
            await update.message.reply_text("Hey! Tobi will get back to you soon 🤙")


def main():
    token = get_token()
    if not token:
        print("No Telegram bot token found. Add TELEGRAM_BOT_TOKEN to config/api_keys.env")
        sys.exit(1)

    load_owner_id()

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("workout", workout_cmd))
    app.add_handler(CommandHandler("remind", remind_cmd))
    app.add_handler(CommandHandler("finance", finance_cmd))
    app.add_handler(CommandHandler("messages", messages_cmd))
    app.add_handler(CommandHandler("twitter", twitter_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("Super Tobi Telegram bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
