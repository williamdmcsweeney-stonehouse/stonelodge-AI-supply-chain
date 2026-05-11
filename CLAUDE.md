# Peckham Capital — Project Guide (Supply Chain)

<!-- BEGIN CROSS-REPO -->

## What We Are Building

Peckham is building a **self-improving investment research system** — 20 specialized agents that collectively outperform any generalist analyst on breadth, depth, speed, and memory, and get meaningfully better every week without manual intervention.

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
- **AI**: Anthropic Claude API (Opus for analyst chat, Haiku for high-volume daily state). Central model registry: `src/config/models.js`.

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
> - `scripts/guard-agent-memory-path.js` PreToolUse hook blocks any Write/Edit/NotebookEdit that targets `*\OneDrive\*`, `C:\Users\willi\.claude\agent-memory`, or any C:\Projects\Peckham path.
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
The company is **Peckham Capital** (not "Peckham").

<!-- END CROSS-REPO -->

> **For the full agent system, training programs, behavioral rules, and backend-specific detail, see `stonelodge-backend/CLAUDE.md`.** Sync is automated via `scripts/sync-cross-repo-claude-md.js` in the backend repo — do not edit the block above directly here, edit it in backend and re-run the sync.
