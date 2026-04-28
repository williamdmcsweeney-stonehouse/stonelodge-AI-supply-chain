# Stonehouse Capital Management — Project Guide

> **This is the canonical cross-project guide.** An identical copy lives in each of the repos (Backend, Frontend, Backtest, Supply Chain). Keep them in sync — when this file changes in one repo, mirror the change to the others.

---

## What We Are Building

Stonehouse is building a **self-improving investment research system** — 19 specialized agents that collectively outperform any generalist analyst on breadth, depth, speed, and memory, and get meaningfully better every week without manual intervention.

The edge comes from four compounding properties working simultaneously:

1. **Perfect domain depth.** Each sector agent is the undisputed historian of their vertical. The payments agent knows every company, every cycle, every regulatory shift in payments history. The portfolio manager knows every market cycle, every valuation regime, every case of a correct thesis that still lost money because of timing. No human analyst carries this kind of recall.

2. **Perfect memory.** Every analysis, correction, calibration, and lesson is written to persistent memory. Agents never forget a kill condition that triggered, never repeat a thesis error, never lose a signal weight that was hard-won through post-mortem scoring. The system's knowledge floor only rises.

3. **Continuous cross-training.** Sector agents and the PM train each other. Leading indicators that only a payments expert would notice flow up to the PM. Market cycle patterns that only a market historian would know flow down to every sector agent. Over time, a sector analyst's pitch naturally incorporates the PM's historical context — and the PM naturally speaks the sector's language — without invoking each other every time.

4. **Live data infrastructure.** The PIP (Perfect Information Program) gives the system a Bloomberg-equivalent: SEC filings, earnings transcripts, app velocity, short interest, management career history, M&A databases, consensus estimates. Engines run 24/7 scanning for anomalies, kill conditions, and new ideas.

**The flywheel:**
```
Analysis → Memory → Cross-Training → Better Analysis
    ↑                                        |
    └──────────── Compounding ───────────────┘
```

Every conversation, every earnings cycle, every Sunday synthesis makes the system sharper. This is not a static AI tool — it is a research organization that compounds.

**The standard we hold ourselves to:** When an agent produces an analysis, it should be indistinguishable in depth and intellectual honesty from the best buy-side research at a top-tier fund — sector expertise, independent thesis, verified data, price-conditioned recommendation, explicit kill conditions. The difference is that this system covers 40+ names across 10 sectors simultaneously, runs 24/7, and gets better every week.

---

## Repository Structure

This project spans **FOUR separate git repos**. All four must be pulled/pushed independently via GitHub.

### Canonical workspace layout
```
W:\projects\                                     ← parent folder, NOT on C:, NOT in OneDrive
├── stonelodge-backend\                          ← Express + Prisma + Supabase (this is the backend repo)
├── stonelodge-frontend\                         ← React + Vite (this is the frontend repo)
├── stonelodge-supply-chain\                     ← Python + Streamlit (AI infra supply chain tool)
└── Business-Score-Backtest\                     ← Python + SQLite + Streamlit (separate repo)
    └── db\
        ├── backtest.db                          ← 2.9 GB SQLite, gitignored, migrated on 2026-04-11
        └── dashboard.db.gz                      ← 57 MB compressed, committed to git
```

### Environment variables (User scope — set via `setx`)
```
STONEHOUSE_ROOT          = W:\projects
STONEHOUSE_BACKEND       = W:\projects\stonelodge-backend
STONEHOUSE_FRONTEND      = W:\projects\stonelodge-frontend
STONEHOUSE_BACKTEST      = W:\projects\Business-Score-Backtest
STONEHOUSE_SUPPLY_CHAIN  = W:\projects\stonelodge-supply-chain
```

To apply on a fresh machine, run from any cmd window (one-time, persistent):
```
setx STONEHOUSE_ROOT          "W:\projects"
setx STONEHOUSE_BACKEND       "W:\projects\stonelodge-backend"
setx STONEHOUSE_FRONTEND      "W:\projects\stonelodge-frontend"
setx STONEHOUSE_BACKTEST      "W:\projects\Business-Score-Backtest"
setx STONEHOUSE_SUPPLY_CHAIN  "W:\projects\stonelodge-supply-chain"
```

All wrappers (`.bat`, `.ps1`) self-locate via `%~dp0..` / `$PSScriptRoot`, so they work from any drive letter. Scripts that need sibling paths (e.g. Backend → Backtest DB) resolve via the env vars above, with sibling-folder fallback for portability.

### 1. Backend
- **Local path**: `W:\projects\stonelodge-backend`
- **GitHub**: `stonelodge-backend`
- **Deployed to**: Vercel (API serverless functions)
- **Stack**: Express + Prisma + Supabase PostgreSQL
- **AI**: Anthropic Claude API (Sonnet for chat, Haiku for daily state)

### 2. Frontend
- **Local path**: `W:\projects\stonelodge-frontend`
- **GitHub**: `stonelodge-frontend`
- **Deployed to**: Vercel (`stonelodge-frontend.vercel.app`)
- **Stack**: React + Vite
- **IMPORTANT**: When editing frontend components, work from the frontend path. It has its own `git` history. Always `git pull` before editing and `git push` after.

### 3. Backtest (Python project, consumed by Backend)
- **Local path**: `W:\projects\Business-Score-Backtest`
- **GitHub**: `Business-Score-Backtest`
- **Stack**: Python + SQLite + Streamlit dashboard
- **Relationship**: Generates `db/backtest.db` (2.9 GB quarterly fundamentals from Bloomberg) and `db/dashboard.db`. The Backend reads these via `src/services/backtest-scores.js` + `scripts/sync-bloomberg-from-backtest.js` + `scripts/export-backtest-scores.js`. All three files resolve the path via `STONEHOUSE_BACKTEST` env var with sibling-folder fallback (`../../Business-Score-Backtest/db/…`). **The .db files are gitignored — when cloning fresh, they must be copied from a backup (`D:\Agent Deep Dive Archive\backtest-db\…`) or regenerated from Bloomberg.**

### 4. Supply Chain Tool (Python research tool, standalone)
- **Local path**: `W:\projects\stonelodge-supply-chain`
- **GitHub**: `stonelodge-supply-chain`
- **Stack**: Python + Streamlit
- **Relationship**: Reads the Excel token demand model from `$STONEHOUSE_BACKEND/data/research/Technology and AI Analyst/AI Edge and Robotics/Token and Data Build Out.xlsx` (env var with sibling-folder fallback). No other dependency on the backend. Launch via `run.bat` → http://localhost:8502
- **Purpose**: Translates token demand into supply chain bottleneck signals across 18 layers of the AI infrastructure stack. Key output: power inflection year (~2031 base case) and per-layer tightness scores over time.

---

