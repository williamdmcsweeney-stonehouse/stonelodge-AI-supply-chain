# AI Infrastructure Supply Chain — Stonehouse Capital Management

## This Repo
Standalone Python + Streamlit research tool.
- `model.py` — 18-layer supply chain model, 30 GW 2025 calibration
- `app.py` — 5-tab Streamlit dashboard (demand levers, heat map, flow chart)
- `run.bat` — launch on http://localhost:8502
- Excel token demand model lives in `$STONEHOUSE_BACKEND/data/research/Technology and AI Analyst/AI Edge and Robotics/Token and Data Build Out.xlsx`

## Sibling Repos
```
W:\projects\
├── stonelodge-backend\     ← Express API, agent memory, research data
├── stonelodge-frontend\    ← React dashboard
├── stonelodge-supply-chain\ ← THIS REPO
└── Business-Score-Backtest\ ← Bloomberg fundamentals
```

## Agents Available
All 19 Stonehouse agents are in `.claude/agents/`. Their accumulated memory
lives in `W:\projects\stonelodge-backend\.claude\agent-memory\`. Invoke them
for sector-specific analysis — e.g. tech-ai-sector-analyst for GPU/HBM/networking
supply dynamics, industrials-sector-analyst for power grid constraints, 
semiconductors-analyst for fab equipment and packaging bottlenecks.

## Key Model Parameters
- Calibration anchor: 30 GW AI infrastructure power in 2025
- Efficiency doubling: every 2.5 years (historical compute efficiency trend)
- Power inflection: ~2031 base case (efficiency gains outpace token demand growth)
- Tightness persistence post-peak: lead-time-weighted decay (power gen 8yr = slow; GPU 1.25yr = fast)

## Environment Variables
```
STONEHOUSE_BACKEND       = W:\projects\stonelodge-backend
STONEHOUSE_SUPPLY_CHAIN  = W:\projects\stonelodge-supply-chain
```
