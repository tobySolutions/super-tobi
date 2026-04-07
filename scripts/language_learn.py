#!/usr/bin/env python3
"""
Super Tobi Language Learning System — spaced repetition, AI-powered lessons & conversation practice.
"""

import argparse
import json
import random
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

BASE = Path(__file__).resolve().parent.parent
DATA_FILE = BASE / "data" / "learning" / "languages.json"
CLAUDE_CLI = "/Users/tobiloba/.local/bin/claude"

console = Console()


def load_data():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        console.print("[red]Error:[/] Could not load languages.json")
        sys.exit(1)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_language(data, code):
    for lang in data["languages"]:
        if lang["code"] == code or lang["name"].lower() == code.lower():
            return lang
    console.print(f"[red]Language not found:[/] {code}")
    available = ", ".join(f"{l['name']} ({l['code']})" for l in data["languages"])
    console.print(f"[dim]Available: {available}[/]")
    sys.exit(1)


def ask_claude(prompt):
    """Call Claude CLI and return the response."""
    try:
        result = subprocess.run(
            [CLAUDE_CLI, "-p", prompt],
            capture_output=True, text=True, timeout=60
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[AI response timed out]"
    except FileNotFoundError:
        return "[Claude CLI not found at expected path]"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LESSON
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_lesson(lang_code):
    """Teach a new lesson: 5 vocabulary words + 2 phrases with AI tips."""
    data = load_data()
    lang = get_language(data, lang_code)
    name = lang["name"]

    # Pick 5 words and 2 phrases that are due for review or least practiced
    today = date.today().isoformat()

    # Sort vocab by least practiced
    vocab = sorted(lang["vocabulary"], key=lambda w: w["correct"] + w["incorrect"])
    lesson_words = vocab[:5]

    phrases = sorted(lang["phrases"], key=lambda p: p["correct"] + p["incorrect"])
    lesson_phrases = phrases[:2]

    console.print(Panel(
        f"[bold]{name} Lesson[/]\n[dim]Session #{lang['total_sessions'] + 1}[/]",
        border_style="cyan"
    ))

    # Display vocabulary
    console.print("\n[bold cyan]Vocabulary[/]\n")
    word_table = Table(box=box.ROUNDED, show_lines=True)
    word_table.add_column("#", style="dim", width=3)
    word_table.add_column("Word", style="bold")
    word_table.add_column("Transliteration", style="yellow")
    word_table.add_column("Meaning", style="green")

    word_list_for_ai = []
    for i, w in enumerate(lesson_words, 1):
        word_table.add_row(str(i), w["word"], w.get("transliteration", ""), w["translation"])
        word_list_for_ai.append(f"{w['word']} ({w['translation']})")

    console.print(word_table)

    # Display phrases
    console.print("\n[bold cyan]Phrases[/]\n")
    phrase_table = Table(box=box.ROUNDED, show_lines=True)
    phrase_table.add_column("#", style="dim", width=3)
    phrase_table.add_column("Phrase", style="bold")
    phrase_table.add_column("Transliteration", style="yellow")
    phrase_table.add_column("Meaning", style="green")

    phrase_list_for_ai = []
    for i, p in enumerate(lesson_phrases, 1):
        phrase_table.add_row(str(i), p["phrase"], p.get("transliteration", ""), p["translation"])
        phrase_list_for_ai.append(f"{p['phrase']} ({p['translation']})")

    console.print(phrase_table)

    # Get AI pronunciation tips and example sentences
    console.print("\n")
    with console.status("[bold cyan]Getting pronunciation tips and examples from AI...[/]"):
        words_str = ", ".join(word_list_for_ai)
        phrases_str = ", ".join(phrase_list_for_ai)
        prompt = (
            f"I'm learning {name}. Give me brief pronunciation tips and one example sentence for each of these words and phrases. "
            f"Keep it concise — 1-2 lines per item. Format nicely with the word/phrase as a header.\n\n"
            f"Words: {words_str}\n\nPhrases: {phrases_str}"
        )
        tips = ask_claude(prompt)

    console.print(Panel(tips, title="[bold yellow]Pronunciation Tips & Examples[/]", border_style="yellow", padding=(1, 2)))

    # Update session count
    lang["total_sessions"] += 1
    lang["streak"] += 1
    save_data(data)

    console.print(f"\n[bold green]Lesson complete![/] Session #{lang['total_sessions']} recorded.")
    console.print(f"[dim]Streak: {lang['streak']} days | Run 'supertobi lang quiz {lang_code}' to test yourself[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QUIZ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_quiz(lang_code):
    """Spaced repetition quiz on learned vocabulary."""
    data = load_data()
    lang = get_language(data, lang_code)
    name = lang["name"]
    today = date.today().isoformat()

    # Collect items due for review
    due_vocab = [w for w in lang["vocabulary"] if w.get("next_review", today) <= today]
    due_phrases = [p for p in lang["phrases"] if p.get("next_review", today) <= today]

    all_items = []
    for w in due_vocab:
        all_items.append(("vocab", w))
    for p in due_phrases:
        all_items.append(("phrase", p))

    if not all_items:
        console.print(f"[dim]No {name} items due for review today. Come back later![/]")
        next_reviews = []
        for w in lang["vocabulary"]:
            next_reviews.append(w.get("next_review", "9999-99-99"))
        for p in lang["phrases"]:
            next_reviews.append(p.get("next_review", "9999-99-99"))
        if next_reviews:
            earliest = min(next_reviews)
            console.print(f"[dim]Next review due: {earliest}[/]")
        return

    random.shuffle(all_items)
    quiz_items = all_items[:10]  # Cap at 10 per session

    console.print(Panel(
        f"[bold]{name} Quiz[/]\n[dim]{len(quiz_items)} items due for review[/]",
        border_style="magenta"
    ))

    correct_count = 0
    total = len(quiz_items)

    for i, (item_type, item) in enumerate(quiz_items, 1):
        if item_type == "vocab":
            source = item["word"]
            answer = item["translation"]
            hint = item.get("transliteration", "")
        else:
            source = item["phrase"]
            answer = item["translation"]
            hint = item.get("transliteration", "")

        console.print(f"\n[bold cyan]({i}/{total})[/] What does this mean?")
        console.print(f"  [bold]{source}[/]")
        if hint:
            console.print(f"  [dim]({hint})[/]")

        user_answer = Prompt.ask("  Your answer")

        # Check answer (case-insensitive, flexible matching)
        correct = answer.lower().strip()
        given = user_answer.lower().strip()

        # Accept if the answer contains the key words
        is_correct = (given == correct or
                      given in correct or
                      correct in given or
                      any(word in given for word in correct.split() if len(word) > 3))

        if is_correct:
            console.print("  [bold green]Correct![/]")
            item["correct"] = item.get("correct", 0) + 1
            correct_count += 1
            # Increase interval (spaced repetition)
            current_interval = item.get("interval_days", 1)
            new_interval = min(current_interval * 2, 30)  # Cap at 30 days
            item["interval_days"] = new_interval
        else:
            console.print(f"  [bold red]Not quite.[/] The answer is: [green]{answer}[/]")
            item["incorrect"] = item.get("incorrect", 0) + 1
            # Reset interval on incorrect
            item["interval_days"] = 1

        # Set next review date
        next_date = date.today() + timedelta(days=item["interval_days"])
        item["next_review"] = next_date.isoformat()

    # Summary
    pct = (correct_count / total) * 100
    color = "green" if pct >= 80 else "yellow" if pct >= 50 else "red"
    console.print(f"\n[bold {color}]Score: {correct_count}/{total} ({pct:.0f}%)[/]")

    lang["total_sessions"] += 1
    save_data(data)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PRACTICE (Conversation)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_practice(lang_code):
    """AI conversation practice — Claude acts as a native speaker."""
    data = load_data()
    lang = get_language(data, lang_code)
    name = lang["name"]
    level = lang.get("level", "beginner")

    # Build context from known vocabulary
    known_words = [f"{w['word']} ({w['translation']})" for w in lang["vocabulary"][:15]]
    words_str = ", ".join(known_words)

    console.print(Panel(
        f"[bold]{name} Conversation Practice[/]\n"
        f"[dim]Level: {level} | Type 'quit' to exit[/]\n"
        f"[dim]Claude will speak {name}, correct your mistakes, and help you learn.[/]",
        border_style="green"
    ))

    system_context = (
        f"You are a friendly native {name} speaker having a conversation with a {level}-level learner named Tobiloba. "
        f"He is from Nigeria and wants to learn {name}. "
        f"Rules:\n"
        f"1. Start with a simple greeting in {name}\n"
        f"2. Keep your {name} simple for a {level}\n"
        f"3. After each exchange, briefly note any grammar/pronunciation corrections in English\n"
        f"4. Provide the English translation in parentheses after your {name} text\n"
        f"5. Gradually introduce new vocabulary\n"
        f"6. Be encouraging and patient\n"
        f"Known vocabulary: {words_str}\n"
        f"Keep responses concise — 2-3 sentences in {name} max per turn."
    )

    conversation_history = []

    # Initial greeting from AI
    with console.status(f"[bold green]{name} speaker is typing...[/]"):
        initial = ask_claude(system_context + "\n\nStart the conversation with a greeting.")
    console.print(f"\n[bold green]{name} Speaker:[/]")
    console.print(Panel(initial, border_style="green", padding=(0, 2)))
    conversation_history.append(f"AI: {initial}")

    while True:
        user_input = Prompt.ask(f"\n[bold cyan]You[/]")
        if user_input.lower() in ("quit", "exit", "q"):
            break

        conversation_history.append(f"Tobiloba: {user_input}")

        # Build conversation prompt
        history_str = "\n".join(conversation_history[-10:])  # Last 10 exchanges
        prompt = (
            f"{system_context}\n\n"
            f"Conversation so far:\n{history_str}\n\n"
            f"Continue the conversation. Respond to what Tobiloba said, correct any mistakes, "
            f"and keep the conversation going naturally."
        )

        with console.status(f"[bold green]{name} speaker is typing...[/]"):
            response = ask_claude(prompt)

        console.print(f"\n[bold green]{name} Speaker:[/]")
        console.print(Panel(response, border_style="green", padding=(0, 2)))
        conversation_history.append(f"AI: {response}")

    # Update session count
    lang["total_sessions"] += 1
    save_data(data)
    console.print(f"\n[bold green]Practice session complete![/] Session #{lang['total_sessions']} recorded.")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PROGRESS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_progress():
    """Show progress across all languages."""
    data = load_data()

    console.print(Panel("[bold]Language Learning Progress[/]", border_style="cyan"))

    for lang in data["languages"]:
        priority_colors = {"high": "red", "medium": "yellow", "low": "dim"}
        p_color = priority_colors.get(lang["priority"], "white")

        # Stats
        total_vocab = len(lang["vocabulary"])
        mastered_vocab = sum(1 for w in lang["vocabulary"] if w.get("correct", 0) >= 5)
        total_phrases = len(lang["phrases"])
        mastered_phrases = sum(1 for p in lang["phrases"] if p.get("correct", 0) >= 5)

        # Due for review
        today = date.today().isoformat()
        due_vocab = sum(1 for w in lang["vocabulary"] if w.get("next_review", today) <= today)
        due_phrases = sum(1 for p in lang["phrases"] if p.get("next_review", today) <= today)
        total_due = due_vocab + due_phrases

        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("key", style="dim", min_width=14)
        table.add_column("value")

        table.add_row("Priority", f"[{p_color}]{lang['priority']}[/]")
        table.add_row("Level", lang.get("level", "beginner"))
        table.add_row("Started", lang.get("started", "?"))
        table.add_row("Sessions", str(lang.get("total_sessions", 0)))
        table.add_row("Streak", f"{lang.get('streak', 0)} days")
        table.add_row("Daily Goal", f"{lang.get('daily_goal_minutes', 0)} min")
        table.add_row("", "")
        table.add_row("Vocabulary", f"{mastered_vocab}/{total_vocab} mastered")
        table.add_row("Phrases", f"{mastered_phrases}/{total_phrases} mastered")
        table.add_row("Due for Review", f"[bold {'yellow' if total_due > 0 else 'green'}]{total_due} items[/]")

        console.print(Panel(
            table,
            title=f"[bold]{lang['name']}[/] [dim]({lang['code']})[/]",
            border_style="cyan",
            padding=(0, 1)
        ))

    console.print(f"\n[dim]{len(data['languages'])} languages tracked[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ADD VOCABULARY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def cmd_add(lang_code, word, translation, transliteration=""):
    """Manually add a vocabulary word."""
    data = load_data()
    lang = get_language(data, lang_code)
    today = date.today().isoformat()

    # Check for duplicates
    for existing in lang["vocabulary"]:
        if existing["word"] == word:
            console.print(f"[yellow]'{word}' already exists in {lang['name']} vocabulary.[/]")
            return

    entry = {
        "word": word,
        "transliteration": transliteration,
        "translation": translation,
        "learned": today,
        "correct": 0,
        "incorrect": 0,
        "next_review": today,
        "interval_days": 1,
    }

    lang["vocabulary"].append(entry)
    save_data(data)
    console.print(f"[bold green]Added:[/] {word} = {translation} [dim]to {lang['name']}[/]")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(description="Super Tobi Language Learning System")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--lesson", metavar="LANG", help="New lesson (5 words + 2 phrases with AI tips)")
    group.add_argument("--quiz", metavar="LANG", help="Spaced repetition quiz")
    group.add_argument("--practice", metavar="LANG", help="AI conversation practice")
    group.add_argument("--progress", action="store_true", help="Show progress across all languages")
    group.add_argument("--add", nargs="+", metavar="ARG", help="Add vocabulary: <lang> <word> <translation> [transliteration]")

    args = parser.parse_args()

    if args.lesson:
        cmd_lesson(args.lesson)
    elif args.quiz:
        cmd_quiz(args.quiz)
    elif args.practice:
        cmd_practice(args.practice)
    elif args.progress:
        cmd_progress()
    elif args.add:
        if len(args.add) < 3:
            console.print("[red]Usage:[/] --add <lang> <word> <translation> [transliteration]")
            sys.exit(1)
        lang_code = args.add[0]
        word = args.add[1]
        translation = args.add[2]
        translit = args.add[3] if len(args.add) > 3 else ""
        cmd_add(lang_code, word, translation, translit)


if __name__ == "__main__":
    main()