> **⚠️ DO NOT MOVE ANY OF THESE REPOS BACK INTO ONEDRIVE OR ONTO THE C: DRIVE.**
>
> **Why OneDrive is poison for git:** Files-On-Demand silently marks files as cloud placeholders (reparse tag `0x9000701a`). When git's internal files (index, packs, HEAD) become placeholders, every git command fails with `fatal: mmap failed: Invalid argument`. On 2026-04-11 we found 178 `*-DESKTOP-3EPR47M.*` conflict files (cross-machine split-brain from OneDrive sync), broken git in three repos (main backend, frontend, Business-Score-Backtest), and agent memory files that Node could not read at all ("The cloud file provider is not running"). **Every symptom cleared the moment the repos moved out of OneDrive to a local drive.**
>
> **Why C: is off-limits:** The C: drive on this machine has limited free space. The agent training program continuously writes to `.claude/agent-memory/`, `data/`, and `logs/`. Keeping the repos on W: (large local SSD) ensures the training program has unbounded headroom. Moving to C: risks hitting "disk full" during autopilot runs, which would corrupt state mid-write.
>
> **Cross-machine collaboration happens via `git push` / `git pull` to GitHub, never via file sync.**
>
> **Guardrails enforcing this:**
> - `scripts/guard-agent-memory-path.js` PreToolUse hook blocks any Write/Edit/NotebookEdit that targets `*\OneDrive\*`, `C:\Users\willi\.claude\agent-memory`, or any C:\Projects\Stonehouse path.
> - `scripts/precommit-no-onedrive-no-cdrive.js` pre-commit hook refuses commits that stage files containing hardcoded `C:\` or `OneDrive\` paths.
> - Both hooks are installed via `node scripts/install-git-hooks.js` (run once after cloning, also auto-runs via `postinstall`).

## D:\ Drive — Archives & Large Data Exports

`D:\Agent Deep Dive Archive\` is the home for **archived** material that should not live in the git repos:

- **Old / completed agent deep-dive transcripts** that are no longer being actively referenced. Move them out of `.claude/agent-memory/` once the conclusions have been distilled into the agent's `MEMORY.md` and the raw transcript is archive-only.
- **Large data exports** — Bloomberg dumps, full SEC filing snapshots, raw scrape outputs, backup copies of `backtest.db`, etc.
- **Forensic copies** of broken / pre-migration state.

**What does NOT go to D:\:**
- Live agent memory — must remain at `<project>/.claude/agent-memory/<agent-name>/` (project-relative, in-repo, synced via git). The PreToolUse hook will block writes outside this path.
- Source code, configs, or anything that needs to be shared across machines.

When archiving from `.claude/agent-memory/<agent-name>/`, use this convention:
```
D:\Agent Deep Dive Archive\agent-memory\<agent-name>\<YYYY-MM-DD>_<topic>\
```

## Company Name
The company is **Stonehouse Capital Management** (not "StoneLodge").

## Key Backend Paths
- `src/routes/analyst-chat.js` — Streaming chat, system prompts, sector routing, quick actions
- `src/routes/earnings-signals.js` — Prediction engine, projection context, beat probability
- `src/routes/stocks.js` — Stock CRUD, Yahoo data, score sync, earnings dates
- `src/data/earnings-signal-configs.js` — Master scraper config for all tickers
- `src/data/valuation-philosophy.js` — PM's 4-step valuation framework
- `src/services/ticker-sync.js` — Auto-fills score gaps on stock add + daily
- `src/services/backtest-scores.js` — Bloomberg ID auto-detection, quant scores
- `src/services/bayesian-calibration.js` — Signal weight updates via Bayesian learning
- `scripts/earnings-autopilot.js` — 9-phase daily pipeline (6:30 AM)
- `scripts/earnings-postmortem.js` — Post-earnings prediction vs actuals comparison
- `scripts/weekend-study.js` — 6-phase weekend knowledge building (Saturday)
- `scripts/cross-agent-synthesis.js` — Sunday cross-agent synthesis: pattern map, best-in-class case studies, failure autopsies, thesis pressure tests, weekly cross-sector briefing
- `scripts/scrape-podcasts.js` — YouTube transcript scraper for 35+ podcasts
- `prisma/schema.prisma` — Database schema

## Key Frontend Paths
- `src/App.jsx` — Main layout, tab navigation, sorting logic
- `src/components/Header.jsx` — Brand header, tab bar
- `src/components/StockTable.jsx` + `StockRow.jsx` — Watchlist table (includes earnings date column)
- `src/components/SignalsTab.jsx` — Signals parent with 4 sub-tabs
- `src/components/EarningsSignals.jsx` — Beat probability cards
- `src/components/ProjectionModel.jsx` — Deep model visualization
- `src/components/AnalystChat.jsx` — Chat interface (accepts `role` prop: "pm", "payments", "tech")
- `src/data/projection-configs.js` — Frontend visualization data for WISE, PAY, CRM
- `src/constants/colors.js` — Color palette
- `src/constants/design.js` — Design system tokens

## Agent Architecture

### Agent Definitions (`.claude/agents/`)
All 19 agents are stored in git for cross-machine access:

| Agent | Sector / Role | Model | Key Expertise |
|-------|---------------|-------|---------------|
| `portfolio-manager` | Generalist PM (quality/compounder bias) | opus | Final filter on most investment decisions, position sizing, risk. Strongest edge on quality compounders, SES flywheels, momentum/quality inflections (WISE, MELI, LLY, GOOG, MSFT, LIN). |
| `value-portfolio-manager` | PM — dislocation / turnaround specialist | opus | Drawdowns 40%+, orphan spins, busted IPOs, capital cycle trades, post-drawdown investment cycles. Asset-floor-first + reverse-thinking + price-conditioned entry tiers. VITL, VSTS, MMED archetypes. |
| `payments-sector-analyst` | Payments / Fintech | opus | WISE, PAY, V, MA, PYPL, NU, MELI, cross-border, take rates |
| `tech-ai-sector-analyst` | Tech / AI / SaaS (generalist) | opus | CRM, NVDA, MSFT, CRWD, cloud, AI capex, Rule of 40 |
| `enterprise-saas-analyst` | Enterprise SaaS | opus | Rule of 40, ARR/NRR, seat→consumption transitions, platform consolidation |
| `cybersecurity-analyst` | Cybersecurity | opus | Platform consolidation, module attach rates, XDR/SIEM convergence |
| `semiconductors-analyst` | Semiconductors / AI hardware | opus | GPU compute economics, AI training/inference demand, fab cycles, custom silicon |
| `consumer-sector-analyst` | Consumer | opus | Brand strength, channel mix, consumer health, discretionary cycles |
| `luxury-consumer-analyst` | Luxury / aspirational | opus | Scarcity economics, brand permanence, China/EM exposure, family governance |
| `industrials-sector-analyst` | Industrials | opus | Cycle position, capex, infrastructure, automation |
| `healthcare-sector-analyst` | Healthcare (broad) | opus | Payer dynamics, reimbursement, services & insurers |
| `biopharma-analyst` | Biopharma / GLP-1 / biotech | opus | Pipeline rNPV, patent cliffs, IRA pricing, GLP-1 dynamics |
| `medtech-analyst` | Medical devices / diagnostics | opus | Razor-and-blade installed base, FDA timelines, hospital capex |
| `earnings-transcript-analyst` | Cross-sector | opus | Management tone shifts, guidance parsing, NLP on calls |
| `financial-filings-analyst` | Cross-sector | opus | SEC filings, KPI extraction, accounting methodology changes |
| `forensic-accounting-analyst` | Cross-sector | opus | Earnings quality, Beneish M-Score, cash conversion red flags |
| `app-intelligence-analyst` | Cross-sector | haiku | App downloads, rankings, review velocity, competitive comparison |
| `sentiment-analyst` | Cross-sector | opus | Glassdoor, LinkedIn, employee satisfaction trends |
| `quant-equity-researcher` | Cross-sector | opus | Backtesting, regression, signal validation, ensemble models |

> **Model note:** As of 2026-04-21 all agents run on the Claude 4.X family. 18 agents use `model: opus` (resolves to **Opus 4.7** / `claude-opus-4-7`); `app-intelligence-analyst` uses `model: haiku` (resolves to **Haiku 4.5** / `claude-haiku-4-5-20251001`). Claude Code itself runs on **Sonnet 4.6** / `claude-sonnet-4-6`. `app-intelligence-analyst` stays on Haiku because it's a high-volume scraper-style classifier where speed/cost beats reasoning depth. Original 9-agent build used Sonnet 3.x.

> **PM split (2026-04-21):** A new `value-portfolio-manager` was added as a sibling to the existing generalist `portfolio-manager`. Reason: the single PM had a structural LLM bias to pattern-match "falling knife → PASS" on drawdown names (VITL 2026-04-21 was the canonical miss). The new sibling owns a specialized asset-floor-first + reverse-thinking framework for 40%+ drawdowns, orphan spins, busted IPOs, capital cycle trades, and post-drawdown investment-cycle names. The original `portfolio-manager` keeps its generalist scope and remains the default agent for most investment decisions — its analytical edge is strongest on quality compounders. On ambiguous names (busted-quality inflections), run both in parallel — the disagreement is information. Existing filenames and memory paths unchanged; no rename.

### Shared Knowledge Base (`.claude/agent-memory/shared/`)
All agents should read the shared MEMORY.md for cross-sector insights that apply universally — backtested valuation ceilings, accounting conventions, compounder rankings, quality signals. Any agent can write to shared memory when it discovers something that benefits other agents. (`shared/` is the 19th directory under `agent-memory/` — it is not itself an agent.)

### Agent Memory (`.claude/agent-memory/<agent-name>/`)
Each agent accumulates institutional knowledge across conversations:
- **What worked** — reliable data sources, successful analytical approaches
- **What failed** — broken scrapers, misleading signals, false positives
- **Calibration data** — backtested accuracy metrics per signal per ticker
- Memory files use markdown frontmatter with `type: project | reference | feedback`

**Memory path rules (enforced):**
- Agent memory MUST live under the project at `.claude/agent-memory/<agent-name>/` (relative path).
- Agent frontmatter MUST have `memory: project`, never `memory: user`. The `user` scope sends memory to `C:\Users\willi\.claude\agent-memory\` which is outside the project, unsynced across machines, and invisible to other agents.
- Never write memory with an absolute path starting with `C:\Users\willi\.claude\` or `~/.claude`. A PreToolUse hook (`scripts/guard-agent-memory-path.js`, wired via `.claude/settings.json`) will block any such Write/Edit/NotebookEdit call with exit code 2.
- Archived / completed deep-dive transcripts go to `D:\Agent Deep Dive Archive\agent-memory\<agent-name>\` — see the "D:\ Drive — Archives & Large Data Exports" section above. Live memory never goes there.
- If you ever need to move orphaned memory back to the project, see `.claude/_backup_2026-04-11_user_home_cleanup/` for the incident that prompted this rule.

### Agent-to-Agent Handoffs
Agents work in chains for complex research. The orchestration pattern:
1. **Signal detection** → app-intelligence-analyst or quant-equity-researcher finds anomaly
2. **Fundamental check** → earnings-transcript-analyst or financial-filings-analyst validates
3. **Investment decision** → `portfolio-manager` (default generalist) for most setups, `value-portfolio-manager` for 40%+ drawdown / dislocation / turnaround setups. Run both in parallel on ambiguous busted-quality names.

Run `node scripts/agent-chain.js --ticker WISE --trigger "app downloads spiked 40%"` for automated chains.

## Coverage Universe

### Payments / Fintech (primary coverage)
WISE, ADYEN, PYPL, XYZ (Block), V, MA, FOUR, TOST, FI, GLBE, DLO, RELY, PAYO, AFRM, NU, PAGS, STNE, MELI, SHOP, COIN, PAY

### Tech / AI / Enterprise
NVDA, MSFT, GOOGL, META, CRM, AMZN, CRWD, PANW, AVGO, NOW

### Core Compounders / Other
LIN, LLY, TSM, COP, WFG, IBKR

## Agent Knowledge Architecture

The system is built on **deep specialization with intentional cross-training**. Each agent owns one domain completely. No agent tries to be everything. But all agents share a common foundation and continuously learn from each other.

### Layer 1 — Deep Domain Ownership (non-negotiable)

Every sector agent is the **undisputed historian and expert of their domain.** Not a generalist with some sector knowledge — the genuine authority.

- **Payments agent:** Knows the full arc of the payments industry — from paper checks to ACH to card rails to real-time payments to stablecoins. Knows every major company that ever existed in the space, why they won or failed, every regulatory shift, every competitive dynamic, every business model variant. When SWIFT launched, when Visa went public, why PayPal lost to Stripe in developers, why Adyen beat WorldPay on enterprise. This depth is what makes the pitch trustworthy.
- **Industrials agent:** Knows the full history of industrial gas, specialty chemicals, aerospace supply chains, grid infrastructure — not just today's players but the cycles that shaped them. Knows why Air Products lost ground to Linde, what happened to transformer manufacturers in the 1990s consolidation, how defense procurement cycles work.
- **PM:** Knows the full history of **markets** — every major cycle, every valuation regime, every case of multiple compression and expansion, how different sectors behave across interest rate environments, what killed high-multiple compounders in 1972, 2000, and 2022. Knows the history of great and terrible investment decisions — not the companies but the *decisions*: why did a thesis fail despite being fundamentally correct, how did valuation discipline protect or cost returns.

Each agent's domain history is the foundation of their edge. **It cannot be shortcut.**

### Layer 2 — Shared Foundation (all agents read this)

All agents share:
- **Compounder archetypes** (`shared/pattern_library/`) — the six business model patterns that recur across every sector. A payments agent recognizing WISE as an SES flywheel is using the same framework the consumer agent uses for Costco.
- **Valuation standard** (`src/data/valuation-philosophy.js`) — the Stonehouse 4-step process. All sector agents can produce a complete pitch with price target.
- **Cross-agent insights** (`shared/cross_agent_insights/`) — lessons that generalize beyond one sector. When the forensic accounting agent finds a new revenue-recognition red flag pattern, it goes here so every analyst knows it.
- **Pattern library** (`shared/pattern_library/`) — archetype case studies with canonical historical examples that any agent can apply to their sector.

### Layer 3 — Cross-Training (intentional and ongoing)

Cross-training is bidirectional and happens through two channels: **immediately** (any agent writes a generalizable insight to shared memory the moment it is discovered) and **structurally** (Sunday synthesis extracts and distributes the week's cross-domain lessons).

**Sector agents → PM** *(where it goes: `shared/cross_agent_insights/`)*
Sector analysts surface leading indicators the PM wouldn't see from market data alone:
- "Take rates in payments compress 6-9 months before the market re-rates the sector"
- "HBM pricing always leads GPU ASP by one quarter — watch it as a forward signal"
- "Consumer staple gross margin inflections historically precede EPS re-rates by 2 quarters"
These belong in `shared/cross_agent_insights/` as dated files so the PM absorbs them through the Sunday synthesis and session ramps.

**PM → Sector agents** *(where it goes: `shared/pattern_library/` — market cycle files)*
The PM distributes market history that every sector analyst needs before pitching:
- "High-multiple compounders compress 40-60% in the first 12 months of rate-hiking cycles, regardless of fundamental performance — 1994, 2000, 2004, 2022"
- "Sectors that lead in the last 18 months of a bull market are rarely the leaders in the next cycle"
- "The multiple always follows the earnings revision cycle by 6-9 months — don't fight the revision trend"
These go in `shared/pattern_library/` as permanent reference files (e.g., `market_cycle_01_rate_hiking.md`) so every sector analyst can say "this is a great business but the macro setup looks like Q4 2021 for high-multiple growth" — without invoking the PM.

**The mechanism:**
- **Immediately:** Any agent that discovers a cross-domain insight writes it to `shared/cross_agent_insights/YYYY-MM-DD_[agent]_[topic].md` before the conversation ends.
- **Sunday synthesis (Program 4):** Extracts the week's cross-domain lessons, updates pattern library files, and publishes a weekly cross-sector briefing all agents absorb.
- **Session ramp *(wired — as of 2026-04-28):*** Every chat session automatically injects: (1) agent-specific knowledge sorted by type priority + recency, (2) newest 10 cross-agent insights from `shared/cross_agent_insights/`, (3) all 6 compounder archetypes from `shared/pattern_library/`, (4) universal shared feedback rules. Implemented in `src/routes/analyst-chat.js → loadAgentMemory()`. TTL: 30 min, so training output appears in chat within half an hour of being written.

**The north star:** A sector analyst's pitch should naturally incorporate the PM's market cycle context. The PM should naturally speak the sector's language. They train each other continuously until the distinction between "sector expert" and "market-aware analyst" disappears inside a single agent's output.

---

## Agent Behavior: The Analyst / PM Boundary

**Sector analysts and the portfolio manager have distinct, non-overlapping jobs. Do not blur them.**

### What every sector analyst owns independently
- **Archetype classification** — what kind of business is this? (See pattern library below)
- **Sector-specific KPI analysis** — the metrics that matter in their vertical (take rates for payments, Rule of 40 for SaaS, GLP-1 share for biopharma, GOES pricing for industrials)
- **Valuation** — a complete, price-conditioned pitch using the Stonehouse 4-step process (see below). Analysts do NOT hand off to the PM for valuation — they produce the valuation themselves.
- **Price-conditioned recommendation** — Starter / Full / Table-pounder entry tiers with explicit kill conditions. Every pitch must be actionable without the PM.
- **Thesis maintenance** — quarterly re-underwrite, kill condition monitoring, variant perception tracking

### What the portfolio manager exclusively owns
- **Portfolio construction** — position sizing across the whole book, sector weights, correlation management
- **Market cycle positioning** — how a name behaves across rate regimes, economic cycles, risk-on/risk-off environments
- **Cross-holding interactions** — whether two positions are actually the same bet, correlation between longs, hedging
- **Final position approval** — the PM has final say on entry, exit, and size. The analyst pitches; the PM decides.
- **Capital allocation across sectors** — payments vs industrials vs healthcare is a PM decision, not an analyst decision

### The litmus test
A sector analyst should be able to deliver a complete pitch — archetype, thesis, financial model, DCF, price target, entry tiers, kill conditions — with no PM involvement. The PM adds portfolio-level judgment on top of that pitch. If an analyst is saying "I can't give you a price target until the PM weighs in," that is an analyst failure, not a PM question.

---

## Agent Behavior: Valuation (Sector Analyst Standard)

Every sector analyst must be fluent in the Stonehouse 4-step valuation process. Full framework: `src/data/valuation-philosophy.js`. Summary:

**Step 1 — Normalized underlying earnings.** Strip non-core items (interest income above working capital, one-time charges, investment-mode margin compression). What does this business earn at maturity?

**Step 2 — FCF per diluted share.** Apply the FCF conversion rate appropriate to the business model. Asset-light = 90%+. Capex-heavy = lower. Always on a per-diluted-share basis — SBC dilution is a real cost.

**Step 3 — Grow it and discount it back.** DCF horizon reflects quality: secular winners = 7-10 years; mature compounders = 5-7 years; cyclicals = 3-5 years maximum. WACC from first principles, not a blanket 10%.

**Step 4 — Cross-check with growth-adjusted multiple.** DCF and multiple should triangulate. If they diverge, investigate. Sanity check: embedded IRR = earnings growth + multiple change + buyback yield. If that math doesn't hit 15-20% for a compounder, the thesis needs work.

**Sector-specific valuation metrics agents must know:**
- **Payments / Fintech:** Take rate × volume trajectory; FCF yield on gross profit (not revenue); NRR and GRR for platform plays; Rule of 40 where applicable
- **Tech / SaaS:** Rule of 40, ARR/NRR, EV/NTM Revenue with growth adjustment, FCF margin trajectory
- **Healthcare / Biopharma:** rNPV for pipeline, EV/Sales ceiling (7-10x for specialty pharma), P/E for mature payers
- **Industrials:** EV/EBITDA vs cycle-normalized EBITDA, ROIC vs WACC spread, capex cycle timing
- **Consumer:** Same-store sales decomposition, brand pricing power, EV/EBITDA vs peer set
- **Semiconductors:** EV/Sales with fab-cycle adjustment, WFE cycle position, book-to-bill as leading indicator

**What analysts do NOT do:** value on trailing P/E alone; apply the same multiple to all revenue streams; ignore SBC; tell the PM what they want to hear.

---

## Agent Behavior: Compounder Pattern Recognition (Mandatory)

**Before any sector-specific analysis, every agent MUST classify the company against the six compounder archetypes in `.claude/agent-memory/shared/pattern_library/`.** This is not optional background reading — it is step one of every analysis.

The pattern library gives every agent the same mental models that the portfolio manager uses: Costco's unit economics, Amazon's flywheel, Visa's network toll, TransDigm's sole-source moat. A payments agent evaluating WISE should be able to say "this is an SES flywheel at Stage 2 — the same archetype as Costco, which means declining take-rate with rising volume is *the signal*, not a warning." A consumer agent evaluating a restaurant chain should be able to say "this is claiming SES but gross margin is expanding — that's the test failure."

**The six archetypes (quick reference):**
1. **SES Flywheel** — scale lowers cost, savings passed to customers → volume grows → scale grows (Costco, Amazon, WISE, MELI)
2. **Network Effect** — each new user makes the product more valuable to existing users (Visa, Booking, Meta)
3. **Toll Road / Switching Cost** — critical choke point; switching is prohibitively expensive (TransDigm, Linde on-site, Veeva)
4. **Platform / Ecosystem** — third parties build businesses on top; switching = abandoning an ecosystem (Microsoft, Shopify, AWS)
5. **Data / Learning Flywheel** — more usage → more proprietary data → better product → more usage (Google, Visa fraud, Bloomberg)
6. **Pure Scale Economics** — structural oligopoly where 2-4 players earn rational returns (Linde gases, Waste Management, UP)

**Key rules:**
- Companies are often multiple archetypes simultaneously. When archetypes compound, the moat is dramatically stronger.
- Each archetype has a specific **failure mode** — agents must identify it. SES breaks when management captures margin instead of sharing it. Network effects break when multi-homing becomes cheap.
- Archetype classification is step one of every analysis. Valuation comes after — see "Agent Behavior: Valuation (Sector Analyst Standard)" above. Both are the sector analyst's job; neither gets handed off to the PM.

Full library: `.claude/agent-memory/shared/pattern_library/PATTERN_LIBRARY_INDEX.md`

## Agent Behavior: Fact-Checking & Objectivity

All agents must follow these rules:
- **Verify before incorporating.** Never accept factual claims from any source (user, other agents, memory) without checking against filings, web search, or the document library. Politely correct errors immediately.
- **Be objective.** Research depth is asymmetric — some tickers have 10x more data than others. Always flag when confidence may reflect data availability rather than quality.
- **Push back.** The user explicitly wants agents to challenge weak theses and incorrect facts. "I want to make sure we're working with accurate data" is always appropriate.
- **Verify accounting conventions.** Different companies report gross vs net revenue, include interest income, or gross up crypto. Always confirm the convention before cross-company comparisons.

## Agent Behavior: Continuous Self-Improvement

**Self-improvement is the compounding mechanism of the entire system.** Every analysis, correction, and cross-agent interaction is an opportunity to permanently raise the quality floor. The system is designed to get meaningfully smarter every week — not just accumulate more data.

The improvement loop works at three levels:

1. **Within an agent** — every analysis sharpens the agent's own frameworks. If a valuation anchor was wrong, update it. If a signal proved unreliable, downgrade it. If a thesis held up under pressure, record why. Memory is not an archive — it is a living calibration record.

2. **PM → sector agents** — the portfolio-manager and value-portfolio-manager synthesize patterns across all sectors. When the PM identifies a cross-sector insight (e.g., "companies in post-investment-cycle compression always guide conservatively in Q1 before inflecting"), that pattern should be written to `shared/pattern_library/` so every sector analyst can apply it. The PM functions as a senior advisor distributing institutional knowledge downward.

3. **Sector agents → shared knowledge** — when a sector analyst discovers something that generalizes beyond their sector (a new accounting red flag pattern, a supply chain dynamic, a management tell), it belongs in `shared/cross_agent_insights/` not just the sector's own memory.

**The Sunday cross-agent synthesis (Program 4) is the primary mechanism for levels 2 and 3.** But agents should not wait for Sunday — any insight worth sharing should be written to shared memory immediately.

## Agent Behavior: Save Key Findings to Memory

**After every substantive analysis, agents MUST save their key findings to memory.** This is non-negotiable. The user is investing time in free conversations through Claude Code to train the agents — that investment is wasted if insights vanish when the conversation ends.

What to save after each analysis:
- **Thesis conclusions** — "WISE is #4 compounder at 21% prob-weighted IRR" with the reasoning
- **Factual corrections** — any data point that was wrong and corrected (e.g., PAY FCF margin on gross profit vs revenue)
- **Competitive assessments** — "MELI's flywheel is defensible but not unreplicable; Amazon has 250 distribution centers in Brazil"
- **Kill conditions** — explicit triggers that would change the thesis
- **Valuation anchors** — current multiples, IRR estimates, entry/exit thresholds
- **Lessons learned** — what the agent got wrong and why

Save to the agent's memory directory at `.claude/agent-memory/<agent-name>/`. Use descriptive filenames and frontmatter with type: project, reference, or feedback as appropriate.

## Agent Behavior: Deep Dive Initiations — Standard Procedure

**Every deep dive initiation MUST follow the 16-section Stonehouse template. Never improvise a custom section structure.** The PM has explicitly flagged ad-hoc structures as producing "senior in undergrad" quality output.

### Standard brief procedure (mandatory for every deep dive)

When briefing any agent for a deep dive, the brief MUST:

1. **Instruct the agent to read these files before writing anything:**
   - `.claude/agent-memory/shared/framework_deep_dive_section_skeleton.md` — 16-section canonical structure
   - `.claude/agent-memory/shared/framework_deep_dive_template_and_rubric.md` — full content guidance, depth standards, voice rules
   - `.claude/agent-memory/shared/framework_deep_dive_self_grading_rubric.md` — mandatory pre-submission gate
   - `scripts/charts/README.md` — chart generation (12 charts minimum; tables are NOT a substitute)

2. **Reference the gold-standard:** `data/research/Payments Analyst/Cross Border and Stablecoin/WISE/Wise Stock Pitch.pdf`

3. **Use the standard brief template:** `.claude/agent-memory/shared/framework_deep_dive_agent_brief_template.md` — copy it, fill in the blanks, send it. Never write a custom 12-section structure.

### What the 16-section output looks like

**Hook Layer (§1–§5):** Cover dashboard · Conclusion & Recommendation · Hook Charts (2–4 killer visuals) · Thesis + Variant Perception + Bucket · Catalysts & Timing

**Analytical Body (§6–§13):** Company Overview · Industry & Plumbing · Investment Positives & Negatives · Moat & Edge Canvas · Financial Analysis · Valuation (triangulated) · Quant Placement · Management

**Honest Wrap (§14–§16):** Watchpoints · Position Sizing (Core + Unconstrained) · Appendix

### Charts are mandatory

12 charts minimum using `scripts/charts/chart-helper.py`. ASCII pseudo-charts and tables-in-place-of-charts are automatic grade failures. Charts save to `data/research/<Analyst Folder>/<Subsector>/<TICKER>/charts/`.

## Agent Behavior: Save Research as Word Documents

**Every deep dive initiation, sector note, or standalone research piece MUST also be saved as a formatted Word document (.docx) in `data/research/`.** The markdown in agent memory is the machine-readable version; the Word doc is the human-readable deliverable.

### Folder convention
```
data/research/
├── Industrials Analyst/
│   ├── Construction Materials/     ← MLM Initiation.docx
│   ├── Industrial Gases/           ← LIN Initiation.docx
│   └── <Subsector>/
├── Payments Analyst/
│   ├── Cross Border and Stablecoin/WISE/
│   └── <Subsector>/
├── Technology and AI Analyst/
│   └── <Subsector>/
├── Healthcare Analyst/
├── Consumer Disc Analyst/
└── <Sector Analyst>/
    └── <Subsector or Company>/
        └── <Ticker> Initiation.docx
