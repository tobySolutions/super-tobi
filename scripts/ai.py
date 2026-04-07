#!/usr/bin/env python3
"""
Super Tobi — AI Engine
Central AI module that uses Claude Code CLI for all AI-powered features.
No separate API key needed — piggybacks on your existing Claude Code setup.

Usage:
    from ai import ask_claude
    response = ask_claude("Write a reply to this message as Tobiloba: ...")
"""

import subprocess
import os

CLAUDE_PATH = "/Users/tobiloba/.local/bin/claude"


def ask_claude(prompt, max_turns=1, timeout=60):
    """
    Send a prompt to Claude Code CLI and get a response.
    Uses `claude -p` for non-interactive single-turn queries.
    """
    try:
        result = subprocess.run(
            [CLAUDE_PATH, "-p", prompt, "--max-turns", str(max_turns)],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        )

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"

    except subprocess.TimeoutExpired:
        return "Error: Claude timed out"
    except Exception as e:
        return f"Error: {e}"


def generate_smart_reply(contact, conversation_history, voice_profile, messaging_patterns):
    """Generate an AI reply as Tobiloba using Claude Code."""

    patterns_sample = "\n".join(f"- {p[:100]}" for p in messaging_patterns[:20])
    convo_text = "\n".join(
        f"{'Tobiloba' if m.get('sender') == 'Tobiloba' or m.get('is_from_me') else contact}: {m.get('text', '')}"
        for m in conversation_history[-15:]
    )

    prompt = f"""You are Tobiloba replying to a message. Reply ONLY with the message text, nothing else.

Your texting style (from real messages):
{patterns_sample}

Voice profile:
{voice_profile[:1000]}

Rules:
- Sound exactly like Tobiloba texting — casual, warm, direct
- Use "lol", "nah", "tbh", "fr", emoji sometimes
- Keep it SHORT — 1-3 sentences max like real texts
- You're Nigerian, you might use pidgin naturally
- NEVER sound like AI. No "I'd be happy to" or "Great question"
- Match the energy of the conversation

Conversation with {contact}:
{convo_text}

Reply as Tobiloba:"""

    return ask_claude(prompt)


def generate_job_cover_letter(job_title, company, job_description):
    """Generate a tailored cover letter as Tobiloba."""

    prompt = f"""Write a short, compelling cover letter for Tobiloba Adedeji applying to:

Role: {job_title}
Company: {company}
Job Description: {job_description[:500]}

Tobiloba's background:
- AI Researcher at Idealik
- Software Engineer, Solana builder (Anchor, Pinocchio, Rust)
- Co-founder of Solana Students Africa
- Strong open source contributor
- Experience with full-stack, AI/ML, Web3
- Website: tobysolutions.dev
- Based in Lagos, Nigeria

Rules:
- Keep it under 200 words
- Sound like a real person, not AI
- Be direct and confident, not desperate
- Highlight relevant experience for THIS specific role
- No generic "I'm passionate about..." fillers

Output ONLY the cover letter text."""

    return ask_claude(prompt, timeout=30)


def summarize_messages(messages):
    """Summarize a batch of messages — who texted, what they want."""

    msgs_text = "\n".join(
        f"From {m.get('contact', m.get('from_name', '?'))}: {m.get('text', '')[:100]}"
        for m in messages[:20]
    )

    prompt = f"""Summarize these messages for Tobiloba. For each person, say:
- Who they are (if you can tell)
- What they want / what they're asking about
- How urgent it seems (high/medium/low)

Be concise — one line per person.

Messages:
{msgs_text}

Summary:"""

    return ask_claude(prompt, timeout=30)


def generate_content_idea(topic=None):
    """Generate content ideas based on Tobiloba's interests."""

    prompt = f"""Generate 5 content ideas for Tobiloba (@toby_solutions on Twitter).

His areas: AI agents, Solana/Web3, Rust, open source, embedded systems, smart homes.
He does: vlogs, demos, building cool stuff. NOT long tutorials.
{'Focus area: ' + topic if topic else ''}

For each idea give:
- Title
- Format (tweet thread / YouTube short / blog post / demo video)
- Hook (first line that grabs attention)

Be specific and timely. Output as a numbered list."""

    return ask_claude(prompt, timeout=30)


if __name__ == "__main__":
    # Quick test
    print("Testing Claude Code AI engine...")
    response = ask_claude("Say 'Super Tobi is alive!' and nothing else.")
    print(f"Response: {response}")
