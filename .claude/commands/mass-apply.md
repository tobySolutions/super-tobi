# /mass-apply — Mass Job Application System

You are Super Tobi's mass application engine. Apply to as many matching jobs as possible.

## Process

1. **Search all boards** using WebSearch for current openings matching Tobiloba's profile:
   - Search queries: "AI engineer remote", "Solana developer remote", "Rust developer remote", "fullstack engineer remote web3", "ML engineer remote", "blockchain engineer remote", "DevRel engineer remote"
   - Boards: Wellfound, Indeed, LinkedIn, Arc.dev, Built In, Web3Career, RemoteOK, CryptoJobsList, Solana Jobs, RustJobs.dev, Otta, Glassdoor, AngelList, Working Nomads

2. **For each job found:**
   - Check if already in applications.json (skip duplicates)
   - Score it (must be 40%+ to apply)
   - Find the direct application link

3. **Apply via Playwright browser:**
   - Navigate to application page
   - Fill ALL fields with Tobiloba's details:
     - Name: Tobiloba Adedeji
     - Email: adedejitobiloba7@gmail.com
     - Phone: +2348029603888
     - Location: Lagos, Nigeria
     - Current company: Idyllic Labs
     - LinkedIn: https://www.linkedin.com/in/tobiloba-adedeji
     - Twitter: https://twitter.com/toby_solutions
     - GitHub: https://github.com/tobySolutions
     - Portfolio: https://tobysolutions.dev
   - Generate a tailored cover letter using Claude CLI
   - Upload resume: data/career/resume/Tobiloba_Adedeji_Resume.pdf
   - If Greenhouse verification code needed, auto-grab from Gmail
   - Submit

4. **Log everything** to applications.json with status "applied"

5. **Skip and move on** if:
   - Site requires login (note for future: create account)
   - Cloudflare blocks
   - Form is too complex to fill programmatically
   - Don't waste time — skip and hit the next one

6. **Notify via Telegram** with summary of how many applied

## Goal: Apply to as many qualifying jobs as possible in one run. Speed over perfection.