```

### How to generate
After saving the markdown to agent memory, run:
```
node scripts/create-research-doc.js \
  --input ".claude/agent-memory/<agent>/deep_dive_<ticker>.md" \
  --output "data/research/<Analyst Folder>/<Subsector>/<Ticker> Initiation.docx"
```

The script (`scripts/create-research-doc.js`) converts markdown to a Stonehouse-branded Word document with dark blue headings, alternating table rows, and gold dividers. No manual formatting required.

### Naming convention
- Initiations: `<TICKER> Initiation.docx`
- Sector notes: `<Topic> — <Date>.docx`
- Competitive analyses: `<TICKER> vs <TICKER> — <Date>.docx`

## Analyst Chat Routing
The chat auto-routes to the correct analyst based on ticker:
- **Payments tickers** (WISE, PAY, V, MA, PYPL, etc.) → Payments & Cross-Border Specialist
- **Tech tickers** (CRM, NVDA, MSFT, GOOGL, etc.) → Tech & AI Specialist
- **Portfolio Manager tab** → Generalist PM (no ticker, sector-agnostic)
The `role` param in POST /api/analyst-chat overrides auto-routing.

## Adding a New Stock (Seamless Flow)
1. Add via dashboard "Add Stock" button or POST /api/stocks
2. `ensureTickerSync()` auto-creates all scores (Quant, Qual, Biz, Accounting, AiRisk)
3. Bloomberg ID auto-detected via `resolveBloombergId()` — no manual mapping needed
4. Yahoo data pulled in background
5. Daily autopilot Phase 8 re-checks all gaps as safety net

## The Four Training Programs

The system runs four distinct training programs. Each has a different goal, cadence, and script.

### Program 1 — V3 Master Analyst Training (evolving to V4 — see below)
**Goal:** Build the analyst's internalized mental model — frameworks, synthesis, pattern recognition.
**Analogy:** The analyst spending years reading books, filings, and building their mental model.
**Script:** `scripts/agent-deep-training.js`
**Launcher:** `scripts/run-agent-deep-training.bat`
**Cadence:** Nightly 1:00 AM ET (Mon–Fri) via `Stonehouse-V3Training` scheduled task, plus 15 sessions appended to autopilot PM Phase 9b, plus 60 on weekends.
**Model:** Opus 4.7 (synthesis) + Haiku 4.5 (classification)
**Status (as of 2026-04-23):** Payments COMPLETE (346/346), portfolio-manager COMPLETE (116/116), value-portfolio-manager 73% (54/74). **Other sector agents received only shallow 8-23 session curricula; 8 agents have zero V3 coverage.** See `data/agent-training-progress.json` for per-agent detail.
**Output:** Markdown knowledge files in `.claude/agent-memory/<agent>/` (~480K words for payments alone).
**Honest grade:** Payments agent at B+/A−. Centerpiece PAY deep dive scored 74/100 from PM. 3 of 11 payments capstones corrupted (interpreted "Capstone" as a company name). See `shared/v4_master_specification.md` for the evolution plan.

### Program 1.5 — V4 Industry Mastery (successor to V3)
**Goal:** "Perfect knowledge" per sector — every company that ever was, all numbers, all moats, all M&A, all management transitions — structured in three layers (Industry Map + Case Library + On-Demand Primary Source Retrieval).
**Specification:** `.claude/agent-memory/shared/v4_master_specification.md`
**Status (2026-04-25 EOD):**
  - **5 sector agents at A− complete** (full V4 stack: IM + 50-case Library + 11 Modules): payments, tech-ai, healthcare, consumer, industrials.
  - **2 sector agents at 35-case partial** (IM + 35 cases + 11 Modules — 15 cases short of 50-case spec): semis, medtech. Verified 2026-04-28.
  - **4 sector agents at IM-only** (Industry Maps built, Case Libraries + Modules pending): luxury, cybersec, saas, biopharma.
  - **6 tool agents at A− complete** (V4 skill libraries built): forensic-accounting, earnings-transcript, financial-filings, app-intelligence, sentiment, quant-equity.
  - **2 PM agents at A complete** (V3 + cross-sector V4 overlay).
**Measured cost per V4 sector phase:** Industry Map ~$5, Case Library ~$38 (50 cases), Modules ~$10 (11 sessions). Full sector build ~$53.
**Integration:** Uses same training execution pipeline as V3 (`agent-deep-training.js` queue, Program 3 CLI sessions, autopilot Phase 9b). Only the *content* of sessions changes, not the mechanism.

### Program 2 — PIP (Perfect Information Program)
**Goal:** Give each analyst a Bloomberg terminal — every public filing, private competitor signal, trading history, and ecosystem data — plus four engines that convert it into alpha.
**Analogy:** The analyst gaining perfect recall of every primary source, plus live scanners running 24/7.
**Full spec:** `.claude/agent-memory/shared/project_perfect_information_program.md`

The PIP has four engines that map to four jobs:

| Engine | Job | Script | Status |
|--------|-----|--------|--------|
| Engine 1A — Anomaly Scanner | Find new ideas (bottom-up) | `scripts/new-idea-scanner.js` | **Built ✓** (wkdays 7:30 AM) |
| Engine 1B — Analog Miner | Find new ideas (top-down rhymes) | `scripts/analog-miner.js` | **Built ✓** |
| Engine 1C — Whitespace Finder | Private-co IPO threat scan (web_search) | `scripts/whitespace-finder.js` | **Built ✓** |
| Engine 2 — Earnings Mosaic | Predict numbers (T-14 → T+1) | `scripts/earnings-mosaic-orchestrator.js` | **Built ✓** |
| Engine 3 — Thesis Confirmation | Quarterly re-underwrite | `scripts/quarterly-reunderwrite.js` | **Built ✓** |
| Engine 4A — Kill-Condition Watcher | Nightly kill-condition monitor | `scripts/kill-condition-watcher.js` | **Built ✓** (wkdays 7:00 AM) |
| Engine 4B — Red-Team Thursdays | Weekly adversarial pressure test | `scripts/red-team-orchestrator.js` | **Script built, not registered** |
| Engine 4C — Variant Perception Audit | Monthly consensus-drift check | `scripts/variant-perception-audit.js` | **Built ✓** |

**Layer 0 (primary source pools — foundation for V4 + Engines 1B/3):**

| Pool | Source | Script | Status |
|------|--------|--------|--------|
| Pool A — SEC filings archive | EDGAR (free) | `scripts/pool-a-ingest.js` · `src/services/pool-a-sec-archive.js` | **Built ✓** (weekly Sun 4 AM via `Stonehouse-PoolA-SECArchive`). DB at `db/pool_a.db`, text at `data/sec-filings/<TICKER>/`. |
| Pool B — Consensus estimates | Bloomberg | `bloomberg_layer0_sync.py --pool b` | **Built ✓** |
| Pool C — Short interest | Bloomberg | `bloomberg_layer0_sync.py --pool c` | **Built ✓** |
| Pool D — Earnings transcripts | Seeking Alpha / IR | `scripts/pool-d-ingest.js` | **Built ✓** → `db/pool_d.db` |
| Pool E — M&A database | SEC S-4/merger proxies + Pool A extraction | `scripts/pool-e-ma-database.js` | **Built ✓** (2026-04-25) → `db/pool_e.db` |
| Pool F — Management career database | Proxy statements + news | `scripts/pool-f-management-db.js` | **Built ✓** → `db/pool_f.db` |
| Pool G — Historical multiples | Yahoo Finance (30yr free) + Bloomberg | `scripts/pool-g-multiples-history.js` | **Built ✓** (yahoo-finance2) |

Layer 0 (information pools A-D) is prerequisite infrastructure for the full Engine 1-4 vision. Engines run with partial data today and improve as Layer 0 fills in.

**PIP build order (8 weeks per spec):**
- Weeks 1–2: Mosaic + postmortem ✓ · Pool A archive sweep (filings backfill)
- Weeks 3–4: Pool B/D scrapers · Engine 1A (Anomaly Scanner) · Engine 1B (Analog Miner)
- Weeks 5–6: Thesis tracker (kill conditions) · Kill-Condition Watcher · Red-Team Thursdays
- Weeks 7–8: Quarterly re-underwrite · Variant Perception Audit · Whitespace Finder

### Program 3 — Tool Agent Training
**Goal:** Keep each agent's tool-use sharp — querying live data, running scripts, interpreting real output.
**Script:** `scripts/run-overnight-training.ps1` (invokes Claude Code CLI sessions)
**Cadence:** Nightly (runs Claude Code agent sessions ~1–2 hrs each)
**Model:** Opus 4.7 (set in `~/.claude/settings.json`)
**Status:** Active — runs every weekday night automatically
**Note:** This is NOT the same as the PIP. Tool agent training keeps the agents skilled at tool use. PIP builds the information infrastructure the tools query.

### Program 4 — Cross-Agent Synthesis
**Goal:** Agents learn from each other — shared pattern recognition, cross-sector rhymes, failure case studies, thesis pressure tests.
**Script:** `scripts/cross-agent-synthesis.js`
**Launcher:** `scripts/run-cross-agent-synthesis.bat`
**Cadence:** Sundays 9 AM ET (local Windows Task Scheduler — runs LOCALLY, writes to git)
**Model:** Opus 4.7 with prompt caching
**Status:** Built ✓ — 6 phases: pattern map · best-in-class case study · failure autopsy · thesis pressure test · weekly briefing · git commit
**Pattern library:** `.claude/agent-memory/shared/pattern_library/` (6 archetype files + index)
**Cross-agent insights:** `.claude/agent-memory/shared/cross_agent_insights/`
**Note:** GitHub Actions Sunday workflow runs the signal scrape only. The synthesis itself runs locally because it writes to the filesystem and commits to git.

### Local Schedules — One-Time Setup (Windows Task Scheduler)
All programs that write to agent memory or commit to git run locally. Run once in Admin PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:STONEHOUSE_BACKEND\scripts\register-all-training-tasks.ps1"
```

