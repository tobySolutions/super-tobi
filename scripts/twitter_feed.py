#!/usr/bin/env python3
"""
Super Tobi — Twitter Feed Puller
Uses the twitterapi.io API key to pull:
- Mentions of @toby_solutions
- Timeline / home feed
- Interesting topics in AI, Solana, open source, embedded systems
- DMs (if API supports it)
"""

import os
import sys
import json
import requests
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
DATA_DIR = os.path.join(BASE_DIR, "data")
TWITTER_CACHE = os.path.join(DATA_DIR, "content", "twitter_feed.json")

TWITTER_HANDLE = "toby_solutions"

# Topics Tobiloba cares about
INTEREST_TOPICS = [
    # Tech & Career
    "AI agents",
    "AI research breakthroughs",
    "Solana development",
    "Claude API",
    "Rust programming",
    "open source",
    "developer tools",
    "MLOps",
    # Startup & VC
    "YCombinator startups",
    "VC funding rounds",
    "startup fundraising",
    "a]16z crypto",
    # Music & Culture
    "Afrobeats new music",
    "Burna Boy",
    "Wizkid",
    "Davido",
    # Movies & Entertainment
    "new movies 2026",
    "movie releases",
    # Blockchain
    "Solana ecosystem",
    "Anchor Solana",
    "crypto trading",
    # Finance
    "FOREX trading",
]


def get_api_key():
    env_file = os.path.join(CONFIG_DIR, "api_keys.env")
    with open(env_file) as f:
        for line in f:
            if line.startswith("TWITTER_API_KEY=") and "#" not in line:
                return line.strip().split("=", 1)[1]
    return None


def twitter_request(endpoint, params=None):
    """Make a request to twitterapi.io."""
    api_key = get_api_key()
    if not api_key:
        print("❌ No Twitter API key found")
        return None

    url = f"https://api.twitterapi.io/twitter/{endpoint}"
    headers = {"X-API-Key": api_key}

    try:
        import time
        time.sleep(1)  # Rate limit: 1 req per 5s on free tier
        response = requests.get(url, headers=headers, params=params or {}, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"  API error {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  Request failed: {e}")
        return None


def get_mentions():
    """Get recent mentions of @toby_solutions."""
    result = twitter_request("user/mentions", {
        "userName": TWITTER_HANDLE,
    })
    if not result:
        return []

    tweets = result.get("tweets", [])
    return [{
        "id": t.get("id"),
        "author": t.get("author", {}).get("userName", t.get("author", "unknown")),
        "author_name": t.get("author", {}).get("name", "") if isinstance(t.get("author"), dict) else "",
        "text": t.get("text", ""),
        "likes": t.get("likeCount", 0),
        "retweets": t.get("retweetCount", 0),
        "date": t.get("createdAt", ""),
        "url": t.get("url", ""),
        "type": "mention",
    } for t in tweets]


def get_user_tweets():
    """Get Tobiloba's recent tweets."""
    result = twitter_request("user/last_tweets", {
        "userName": TWITTER_HANDLE,
    })
    if not result:
        return []

    tweets = result.get("tweets", [])
    if not tweets:
        # Fallback: use advanced_search with from: operator
        result = twitter_request("tweet/advanced_search", {
            "query": f"from:{TWITTER_HANDLE}",
            "queryType": "Latest",
        })
        if result:
            tweets = result.get("tweets", [])

    return [{
        "id": t.get("id"),
        "text": t.get("text", ""),
        "likes": t.get("likeCount", 0),
        "retweets": t.get("retweetCount", 0),
        "replies": t.get("replyCount", 0),
        "views": t.get("viewCount", 0),
        "date": t.get("createdAt", ""),
        "url": t.get("url", ""),
        "type": "own_tweet",
    } for t in tweets]


