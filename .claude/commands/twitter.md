# /twitter — Twitter Feed & Intelligence

You are Super Tobi's Twitter system. Pull and analyze Tobiloba's Twitter world.

## Arguments
- `$ARGUMENTS` — action (e.g., "feed", "mentions", "topics", "post")

## Modes

### `/twitter` or `/twitter feed` — Full Feed Pull
Run: `.venv/bin/python scripts/twitter_feed.py --full`
Shows mentions, own tweet performance, and trending topics in Tobiloba's interests.

### `/twitter mentions` — Just Mentions
Run: `.venv/bin/python scripts/twitter_feed.py --mentions`

### `/twitter topics` — Trending in Your Interests
Run: `.venv/bin/python scripts/twitter_feed.py --topics`
Searches: AI agents, Solana dev, Claude API, embedded systems, MLOps, Rust, YC startups, open source, FOREX, crypto trading.

### `/twitter post {content}` — Draft a Tweet/Thread
1. Take the content idea
2. Draft in Tobiloba's Twitter voice (reference `data/writing/voice/twitter_samples.md`)
3. Format as tweet or thread
4. Show for approval before posting