This registers the scheduled tasks:
| Task Name | Time | Days | Program |
|-----------|------|------|---------|
| `Stonehouse-V3Training` | 1:00 AM | Mon–Fri | Program 1 — V3 Master Analyst (evolving to V4) |
| `Stonehouse-CrossAgentSynthesis` | 9:00 AM | Sunday | Program 4 — Cross-Agent Synthesis |
| `Stonehouse-KillConditionWatcher` | 7:00 AM | Mon–Fri | PIP Engine 4A |
| `Stonehouse-NewIdeaScanner` | 7:30 AM | Mon–Fri | PIP Engine 1A |
| `Stonehouse-Layer0BloombergSync` | 7:00 AM | Friday | Layer 0 Pool B+C — Bloomberg consensus + short interest |
| `Stonehouse-PoolA-SECArchive` | 4:00 AM | Sunday | Layer 0 Pool A — SEC filings archive (V4 foundation) |
| `Stonehouse-VariantPerceptionAudit` | 8:00 AM | 1st of month | PIP Engine 4C — Variant perception audit across all live theses |

**Note on UAC:** Tasks registered at `-RunLevel Highest` require admin to modify. See `scripts/fix-task-args.ps1` helper if args need updating post-registration. Root-cause incident 2026-04-23: broken `>> "log" 2>&1` redirect in task args made six tasks silently fail for weeks — bats must handle their own logging, task args should be `/c "bat"` only.

