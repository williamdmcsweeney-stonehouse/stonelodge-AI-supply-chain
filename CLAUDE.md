# Peckham Capital — Project Guide (Supply Chain)

<!-- BEGIN CROSS-REPO -->

## What We Are Building

Peckham is a **self-improving investment research system** — 23 specialized agents that outperform any generalist analyst on breadth, depth, speed, and memory, and improve weekly without manual intervention.

**The edge:**
1. **Perfect domain depth** — each sector agent is the undisputed historian of their vertical.
2. **Perfect memory** — every analysis, correction, calibration, and lesson persisted; the knowledge floor only rises.
3. **Continuous cross-training** — sector agents and the PM train each other; the PM absorbs sector signals, sectors absorb PM cycle pattern recognition.
4. **Live data infrastructure (PIP)** — SEC filings, transcripts, app velocity, short interest, management career history, M&A databases, consensus estimates.

**Flywheel:** Analysis → Memory → Cross-Training → Better Analysis (compounding).

**The standard:** Every analysis must match top-tier buy-side research depth and intellectual honesty — independent thesis, verified data, price-conditioned recommendation, explicit kill conditions. The system covers 40+ names across 10 sectors 24/7 and gets better every week.

---

## Repository Structure

Four separate git repos. All four pull/push independently via GitHub.

```
W:\projects\                                     ← parent, NOT on C:, NOT in OneDrive
├── stonelodge-backend\                          ← Express + Prisma + Supabase
├── stonelodge-frontend\                         ← React + Vite
├── stonelodge-supply-chain\                     ← Python + Streamlit (AI infra)
└── Business-Score-Backtest\                     ← Python + SQLite + Streamlit
    └── db\backtest.db (2.9 GB, gitignored) + dashboard.db.gz (committed)
```

**Env vars (User scope, persist via `setx`):** `STONEHOUSE_ROOT`, `STONEHOUSE_BACKEND`, `STONEHOUSE_FRONTEND`, `STONEHOUSE_BACKTEST`, `STONEHOUSE_SUPPLY_CHAIN`. Fresh-machine setup commands: **`docs/NEW-PC-BOOTSTRAP.md`**.

All wrappers self-locate via `%~dp0..` / `$PSScriptRoot`; cross-repo paths resolve via env vars with sibling-folder fallback.

| Repo | Stack | Deploy | Notes |
|------|-------|--------|-------|
| Backend | Express + Prisma + Supabase PostgreSQL | Vercel (API serverless) | AI: Opus (chat) / Haiku (high-volume). Model registry: `src/config/models.js`. |
| Frontend | React + Vite | Vercel (`stonelodge-frontend.vercel.app`) | Own git history — `pull` before editing, `push` after. |
| Backtest | Python + SQLite + Streamlit | local | Generates `db/backtest.db` (Bloomberg quarterly fundamentals). Backend reads via `src/services/backtest-scores.js` + `scripts/sync-bloomberg-from-backtest.js` + `scripts/export-backtest-scores.js` (all three resolve via `STONEHOUSE_BACKTEST` env var with sibling fallback). DB gitignored — restore from `D:\Agent Deep Dive Archive\backtest-db\` or regenerate. |
| Supply Chain | Python + Streamlit | local (`run.bat` → :8502) | Reads `$STONEHOUSE_BACKEND/data/research/Technology and AI Analyst/AI Edge and Robotics/Token and Data Build Out.xlsx`. Outputs power inflection year + per-layer tightness scores. |

---

> **⚠️ NEVER move repos into OneDrive or onto C:.** OneDrive corrupts git internals (`fatal: mmap failed: Invalid argument`) and silently split-brains across machines; C: lacks headroom for nightly autopilot writes. Full postmortem (2026-04-11 incident) + guardrail scripts: **`docs/disaster-recovery.md` → "Environment hazards"**. Enforced by `scripts/guard-agent-memory-path.js` (PreToolUse) + `scripts/precommit-no-onedrive-no-cdrive.js` (pre-commit), both installed via `node scripts/install-git-hooks.js` (auto-runs on `postinstall`).

## D:\ Drive — Archives Only

`D:\Agent Deep Dive Archive\` is for archived deep-dive transcripts (after distillation to MEMORY.md), large data exports (Bloomberg dumps, backtest.db backups), and forensic pre-migration copies. **Live agent memory NEVER goes there** — must stay at `<project>/.claude/agent-memory/<agent>/`. Archive convention: `D:\Agent Deep Dive Archive\agent-memory\<agent>\<YYYY-MM-DD>_<topic>\`.

## Company Name
The company is **Peckham Capital** (not "Peckham", not "Stonehouse", not "Stonelodge" — those are legacy repo names).

<!-- END CROSS-REPO -->

> **For the full agent system, training programs, behavioral rules, and backend-specific detail, see `stonelodge-backend/CLAUDE.md`.** Sync is automated via `scripts/sync-cross-repo-claude-md.js` in the backend repo — do not edit the block above directly here, edit it in backend and re-run the sync.
