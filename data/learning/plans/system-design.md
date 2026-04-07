# System Design & Databases — Learning Plan

**Owner:** Tobiloba
**Priority:** #1 NOW
**Duration:** 8 weeks (2026-03-20 to 2026-05-15)
**Daily commitment:** 1.5–2 hours
**Goal:** Go from "can build basic backends" to "can design, defend, and ship complex systems"

---

## Phase 1: Foundations (Week 1–2)

**Dates:** 2026-03-20 to 2026-04-03

### What You're Learning
- How the internet actually works at scale (DNS, TCP/IP, HTTP)
- Load balancing strategies (round robin, least connections, consistent hashing)
- Caching layers (browser, CDN, application, database)
- CDNs and edge networks
- Forward vs reverse proxies
- Horizontal vs vertical scaling
- CAP theorem (just the concept — you'll go deeper later)

### Daily Schedule

| Day | Topic | Task |
|-----|-------|------|
| 1 | DNS + How the web works | Watch "How DNS Works" by ByteByteGo. Read the Cloudflare Learning Center DNS article. Draw the full request lifecycle from browser to server. |
| 2 | HTTP deep dive | Read MDN HTTP overview. Understand methods, status codes, headers, keep-alive, HTTP/2 vs HTTP/3. |
| 3 | Load Balancing | Watch ByteByteGo "Load Balancing" video. Read NGINX load balancing docs. Write notes on when to use L4 vs L7 load balancing. |
| 4 | Caching — Theory | Watch "Caching Strategies" by Hussein Nasser. Study cache-aside, write-through, write-behind, read-through patterns. |
| 5 | Caching — Practice | Set up Redis locally. Build a simple Node/Python API that caches DB reads in Redis. Measure the latency difference. |
| 6 | CDNs + Proxies | Read Cloudflare "What is a CDN?" article. Watch ByteByteGo "Proxy vs Reverse Proxy." Diagram a system that uses both a CDN and reverse proxy. |
| 7 | Review + Quiz | Re-draw all diagrams from memory. Explain each concept in your own words (write a Twitter thread draft if it clicks). |
| 8 | Scaling concepts | Watch "Vertical vs Horizontal Scaling" by Gaurav Sen. Read about stateless vs stateful services. |
| 9 | CAP Theorem | Watch "CAP Theorem" by Tech Dummies. Read Martin Kleppmann's blog post on CAP. Write a one-page summary of tradeoffs. |
| 10 | Consistent Hashing | Watch Gaurav Sen "Consistent Hashing" video. Implement a basic consistent hashing ring in Python or JS. |
| 11 | Rate Limiting | Read Stripe's rate limiting blog post. Implement token bucket algorithm locally. |
| 12 | API Design Basics | Read Microsoft REST API guidelines (free). Design an API for a simple social app — define endpoints, status codes, pagination. |
| 13 | Networking recap | Read "High Performance Browser Networking" Chapter 1 (free online). Understand TCP handshake, TLS, connection pooling. |
| 14 | Phase 1 Capstone | Draw a complete architecture diagram for a basic web app with: DNS, CDN, load balancer, app servers, cache layer, database. Write a 1-page explanation of each component's role. |

### Free Resources
- **ByteByteGo YouTube channel** — https://www.youtube.com/@ByteByteGo (short, visual explanations of every concept)
- **Gaurav Sen YouTube channel** — https://www.youtube.com/@gaborSen (system design fundamentals, excellent for intuition)
- **Hussein Nasser YouTube channel** — https://www.youtube.com/@haborNasser (deep backend/networking topics)
- **Cloudflare Learning Center** — https://www.cloudflare.com/learning/ (clear articles on DNS, CDN, DDoS, etc.)
- **"High Performance Browser Networking" by Ilya Grigorik** — https://hpbn.co/ (free online book)
- **System Design Primer (GitHub)** — https://github.com/donnemartin/system-design-primer (the single best free reference)
- **MDN Web Docs** — https://developer.mozilla.org/en-US/docs/Web/HTTP (HTTP reference)

### Checkpoint
- [ ] Can explain the full lifecycle of a web request (DNS → CDN → LB → App → Cache → DB)
- [ ] Can explain 3 caching strategies and when to use each
- [ ] Can explain horizontal vs vertical scaling with real examples
- [ ] Built a working Redis cache demo
- [ ] Can explain CAP theorem in plain language

---

## Phase 2: Databases Deep Dive (Week 3–4)

**Dates:** 2026-04-03 to 2026-04-17

### What You're Learning
- SQL fundamentals at depth (joins, subqueries, CTEs, window functions)
- Database indexing — how B-trees work, when to index, composite indexes
- Query optimization — reading EXPLAIN plans, spotting N+1 queries
- NoSQL categories: document (MongoDB), key-value (Redis), wide-column (Cassandra), graph (Neo4j)
- When to use SQL vs NoSQL (not a religion — it's about access patterns)
- Sharding strategies (range, hash, directory)
- Replication (leader-follower, leader-leader, quorum)
- ACID vs BASE

### Daily Schedule

| Day | Topic | Task |
|-----|-------|------|
| 1 | SQL Refresher | Complete SQLBolt (all lessons). Focus on JOINs and aggregations. |
| 2 | Advanced SQL | Study CTEs, window functions (ROW_NUMBER, RANK, PARTITION BY). Use PostgreSQL Exercises site. |
| 3 | Indexing — Theory | Watch "Database Indexing" by Hussein Nasser. Read Use The Index, Luke! chapters 1–3. Understand B-tree structure. |
| 4 | Indexing — Practice | Create a PostgreSQL table with 1M rows (use generate_series). Run queries with and without indexes. Compare EXPLAIN ANALYZE output. |
| 5 | Query Optimization | Read "How to read EXPLAIN plans" (pgMustard blog). Take 3 slow queries and optimize them using indexes and query rewriting. |
| 6 | N+1 Problem | Understand the N+1 query problem. Write code that demonstrates it, then fix it with eager loading / joins. |
| 7 | ACID + Transactions | Watch "ACID Explained" by Hussein Nasser. Write a bank transfer scenario that demonstrates isolation levels (READ COMMITTED vs SERIALIZABLE). |
| 8 | NoSQL — Document DBs | Read MongoDB University free course intro. Build a simple app with MongoDB. Understand embedding vs referencing. |
| 9 | NoSQL — Key-Value & Wide-Column | Study Redis data structures beyond strings (sorted sets, hashes, streams). Read Cassandra's data model overview. |
| 10 | SQL vs NoSQL Decision Framework | Create a decision matrix: access patterns, consistency needs, scale requirements, team expertise. Write it up as a reference card. |
| 11 | Sharding | Watch ByteByteGo "Database Sharding" video. Study range-based vs hash-based sharding. Diagram shard key selection for an e-commerce app. |
| 12 | Replication | Watch "Master-Slave vs Master-Master" by Hussein Nasser. Understand replication lag and its consequences. Diagram leader-follower setup. |
| 13 | Schema Design Project | Design a complete database schema for a real project: a Solana NFT marketplace. Define tables, relationships, indexes, and justify SQL vs NoSQL for each data type. |
| 14 | Phase 2 Capstone | Write a 2-page document: "Database Architecture for [your project]." Include schema diagram, index strategy, sharding plan, replication setup. Post as a blog draft. |

### Free Resources
- **SQLBolt** — https://sqlbolt.com/ (interactive SQL lessons, start here)
- **PostgreSQL Exercises** — https://pgexercises.com/ (hands-on SQL practice)
- **Use The Index, Luke!** — https://use-the-index-luke.com/ (the best free resource on indexing, period)
- **CMU Database Systems Course (Andy Pavlo)** — https://www.youtube.com/playlist?list=PLSE8ODhjZXjbj8BMuIrRcacnQh20hmY9g (world-class DB lectures, free)
- **MongoDB University** — https://university.mongodb.com/ (free courses)
- **Hussein Nasser — Database Engineering playlist** — YouTube (covers internals deeply)
- **Designing Data-Intensive Applications (DDIA) by Martin Kleppmann** — Chapters 2, 3, 5, 6 (the bible — buy or find the PDF, worth every cent)

### Checkpoint
- [ ] Can write complex SQL (CTEs, window functions, self-joins)
- [ ] Can read and interpret EXPLAIN ANALYZE output
- [ ] Can explain B-tree indexing and when NOT to index
- [ ] Can articulate when to use SQL vs NoSQL with specific reasoning
- [ ] Completed a real schema design with justified decisions
- [ ] Can explain sharding strategies and their tradeoffs

---

## Phase 3: System Design Patterns (Week 5–6)

**Dates:** 2026-04-17 to 2026-05-01

### What You're Learning
- Monolith vs microservices (and the spectrum between them)
- Event-driven architecture
- CQRS (Command Query Responsibility Segregation)
- Message queues (RabbitMQ, SQS) vs event streaming (Kafka)
- Pub/Sub patterns
- Rate limiting algorithms (token bucket, sliding window)
- Circuit breaker pattern
- Saga pattern for distributed transactions
- Idempotency
- Observability (logging, metrics, tracing)

### Daily Schedule

| Day | Topic | Task |
|-----|-------|------|
| 1 | Monolith vs Microservices | Watch ByteByteGo "Monolith vs Microservices." Read Martin Fowler's "Monolith First" article. Write a pros/cons list from personal experience. |
| 2 | Service Communication | Study sync (REST, gRPC) vs async (message queues) communication. Read about gRPC and Protocol Buffers. |
| 3 | Message Queues — Theory | Watch "Message Queues Explained" by Hussein Nasser. Understand at-least-once vs exactly-once delivery. Study dead letter queues. |
| 4 | Message Queues — Practice | Set up RabbitMQ locally (Docker). Build a producer-consumer system: an order service that publishes events, a notification service that consumes them. |
| 5 | Event-Driven Architecture | Watch ByteByteGo "Event-Driven Architecture." Read about event sourcing. Diagram an event-driven e-commerce flow. |
| 6 | Kafka Basics | Watch Confluent's "Apache Kafka 101" (free course). Understand topics, partitions, consumer groups, offsets. |
| 7 | CQRS | Read Martin Fowler's CQRS article. Diagram a system where reads and writes use different data stores. Understand when CQRS is overkill. |
| 8 | Rate Limiting | Implement token bucket and sliding window rate limiters. Test them against a local API. |
| 9 | Circuit Breaker + Retry | Read about the circuit breaker pattern (Michael Nygard). Implement a basic circuit breaker in code. Understand exponential backoff. |
| 10 | Saga Pattern | Watch "Saga Pattern" by ByteByteGo. Understand choreography vs orchestration sagas. Diagram a multi-service order flow. |
| 11 | Idempotency | Read Stripe's idempotency key blog post. Implement idempotent API endpoints. Understand why this matters for payments and distributed systems. |
| 12 | Observability | Study the three pillars: logs, metrics, traces. Read about structured logging. Set up basic Prometheus + Grafana locally (Docker). |
| 13 | Architecture Review | Take a real system you've built. Redesign it using patterns from this phase. Document what changes, what stays, and why. |
| 14 | Phase 3 Capstone | Design a complete event-driven system for a Solana transaction indexer. Include: service boundaries, message flow, failure handling (circuit breakers, DLQ, retries), observability. Write it up as a blog draft. |

### Free Resources
- **Martin Fowler's Blog** — https://martinfowler.com/ (definitive articles on microservices, CQRS, event sourcing)
- **ByteByteGo YouTube** — System design patterns playlist
- **Confluent Kafka 101** — https://developer.confluent.io/courses/ (free)
- **RabbitMQ Tutorials** — https://www.rabbitmq.com/tutorials (official, hands-on)
- **"Designing Data-Intensive Applications"** — Chapters 4, 7, 8, 9, 11, 12
- **Microsoft Cloud Design Patterns** — https://learn.microsoft.com/en-us/azure/architecture/patterns/ (comprehensive pattern catalog, free)
- **Sam Newman — "Building Microservices"** — Chapter summaries available on various blogs
- **The Twelve-Factor App** — https://12factor.net/ (short, essential reading)

### Checkpoint
- [ ] Can explain microservices tradeoffs without defaulting to "microservices good"
- [ ] Built a working message queue system locally
- [ ] Can diagram event-driven architecture for a real use case
- [ ] Can explain CQRS and when it's worth the complexity
- [ ] Implemented rate limiting and circuit breaker patterns
- [ ] Can design a system with proper failure handling

---

## Phase 4: Practice — System Design Interviews (Week 7–8)

**Dates:** 2026-05-01 to 2026-05-15

### What You're Learning
- How to approach system design problems methodically
- How to scope, estimate, and communicate trade-offs
- How to draw clear architecture diagrams under pressure
- How to handle follow-up questions and deep dives

### The Framework (Use This Every Time)

```
1. CLARIFY (2 min)    — Ask questions. Define scope. Identify users, scale, constraints.
2. ESTIMATE (3 min)   — Back-of-envelope: QPS, storage, bandwidth.
3. HIGH-LEVEL (5 min) — Draw the big boxes: client, API, services, DB, cache.
4. DEEP DIVE (15 min) — Go deep on 2-3 components. This is where you show expertise.
5. TRADE-OFFS (5 min) — Discuss alternatives. What breaks at 10x scale? What would you monitor?
```

### Daily Schedule

| Day | Topic | Task |
|-----|-------|------|
| 1 | Back-of-envelope estimation | Practice: estimate QPS, storage, and bandwidth for Twitter, YouTube, WhatsApp. Use powers of 2 and standard latency numbers. |
| 2 | Design a URL Shortener | Follow the framework. Focus on: hash generation, collision handling, database choice, read-heavy optimization, analytics. Write up your design. |
| 3 | Design a Rate Limiter | System-level rate limiter. Focus on: algorithm choice, distributed rate limiting, Redis-based implementation, edge cases. |
| 4 | Design Twitter/X Feed | Focus on: fan-out on write vs fan-out on read, celebrity problem, timeline caching, real-time updates via WebSockets. |
| 5 | Design a Chat System (WhatsApp) | Focus on: WebSocket management, message delivery guarantees, group chats, presence indicators, message storage. |
| 6 | Design YouTube/Video Platform | Focus on: video upload pipeline, transcoding, CDN distribution, recommendation pre-computation, view counting at scale. |
| 7 | Design a Notification System | Focus on: multi-channel (push, SMS, email), priority queues, rate limiting per user, template system, delivery tracking. |
| 8 | Design a Web Crawler | Focus on: URL frontier, politeness policy, deduplication (bloom filters), distributed crawling, robots.txt. |
| 9 | Design an E-Commerce System | Focus on: inventory management (avoid overselling), payment processing, order state machine, search (Elasticsearch). |
| 10 | Design a Solana Indexer | Your domain! Focus on: RPC polling vs WebSocket, transaction parsing, database schema for on-chain data, handling reorgs, API layer. |
| 11 | Mock Interview #1 | Pick a random problem. Set a 35-minute timer. Talk out loud (record yourself). Review against solutions. |
| 12 | Mock Interview #2 | Different problem. Same format. Focus on what you missed in #1. |
| 13 | Mock Interview #3 | Ask a friend or use Pramp (free). Get external feedback. |
| 14 | Final Capstone | Write a blog post: "How I'd Design [X] — A System Design Walkthrough." Publish it. Add to portfolio. |

### Free Resources
- **System Design Interview by Alex Xu** — Volume 1 and 2 (buy these — they are the highest ROI books for this phase)
- **Exponent System Design YouTube playlist** — https://www.youtube.com/@tryexponent (mock interview format)
- **ByteByteGo System Design playlist** — covers most classic problems
- **Pramp** — https://www.pramp.com/ (free mock interviews with real people)
- **Neetcode System Design playlist** — https://www.youtube.com/@NeetCode (concise and clear)
- **System Design Primer (GitHub)** — https://github.com/donnemartin/system-design-primer (reference for all problems)
- **Latency numbers every programmer should know** — https://gist.github.com/jboner/2841832

### Checkpoint
- [ ] Can solve a system design problem in 35 minutes using the framework
- [ ] Completed at least 8 design problems with written solutions
- [ ] Did at least 2 mock interviews (1 solo recorded, 1 with another person)
- [ ] Published 1 system design blog post
- [ ] Can do back-of-envelope estimation confidently

---

## Key Books (Priority Order)

| # | Book | Why | Cost |
|---|------|-----|------|
| 1 | Designing Data-Intensive Applications — Martin Kleppmann | The single most important book. Covers databases, replication, partitioning, consistency, batch/stream processing. | ~$40 |
| 2 | System Design Interview Vol 1 — Alex Xu | Step-by-step walkthroughs of 15+ classic design problems. | ~$35 |
| 3 | System Design Interview Vol 2 — Alex Xu | More advanced problems (proximity service, stock exchange, etc.). | ~$40 |
| 4 | Database Internals — Alex Petrov | Deep dive into how databases actually work (B-trees, LSM trees, consensus). Read after Phase 2. | ~$45 |

## Weekly Rituals

- **Monday:** Set the week's learning goal. Write it down.
- **Daily:** 1.5–2 hours of focused study. Log what you covered.
- **Friday:** Write a short summary of what you learned that week. Post as a Twitter thread or blog draft.
- **Sunday:** Review the week. Update progress.json. Adjust pace if needed.

## How This Connects to Your Career

| Target Role | How This Helps |
|-------------|---------------|
| AI Engineer | You'll understand how to build inference pipelines at scale, cache model outputs, design ML system architectures |
| Solana Developer | Database design for indexers, system design for RPC infrastructure, event-driven architectures for on-chain data |
| Backend Engineer | This IS the job. System design interviews are the gate. |
| Full Stack Engineer | You'll design backends that don't fall over, and understand the infrastructure your frontends depend on |

---

*Plan created: 2026-03-20*
*Status: Active — Phase 1 in progress*