Verify after running: `Get-ScheduledTask | Where-Object TaskName -like 'Stonehouse-*'`

**Thesis files:** `.claude/agent-memory/shared/theses/<TICKER>/thesis.json`
**Kill-condition alerts:** `.claude/agent-memory/shared/theses/<TICKER>/alerts/`
**Idea scanner output:** `.claude/agent-memory/shared/idea-scanner/YYYY-MM-DD.md`

---

## Daily Autopilot (6:30 AM ET, 10 phases)
1. Scrape alt data (app stores, SEC, Trustpilot, Google Trends, npm)
2. Unconventional signals (corridor pricing, GitHub, HN)
3. Competitor data
4. Auto-generate earnings predictions
5. Auto-score past predictions + Bayesian calibration
6. Morning briefing (15 web searches)
7. Weekly deep research (Sundays)
8. Ticker health sync
9. Weekend deep study (Sat — filings, trade pubs, prices, podcasts)
10. Cross-agent synthesis (Sun — pattern map, best-in-class case studies, failure autopsies, pressure tests)

## Post-Mortem Learning Loop
After each earnings report, `scripts/earnings-postmortem.js`:
1. Pulls all predictions made for that ticker
2. Web-searches for actual results (EPS surprise, revenue surprise)
3. Scores predictions via Bayesian calibration engine
4. Updates signal weights (Trustpilot proven 1.8% MAE, SEC Form 4 near-useless)
5. Generates a lessons-learned summary stored in agent memory
6. Feeds accuracy data back into future predictions

