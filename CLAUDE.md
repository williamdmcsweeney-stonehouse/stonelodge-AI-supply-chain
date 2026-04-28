# AI Infrastructure Supply Chain

Standalone Python + Streamlit research tool that translates token demand into
supply chain bottleneck signals across the AI infrastructure stack.

## Files
- `model.py` — 29-layer supply chain model with vintaged-fleet GPU dynamics + macro gap framework
- `dashboard_v2/app.py` — Streamlit dashboard (macro gap, capex flow, bottleneck map, heat grid, easiest bets)
- `app.py` — legacy v1 (5-tab UI on port 8502)
- `dashboard_v2/run.bat` — launch v2 on http://localhost:8503
- `Token_and_Data_Build_Out_v4_2.xlsx` — token demand + Efficiency Overlay input

## Key Model Parameters
- Calibration anchor: ~30 GW AI infrastructure power in 2025 (sector model); 66 GW total DC capacity (macro gap framework)
- Efficiency doubling: every 2.0 years (empirical) — base case in MACRO_SCENARIOS
- GPU fleet life: 6 years — drives lag between frontier efficiency and fleet-weighted efficiency
- Power inflection: depends on scenario; gap persists through 2034+ in Base case
- Tightness persistence post-peak: lead-time-weighted decay (power gen 8yr = slow; GPU 1.25yr = fast)
- 14 active supply tiers (T1-T15, T6/T10 demand-side) across silicon / dc / power / defense tracks

## Research Notes
See `research/assumptions_validation.md` for the full calibration history (Rounds 1-4).
