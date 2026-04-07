#!/usr/bin/env python3
"""
Super Tobi — Proof Writer
Integrates the /write auto-writer pipeline with the Proof editor.
Creates drafts in Proof, applies voice-calibrated edits as agent suggestions,
and provides shareable links for review.
"""

import json
import os
import re
import subprocess
import sys
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VOICE_DIR = BASE_DIR / "data" / "writing" / "voice"
DRAFTS_DIR = BASE_DIR / "data" / "writing" / "drafts"
RESEARCH_DIR = BASE_DIR / "data" / "writing" / "research"
PROOF_URL = os.environ.get("PROOF_URL", "http://localhost:4000")
CLAUDE_PATH = "/Users/tobiloba/.local/bin/claude"

# Store active document sessions
SESSIONS_FILE = BASE_DIR / "data" / "writing" / "proof_sessions.json"


def load_sessions():
    try:
        with open(SESSIONS_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_sessions(sessions):
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def get_voice_profile():
    """Load the voice analysis for calibration."""
    voice_file = VOICE_DIR / "voice_analysis.md"
    if voice_file.exists():
        return voice_file.read_text()
    return ""


def get_voice_samples(n=3):
    """Get a few recent voice samples for tone matching."""
    samples = []
    for f in sorted(VOICE_DIR.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.name == "voice_analysis.md" or not f.suffix == ".md":
            continue
        content = f.read_text()
        # Take first 500 chars as a sample
        samples.append({"file": f.name, "excerpt": content[:500]})
        if len(samples) >= n:
            break
    return samples


def ask_claude(prompt, timeout=120):
    """Send a prompt to Claude CLI."""
    try:
        result = subprocess.run(
            [CLAUDE_PATH, "-p", prompt, "--max-turns", "3"],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(BASE_DIR),
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def proof_api(method, path, data=None, token=None):
    """Make a Proof API call."""
    url = f"{PROOF_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    if method == "GET":
        r = requests.get(url, headers=headers, timeout=15)
    elif method == "POST":
        r = requests.post(url, headers=headers, json=data, timeout=15)
    elif method == "PUT":
        r = requests.put(url, headers=headers, json=data, timeout=15)
    else:
        raise ValueError(f"Unknown method: {method}")

    if r.status_code >= 400:
        raise Exception(f"Proof API error {r.status_code}: {r.text[:200]}")
    return r.json() if r.text else {}


# ─── Pipeline Steps ──────────────────────────────────

def parse_intent(prompt):
    """Parse the writing prompt into structured intent."""
    result = ask_claude(
        f"Parse this writing prompt into JSON with keys: type (article/blog/essay/thread/email/proposal), "
        f"audience (developers/general/recruiters/conference), tone (technical/casual/narrative/formal), "
        f"length (short/medium/long), topic (main topic), title (suggested title). "
        f"Prompt: {prompt}\n\nReturn ONLY valid JSON, no markdown.",
        timeout=30,
    )
    try:
        # Extract JSON from response
        if "```" in result:
            result = re.search(r'```(?:json)?\s*(.*?)\s*```', result, re.DOTALL).group(1)
        return json.loads(result)
    except Exception:
        return {
            "type": "article",
            "audience": "developers",
            "tone": "technical",
            "length": "medium",
            "topic": prompt,
            "title": prompt[:60],
        }


def research(topic):
    """Research phase — gather material."""
    # Check existing research
    existing = []
    for f in RESEARCH_DIR.iterdir() if RESEARCH_DIR.exists() else []:
        if topic.lower().replace(" ", "") in f.name.lower().replace(" ", ""):
            existing.append(f.read_text()[:500])

    # Web research via Claude
    research_result = ask_claude(
        f"Research this topic briefly for a technical blog post: {topic}\n"
        f"Find 3-5 key points, recent developments, and any relevant data/stats.\n"
        f"Return concise bullet points only.",
        timeout=60,
    )
    return {"existing": existing, "fresh": research_result}


def generate_draft(intent, research_data, voice_profile, samples):
    """Generate the initial draft in Tobiloba's voice."""
    sample_text = "\n\n---\n\n".join(
        f"SAMPLE ({s['file']}):\n{s['excerpt']}" for s in samples
    )

    prompt = f"""You are writing a {intent.get('type', 'blog post')} for Tobiloba Adedeji.

TOPIC: {intent.get('topic', '')}
TITLE: {intent.get('title', '')}
AUDIENCE: {intent.get('audience', 'developers')}
TONE: {intent.get('tone', 'technical')}
LENGTH: {intent.get('length', 'medium')}

VOICE PROFILE:
{voice_profile[:2000]}

RECENT WRITING SAMPLES:
{sample_text[:3000]}

RESEARCH:
{research_data.get('fresh', '')}

CRITICAL RULES:
- Write in Tobiloba's Phase 2 voice: confident, contrarian, thesis-driven
- Use short punchy sentences alternating with longer analytical ones
- Include specific numbers and data, not vague claims
- No AI-sounding phrases: "delve", "landscape", "In conclusion", "It's worth noting"
- No corporate jargon
- Use CS/systems terminology naturally (mutex, kernel, daemon, event sourcing)
- End with something concrete — what to build, what to do next
- Section headers should do rhetorical work, not just organization

Write the FULL {intent.get('type', 'article')}. Output ONLY the markdown content."""

    return ask_claude(prompt, timeout=180)


def create_proof_doc(title, markdown):
    """Create a new Proof document and return session info."""
    data = proof_api("POST", "/documents", {
        "title": title,
        "markdown": markdown,
        "ownerId": "agent:supertobi",
    })
    return {
        "slug": data["slug"],
        "docId": data.get("docId", ""),
        "shareUrl": data.get("shareUrl", ""),
        "tokenUrl": data.get("tokenUrl", ""),
        "ownerSecret": data.get("ownerSecret", ""),
        "accessToken": data.get("accessToken", ""),
    }


def set_agent_presence(slug, token, status, summary):
    """Set Super Tobi's presence in the document."""
    try:
        proof_api("POST", f"/documents/{slug}/bridge/presence", {
            "agentId": "agent:supertobi",
            "status": status,
            "summary": summary,
            "name": "Super Tobi",
            "color": "#266854",
        }, token=token)
    except Exception:
        pass


def add_voice_review(slug, token, draft, voice_profile):
    """Review the draft for voice consistency and add comments."""
    review = ask_claude(
        f"You are Tobiloba's writing editor. Review this draft against his voice profile.\n\n"
        f"VOICE PROFILE:\n{voice_profile[:1500]}\n\n"
        f"DRAFT:\n{draft[:3000]}\n\n"
        f"Find 3-5 specific places where the writing doesn't match Tobiloba's voice. "
        f"For each, provide:\n"
        f"1. The exact quote from the draft (5-15 words)\n"
        f"2. What's wrong with it\n"
        f"3. A suggested rewrite\n\n"
        f"Return as JSON array of objects with keys: quote, issue, suggestion",
        timeout=60,
    )

    try:
        if "```" in review:
            review = re.search(r'```(?:json)?\s*(.*?)\s*```', review, re.DOTALL).group(1)
        comments = json.loads(review)
    except Exception:
        comments = []

    for comment in comments[:5]:
        try:
            proof_api("POST", f"/documents/{slug}/bridge/comments", {
                "by": "agent:supertobi",
                "quote": comment.get("quote", ""),
                "text": f"**Voice check:** {comment.get('issue', '')}\n\n**Suggestion:** {comment.get('suggestion', '')}",
            }, token=token)
        except Exception:
            continue

    return comments


def add_suggestions(slug, token, draft, voice_profile):
    """Add inline edit suggestions via Proof bridge."""
    edits = ask_claude(
        f"You are Tobiloba's writing editor. Suggest 3 concrete inline edits to improve this draft.\n\n"
        f"VOICE PROFILE:\n{voice_profile[:1000]}\n\n"
        f"DRAFT:\n{draft[:3000]}\n\n"
        f"For each edit, provide:\n"
        f"1. The exact original text to replace (10-30 words)\n"
        f"2. The replacement text\n\n"
        f"Return as JSON array of objects with keys: original, replacement",
        timeout=60,
    )

    try:
        if "```" in edits:
            edits = re.search(r'```(?:json)?\s*(.*?)\s*```', edits, re.DOTALL).group(1)
        suggestions = json.loads(edits)
    except Exception:
        suggestions = []

    for suggestion in suggestions[:5]:
        try:
            proof_api("POST", f"/documents/{slug}/bridge/suggestions", {
                "by": "agent:supertobi",
                "quote": suggestion.get("original", ""),
                "replacement": suggestion.get("replacement", ""),
            }, token=token)
        except Exception:
            continue

    return suggestions


# ─── Main Pipeline ────────────────────────────────────

def write(prompt, skip_outline=False):
    """Full auto-writer pipeline with Proof integration."""
    print("\n  SUPER TOBI AUTO-WRITER + PROOF EDITOR")
    print("  " + "━" * 45)

    # Step 1: Parse intent
    print("\n  [1/7] Parsing intent...")
    intent = parse_intent(prompt)
    print(f"        Type: {intent.get('type')} | Audience: {intent.get('audience')}")
    print(f"        Title: {intent.get('title')}")

    # Step 2: Research
    print("\n  [2/7] Researching...")
    research_data = research(intent.get("topic", prompt))
    print(f"        Found: {len(research_data.get('existing', []))} existing + fresh research")

    # Step 3: Voice calibration
    print("\n  [3/7] Calibrating voice...")
    voice_profile = get_voice_profile()
    samples = get_voice_samples(3)
    print(f"        Loaded profile + {len(samples)} samples")

    # Step 4: Generate draft
    print("\n  [4/7] Generating draft...")
    draft = generate_draft(intent, research_data, voice_profile, samples)
    print(f"        Draft: {len(draft)} chars, {len(draft.split())} words")

    # Step 5: Create Proof document
    print("\n  [5/7] Creating Proof document...")
    try:
        session = create_proof_doc(intent.get("title", "Untitled"), draft)
        print(f"        Slug: {session['slug']}")
        print(f"        URL:  {session['shareUrl']}")
    except Exception as e:
        print(f"        Proof unavailable ({e}), saving locally instead")
        slug = intent.get("title", "draft").lower().replace(" ", "_")[:30]
        draft_path = DRAFTS_DIR / f"{slug}_v1.md"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        draft_path.write_text(draft)
        print(f"        Saved to: {draft_path}")
        return {"draft": draft, "path": str(draft_path)}

    # Step 6: Agent review (voice + suggestions)
    print("\n  [6/7] Running voice review...")
    set_agent_presence(session["slug"], session["accessToken"], "reviewing", "Checking voice consistency")
    comments = add_voice_review(session["slug"], session["accessToken"], draft, voice_profile)
    print(f"        Added {len(comments)} voice comments")

    print("\n  [7/7] Adding edit suggestions...")
    set_agent_presence(session["slug"], session["accessToken"], "editing", "Suggesting improvements")
    suggestions = add_suggestions(session["slug"], session["accessToken"], draft, voice_profile)
    print(f"        Added {len(suggestions)} inline suggestions")

    set_agent_presence(session["slug"], session["accessToken"], "idle", "Waiting for your review")

    # Save session
    sessions = load_sessions()
    sessions[session["slug"]] = {
        "title": intent.get("title", "Untitled"),
        "type": intent.get("type", "article"),
        "slug": session["slug"],
        "shareUrl": session["shareUrl"],
        "tokenUrl": session["tokenUrl"],
        "ownerSecret": session["ownerSecret"],
        "accessToken": session["accessToken"],
        "created": __import__("datetime").datetime.now().isoformat(),
        "status": "draft",
    }
    save_sessions(sessions)

    # Also save local copy
    slug = intent.get("title", "draft").lower().replace(" ", "_")[:30]
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    (DRAFTS_DIR / f"{slug}_v1.md").write_text(draft)

    # Output
    print("\n  " + "━" * 45)
    print(f"  DRAFT READY")
    print(f"  Open in Proof: {session['shareUrl']}")
    print(f"  Token URL:     {session['tokenUrl']}")
    print(f"  {len(comments)} voice comments + {len(suggestions)} edit suggestions waiting")
    print(f"  Local backup:  data/writing/drafts/{slug}_v1.md")
    print("  " + "━" * 45)

    return {
        "draft": draft,
        "slug": session["slug"],
        "shareUrl": session["shareUrl"],
        "tokenUrl": session["tokenUrl"],
        "comments": len(comments),
        "suggestions": len(suggestions),
    }


def list_docs():
    """List all Proof writing sessions."""
    sessions = load_sessions()
    if not sessions:
        print("  No active writing sessions.")
        return

    print("\n  PROOF DOCUMENTS")
    print("  " + "━" * 45)
    for slug, s in sessions.items():
        print(f"  [{s.get('status', '?')}] {s.get('title', '?')}")
        print(f"         {s.get('shareUrl', '?')}")
    print()


def publish(slug):
    """Export a Proof document for publishing."""
    sessions = load_sessions()
    session = sessions.get(slug)
    if not session:
        print(f"  No session found for slug: {slug}")
        return

    # Get current state from Proof
    try:
        state = proof_api("GET", f"/documents/{slug}/state", token=session.get("accessToken"))
        markdown = state.get("markdown", "")
        print(f"  Exported {len(markdown)} chars from Proof")

        # Save final version
        title_slug = session.get("title", "draft").lower().replace(" ", "_")[:30]
        final_path = DRAFTS_DIR / f"{title_slug}_final.md"
        final_path.write_text(markdown)
        print(f"  Saved to: {final_path}")

        # Update session
        sessions[slug]["status"] = "published"
        save_sessions(sessions)

        return markdown
    except Exception as e:
        print(f"  Error exporting: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  proof_writer.py write <prompt>   — Write a new piece")
        print("  proof_writer.py list             — List all documents")
        print("  proof_writer.py publish <slug>   — Export for publishing")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "write":
        prompt = " ".join(sys.argv[2:])
        if not prompt:
            print("Error: provide a writing prompt")
            sys.exit(1)
        write(prompt)
    elif cmd == "list":
        list_docs()
    elif cmd == "publish":
        if len(sys.argv) < 3:
            print("Error: provide a document slug")
            sys.exit(1)
        publish(sys.argv[2])
    else:
        print(f"Unknown command: {cmd}")