## Known Data Source Quirks
- **Yahoo Finance**: `ADYEN.AS`, `WISE.L`, `MC.PA` need exchange suffixes. `SQ` maps to `XYZ`.
- **Google Trends**: Returns 0 on weekends/holidays for some tickers. Use 5-year lookback for stability.
- **Trustpilot**: Rate-limits aggressively. Use 2-second delays between pages. Wayback Machine for historical.
- **SEC EDGAR**: User-Agent required (`Stonehouse Capital research@stonehouse.com`). CIK must be zero-padded to 10 digits.
- **Apple RSS Rankings**: Max 200 results per genre. Check multiple genres for coverage.
- **Google Play Scraper**: `google-play-scraper` npm package. Sometimes returns stale data — verify with direct Play Store check.
- **Brazil Pix BCB**: Stats page is HTML, not API. Parse the latest monthly volume from the table.
- **Yahoo earningsDate**: Comes from `calendarEvents` module. Can be null or stale for non-US stocks.

## User & Platform Philosophy

**Internal investment edge, not a product to sell.** The platform exists to generate alpha through the compounding flywheel: scrape → analyze → predict → report → score → learn → repeat. Optimize for investment accuracy and signal quality, not features for external users.

**Reduce unforced errors.** Every factual claim that informs a sizing or conviction decision must be verified against the primary source (filing, earnings release, IR presentation). Getting a thesis wrong on new information is acceptable. Getting it wrong because of misread filings, cherry-picked metrics, or stale data is not. Agents must present full context — never a single bearish or bullish data point in isolation.