def search_topics():
    """Search for interesting content in Tobiloba's areas of interest."""
    all_results = []

    import time
    for topic in INTEREST_TOPICS[:5]:  # Pull top 5 topics per run (keep under timeout)
        time.sleep(2)  # Respect rate limit
        result = twitter_request("tweet/advanced_search", {
            "query": topic,
            "queryType": "Top",
        })
        if result:
            tweets = result.get("tweets", [])[:3]  # Top 3 per topic
            for t in tweets:
                author = t.get("author", {})
                if isinstance(author, dict):
                    author_name = author.get("userName", "unknown")
                    author_display = author.get("name", "")
                else:
                    author_name = str(author)
                    author_display = ""

                all_results.append({
                    "id": t.get("id"),
                    "author": author_name,
                    "author_name": author_display,
                    "text": t.get("text", ""),
                    "likes": t.get("likeCount", 0),
                    "retweets": t.get("retweetCount", 0),
                    "date": t.get("createdAt", ""),
                    "url": t.get("url", ""),
                    "topic": topic,
                    "type": "topic",
                })

    return all_results


def format_feed(mentions, own_tweets, topics):
    """Format the feed nicely."""
    lines = []
    lines.append("╔══════════════════════════════════════════════╗")
    lines.append("║        🐦 SUPER TOBI — TWITTER FEED          ║")
    lines.append("╠══════════════════════════════════════════════╣")

    if mentions:
        lines.append("")
        lines.append("  📢 MENTIONS")
        lines.append("  " + "─" * 40)
        for m in mentions[:5]:
            lines.append(f"  @{m['author']}: {m['text'][:80]}")
            lines.append(f"  ❤️ {m['likes']}  🔄 {m['retweets']}  🔗 {m['url']}")
            lines.append("")

    if own_tweets:
        lines.append("  📊 YOUR RECENT TWEETS (performance)")
        lines.append("  " + "─" * 40)
        for t in own_tweets[:5]:
            lines.append(f"  {t['text'][:80]}")
            lines.append(f"  ❤️ {t['likes']}  🔄 {t['retweets']}  💬 {t['replies']}  👁️ {t['views']}")
            lines.append("")

    if topics:
        lines.append("  🔥 TRENDING IN YOUR INTERESTS")
        lines.append("  " + "─" * 40)
        current_topic = ""
        for t in topics:
            if t['topic'] != current_topic:
                current_topic = t['topic']
                lines.append(f"  [{current_topic}]")
            lines.append(f"    @{t['author']}: {t['text'][:70]}")
            lines.append(f"    ❤️ {t['likes']}  🔄 {t['retweets']}")
            lines.append("")

    lines.append("╚══════════════════════════════════════════════╝")
    return "\n".join(lines)


def pull_full_feed():
    """Pull everything and return formatted feed."""
    print("Pulling Twitter feed...")

    mentions = get_mentions()
    print(f"  📢 {len(mentions)} mentions")

    own_tweets = get_user_tweets()
    print(f"  📊 {len(own_tweets)} own tweets")

    topics = search_topics()
    print(f"  🔥 {len(topics)} topic tweets")

    # Cache results
    cache = {
        "pulled_at": datetime.now().isoformat(),
        "mentions": mentions,
        "own_tweets": own_tweets,
        "topics": topics,
    }
    with open(TWITTER_CACHE, "w") as f:
        json.dump(cache, f, indent=2)

    return mentions, own_tweets, topics


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Super Tobi Twitter Feed")
    parser.add_argument("--mentions", action="store_true", help="Show mentions only")
    parser.add_argument("--topics", action="store_true", help="Show trending topics only")
    parser.add_argument("--my-tweets", action="store_true", help="Show your tweet performance")
    parser.add_argument("--full", action="store_true", help="Full feed pull")
    parser.add_argument("--cached", action="store_true", help="Show cached feed")

    args = parser.parse_args()

    if args.cached:
        if os.path.exists(TWITTER_CACHE):
            with open(TWITTER_CACHE) as f:
                cache = json.load(f)
            print(format_feed(cache.get("mentions", []), cache.get("own_tweets", []), cache.get("topics", [])))
        else:
            print("No cached feed. Run with --full first.")
        return

    if args.mentions:
        mentions = get_mentions()
        print(format_feed(mentions, [], []))
    elif args.topics:
        topics = search_topics()
        print(format_feed([], [], topics))
    elif args.my_tweets:
        tweets = get_user_tweets()
        print(format_feed([], tweets, []))
    else:
        mentions, own_tweets, topics = pull_full_feed()
        print(format_feed(mentions, own_tweets, topics))


if __name__ == "__main__":
    main()