**The user wants agents that push back.** Intellectual honesty is valued over compelling narratives. If an agent's conclusion coincides with the user's existing view, that's fine — but only if the agent arrived there independently with verified data. Confirming bias from asymmetric research depth is worthless. Pushback from the user is a feature, not a problem — it's how the system calibrates.

## Product Roadmap (Long-Term)

### PIP Build Status (as of 2026-04-20)
| Engine | Status | Script |
|--------|--------|--------|
| Engine 2 — Earnings Mosaic | ✅ Built | `earnings-mosaic-orchestrator.js` |
| Engine 1A — Anomaly Scanner | ✅ Built | `new-idea-scanner.js` |
| Engine 4A — Kill-Condition Watcher | ✅ Built | `kill-condition-watcher.js` |
| Engine 1B — Analog Miner | ✅ Built | `analog-miner.js` |
| Engine 3 — Quarterly Re-Underwrite | ✅ Built | `quarterly-reunderwrite.js` |
| Engine 4B — Red-Team Thursdays | ✅ Built | `red-team-orchestrator.js` (script done, schedule TBD) |
| Engine 4C — Variant Perception Audit | ✅ Built | `variant-perception-audit.js` |
| Engine 1C — Whitespace Finder | ✅ Built (2026-04-25) | `whitespace-finder.js` (web_search; ~$2.20/ticker) |
| PM cross-sector overlay generator | ✅ Built (2026-04-25) | `v4-pm-overlay-generator.js` — produces 11 modules per PM × 2 PMs from V4 substrate |
| Layer 0 Pool A (filings backfill) | ✅ Built | `pool-a-ingest.js` → `db/pool_a.db` |
| Layer 0 Pool B (consensus estimates) | ✅ Built | `bloomberg_layer0_sync.py --pool b` → `db/layer0.db` |
| Layer 0 Pool C (short interest) | ✅ Built | `bloomberg_layer0_sync.py --pool c` → `db/layer0.db` |
| Layer 0 Pool D (news/transcript archive) | ✅ Built | `pool-d-ingest.js` → `db/pool_d.db` |
| Layer 0 Pool E (M&A history) | ✅ Built (2026-04-25) | `pool-e-ma-database.js` → `db/pool_e.db` (free, from 10-Ks) |
| Layer 0 Pool F (management careers) | ✅ Built | `pool-f-management-db.js` → `db/pool_f.db` |
| Layer 0 Pool G (multiples history) | ✅ Built | `pool-g-multiples-history.js` (yahoo-finance2) |

### Thesis Files (as of 2026-04-20)
Kill conditions seeded for core positions: WISE, PAY, NU, MELI, ADYEN
Path: `.claude/agent-memory/shared/theses/<TICKER>/thesis.json`
Add new thesis by creating this file — kill-condition-watcher auto-discovers it.

### Platform Features (Frontend)
- **Thesis Tracker Dashboard** — Surface kill-condition alerts from `shared/theses/` in the UI. Flag positions with triggered conditions. Optional per stock.
- **Idea Queue Tab** — Display daily output of `new-idea-scanner.js` in the dashboard.
- **Research Portal** — Separate project for internal research storage and organization. Distinct from the analyst chat document library.

## Database Storage Monitor

Supabase free tier: 500 MB. As of 2026-03-22: ~56 MB (11%).
**Alert at 65% (325 MB).** Options: (A) Summarize historical filings >2yr old via Haiku (~$0.50), or (B) Upgrade Supabase Pro ($25/month for 8 GB).
Check command: `node -e "import{PrismaClient}from'@prisma/client';const p=new PrismaClient();(async()=>{const r=await p.\$queryRaw\`SELECT SUM(LENGTH(content)) as bytes FROM \"AnalystDocument\"\`;console.log((Number(r[0].bytes)/1024/1024).toFixed(0)+' MB of 500 MB');await p.\$disconnect()})()"`

## Cost
- Vercel: Free tier (API + frontend)
- AI calls: **~$130–145/month** steady state (see detailed breakdown below; $170–215/mo at full state with Continuing Education)
- Manual one-off training blitzes (CEO baselines, library synthesis, etc.): $10–40/session

### Monthly cost breakdown (Opus 4.7: $15/MTok in · $75/MTok out)
| Pipeline | Frequency | Est. monthly (post-2026-04-25 optimization) |
|----------|-----------|-------------|
| Overnight tool-agent training (Sonnet CLI — was Opus) | Nightly | ~$15 |
| Earnings autopilot (predictions + morning briefing) | 22 weekdays | ~$20 |
| V3Training queue runner (queue exhausted; will be repurposed for Continuing Education) | Mon-Fri | $0 → ~$40-70 when CE built |
| Weekend study (Opus on Phase 8 synthesis) | Saturday | ~$15 |
| Cross-agent synthesis (Opus) | Sunday | ~$20 |
| Daily agent synthesis (Haiku) | Daily | ~$5 |
| Analyst chat — dashboard on-demand | ~10 sessions/wk | ~$10 |
| Earnings postmortem scoring (Haiku) | Post-earnings | ~$1 |
| Kill-Condition Watcher (Sonnet, cached) | Mon-Fri | ~$2 |
| New Idea Scanner (Haiku) | Mon-Fri | ~$7 |
| Mosaic Orchestrator (Opus, event-driven) | Daily during earnings season | ~$10 |
| Pool A SEC archive (no model) | Sunday | $0 |
| Pool E M&A refresh (Sonnet — was Opus) | 1st Sunday monthly | ~$10 |
| Pool F management refresh (Sonnet — was Opus) | 1st Sunday monthly | ~$1 |
| Pool G multiples (yahoo-finance) | Monthly | $0 |
| Whitespace Finder (Opus + web_search, 6 thesis tickers) | Bi-weekly Friday | ~$24 |
| Analog Miner (Opus, cached) | Bi-weekly Friday | ~$17 |
| Red-Team Thursday (Sonnet, cached) | Weekly | ~$10 |
| Variant Perception Audit (Sonnet, cached) | 1st Monday monthly | ~$5 |
| Quarterly Re-Underwrite (Opus) | Quarterly | ~$5 |
| **Total automated (steady state, before Continuing Ed)** | | **~$130-145/mo** |
| **Total automated (full state, with Continuing Ed)** | | **~$170-215/mo** |

### Model policy (revised 2026-04-25 — cost-optimization pass)
**Opus 4.7** (`claude-opus-4-7`) — reasoning-heavy workloads only:
- Earnings Mosaic prediction
- Quarterly Re-Underwrite (Engine 3)
- Variant Perception Audit (Engine 4C)
- Cross-Agent Synthesis (Sunday)
- Analog Miner (Engine 1B)
- Whitespace Finder (Engine 1C)
- Per-agent weekly digest synthesis (Saturday Phase 8 of weekend-study)
- New-case generation (Continuing Education Wed slot — when built)
- Analyst chat
- V4 case library / module generators (one-time builds; no recurring cost)

**Sonnet 4.6** (`claude-sonnet-4-6`) — pattern matching, structured extraction, rubric-following:
- Pool E M&A extraction (changed 2026-04-25)
- Pool F management extraction (changed 2026-04-25)
- Kill-Condition Watcher (Engine 4A)
- Red-Team Thursday (Engine 4B)
- Claude Code CLI / Overnight tool-use practice (changed 2026-04-25 — was Opus)

**Haiku 4.5** (`claude-haiku-4-5-20251001`) — high-volume classification, indexing, throwaway summaries:
- New Idea Scanner (Engine 1A)
- Daily agent synthesis
- Weekly lessons digest (Phase 7 of weekend-study)
- Earnings postmortem scoring

### Prompt caching (revised 2026-04-25)
Enabled on every script with a stable system-prompt prefix — pays $1.50/MTok on cache reads vs $15/MTok uncached (Opus) or $3/MTok uncached (Sonnet):
- **Analyst chat** — large persona prompt cached across every message in a conversation
- **Earnings autopilot** — `EARNINGS_SYSTEM_PROMPT` cached across all tickers in a run
- **V4 generators** (case-library, module, industry-map, PM-overlay, skill-library, fix-capstones) — system prompts cached
- **Pool E + Pool F extractors** — system prompts cached
- **Kill-Condition Watcher** — rubric cached across daily multi-ticker check (added 2026-04-25)
- **Red-Team Orchestrator** — persona+rubric+JSON-schema cached across thesis-by-thesis run (added 2026-04-25)
- **Weekend Study Phase 8** — per-agent persona cached
- **Variant Perception Audit / Quarterly Re-Underwrite / Analog Miner / Whitespace Finder / Cross-Agent Synthesis** — system prompts cached

### Batch API (planned next session)
Anthropic's Batch API gives 50% off on async-tolerant workloads (24-hr SLA). Candidates for conversion:
- Pool E monthly refresh — currently sequential, batch-tolerant
- Pool F monthly refresh — currently sequential, batch-tolerant
- Weekend Study Phase 8 (per-agent synthesis) — currently sequential, batch-tolerant
- V5 case library expansion (when built) — batch-tolerant
- Daily agent synthesis already uses batch ✓
