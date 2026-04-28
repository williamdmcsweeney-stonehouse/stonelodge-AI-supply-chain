# AI Infra Supply Chain Model — Assumptions Validation
**Date:** 2026-04-28
**Reviewers:** `tech-ai-sector-analyst`, `industrials-sector-analyst`
**Source basis:** Q1 2026 prints (GEV, VRT, ETN, SE, FIX, PWR), GS Jan/Feb 2026 semi notes, NVDA 3Q25 + GTC 2026, JPM Mar 2026 grid primer, Wolfe Comm Tech, MS GRoM, Epoch AI, MLPerf 4.1.

This document is the canonical record of every parameter that was reviewed, what changed, and the source of the change. Cite this when justifying the model's outputs.

---

## A. Calibration Anchors (most important — change together)

| # | Parameter | Old | New | Confidence | Source |
|---|---|---|---|---|---|
| A1 | 2025 AI infra power anchor | 30 GW | **38 GW** | M | Hyperscaler 2025 CapEx $296B at $55B/GW × 70% compute = ~30 GW added 2025 alone, plus 2023-24 stock (~12-18 GW) → 38 GW already energized is consistent with NVDA $1T order book + JPM grid queue data |
| A2 | `tokens_per_kwh_2025` | 3,600,000 | **7,000,000** | H | H100 = 3.6M tok/kWh; B200 = 3-4× H100 (MLPerf 4.1, Llama-3 405B); GB200 NVL72 higher. NVDA 3Q25 confirms GB200/GB300 = 2/3 of Blackwell shipments. 2025 deployed mix is overwhelmingly Blackwell, not Hopper |
| A3 | `efficiency_doubling_years` | 2.5 | **2.0** | H | NVDA cadence collapsed from 2yr to ~12-month with 1.6-2× per gen (H100→H200→B200→GB200→Rubin). Epoch AI confirms 2× / 2yr post-2018 trend. **THIS pulls power inflection from ~2031 to ~2028-29** |
| A4 | `tflop_per_w` (was static) | 5.65 | **9.0 in 2025, ramping by gen to ~25 by 2030** | H | H100=5.65, H200=7.0, B200=9.0, GB200=~15, Rubin VR200=25-30. Share-weighted 2025 fleet ≈ 9.0, not 5.65. Should be a step function |
| A5 | `server_kw` (was static) | 25 | **65 in 2025 → 90 (2026) → 120 (2027) → 180 (2030)** | H | GB200 NVL72 = 132 kW/rack at 72 GPUs. Rack-scale (NVL36/NVL72) dominant for new builds. Power density growing faster than the model assumed |
| A6 | `inference_utilization_2025` | 0.067 | **0.12** | M-H | Inference > training at most hyperscalers by end-2025; reasoning models consume 4-7× per query; Hopper repurposed to inference per NVDA 3Q25 |
| A7 | `inference_utilization_2035` | 0.18 | **0.30** | M-H | Same trajectory logic; consensus has fleet utilization rising as workload mix shifts further to inference |

**Net effect of A1-A7 together:** Token output trajectory roughly preserved (38 GW × 7M ≈ old 30 GW × 3.6M with correct fleet composition), but **power inflection moves from ~2031 → ~2028-29**, and per-server economics shift from "more racks" to "denser racks."

---

## B. Per-Layer Supply Growth & Lead Time Updates

| Layer | `supply_growth_pct` Old → New | `lead_time_yrs` Old → New | Confidence | Notes |
|---|---|---|---|---|
| Power Generation | 0.07 → **0.04** | 8.0 (keep) | H | EIA: US net summer adds 2.0-3.3%/yr 2023-25. GEV +59% orders are *demand*, not supply. Industrials specialist owns this call |
| **Transformers / Switchgear** | **SPLIT** into two layers below | — | H | LPT and distribution diverging — aggregating loses signal |
| ↳ **Large Power Transformers (NEW)** | new = **0.08** | new = **3.5** | H | Lead times worsened to 100-210 weeks (from 128); Hitachi VA online 2028, SE Charlotte 2027; WoodMac deficit 30%→5% by 2030 |
| ↳ **Distribution Transformers (NEW)** | new = **0.18** | new = **1.0** | H | Distribution capacity catching up; ETN/NVT/HUBB 10-14% capacity adds |
| UPS / Backup Power | 0.22 → **0.20** | 1.0 (keep) | M | Slight 48V direct-DC cannibalization; effectively unchanged |
| Liquid Cooling | 0.45 → **0.55** | 0.75 (keep) | H | VRT 2025 actuals +60% YoY in liquid; >70% attach by 2026; both agents agree 45% understates the inflection |
| GPU / AI Accelerators | 0.55 → **0.45** | 1.25 (keep) | M | NVDA unit growth normalizing +50-60% 2025→26, +35-40% by 2027 |
| HBM Memory | 0.38 → **0.32** | 1.75 (keep) | H | GS Feb 2026: industry undersupply 5.1%/4.0% in 2026/27; ASIC HBM share 33-36%. Real bit-supply growth 30-35% |
| CoWoS / Advanced Packaging | 0.32 (keep) | **1.0 through 2H26, 1.5 from 2027+** | M-H | TSMC ramps 80→130k WPM end-26 (+62%); HBM4 retightens 2027 (wafer-thinning + interposer area). Bifurcate lead time |
| Fab Equipment | 0.20 → **0.11** | 1.5 (keep) | H | GS WFE: $98B 2024 → $109B 2026 = ~11% over 2 yrs. 0.20 was way too high |
| EDA Tools / IP | 0.18 → **0.14** | 0.5 (keep) | M | Custom-silicon wave (AVGO $21B Anthropic, TPU v7, Trainium 3, OpenAI 2027); supply elastically grows in revenue not capacity |
| CPU / Host Processors | 0.28 → **0.22** | 1.0 (keep) | M | x86 server +1% units; ARM +600bps to 7%; AMD +200bps/yr; net unit capacity 5-8% |
| Server DRAM | 0.30 → **0.25** | 1.25 (keep) | H | GS Feb 2026: server DRAM (ex-HBM) +39%/+22% 2026/27 demand vs 22-25% supply. Customers asking 2028 allocation |
| Advanced Substrates / PCB | 0.25 → **0.20** | 1.0 (keep) | M | IBIDEN/Unimicron/AT&S at 95%+ utilization on AI-grade; **add Ajinomoto 2802 JP — sole ABF dielectric film supplier (true monopoly)** |
| Scale-Out Networking Silicon | 0.50 → **0.45** | 0.75 (keep) | M-H | AVGO Tomahawk 6 (102.4T) volume; ANET silicon attach +50% in 2025 |
| Optical Transceivers | 0.40 → **0.35** | 1.0 (keep) | M | 800G ramping; 1.6T early 2026; CPO transition 2027-28 |
| Fiber / Physical Cabling | 0.35 → **0.30** | 0.5 (keep) | M-H | Corning capacity-constrained 2024-26; Prysmian/CommScope at ceiling; MTP/MPO chokepoint |
| High-Speed Connectors | 0.38 → **0.35** | 0.5 (keep) | M | APH 2025 +28% organic; demand +40%+ given rack-density |
| Data Center Construction | 0.20 → **0.12** | 2.0 (keep) | H | Specialty contractor *labor* capacity grows 5-8%/yr; PWR $44B / FIX $12.5B record backlogs reflect demand not supply |
| DC REITs / Co-lo | 0.18 → **0.10** | 2.5 → **3.0** | M | New supply land+power-gated; PJM queue determines supply; 30-48mo for net-new wholesale |

---

## C. New Layers (3 — all add)

### C1. GOES (Grain-Oriented Electrical Steel)
- `lead_time_yrs`: 4.0 | `supply_growth_pct`: 0.03 | `demand_driver`: compute | `demand_scale`: 0.6
- **Names:** CLF (P), POSCO 005490.KS (P), JFE 5411.T (P), Nippon Steel 5401.T (P), Stalprodukt STP.WA (S), ThyssenKrupp TKA.DE (S), Baoshan 600019.SS (S)
- **Why:** Single US producer (CLF — Butler PA, Zanesville OH); physics-limited expansion; upstream of every transformer. Currently trades as commodity steel; embedded GOES franchise not in any sell-side SOTP.
- **Dashboard placement:** Upstream of LPT in flow chart.

### C2. Skilled Electrical Labor
- `lead_time_yrs`: 4.5 | `supply_growth_pct`: 0.04 (apprenticeship completion rate) | `demand_driver`: capex | `demand_scale`: 1.1
- **Names:** MYRG (P), PWR (P), EME (P), FIX (P), IESC (P — rethink prior cut), APG (S), MTZ (S), DY (S), PRIM (S), LMB (K)
- **Why:** MSFT President called it "#1 problem" March 2026; 4-5yr apprenticeship; no capex fix. Likely the LAST binding constraint to clear, persisting through 2028+.
- **Dashboard placement:** Upstream of DC Construction in flow chart.

### C3. Grid Interconnect Queue
- `lead_time_yrs`: 6.0 | `supply_growth_pct`: 0.05 | `demand_driver`: capex | `demand_scale`: 1.3
- **Names:** GEV (P), SE (P), 6501.T (P), PWR (P), MYRG (P), CEG/TLN (P — behind-the-meter bypass), AEP (S), EXC (S), DUK (S), SO (S), VST (S), ABB (S), NEE (K)
- **Why:** PJM queue 8+ years (from <2 in 2008); ERCOT 2,000+ requests. Distinct from generation capacity — having a turbine doesn't mean you can plug into the grid. FERC Dec 2025 colocation order now in effect.
- **Dashboard placement:** Adjacent to Power Gen in flow chart, with bypass arrows to CEG/TLN behind-the-meter nuclear.

---

## D. Names List Expansion (8-12 per layer — used to populate Supply Chain Map)

[See agent reports — full ranked lists per layer, with primary/secondary/kicker classification, will be encoded directly in `model.py` `LAYERS[layer]["names"]` and the new `LAYERS[layer]["names_detail"]` dict.]

Key additions worth flagging:
- **Ajinomoto 2802 JP** — sole ABF dielectric film supplier (substrates layer); true monopoly
- **BESI NA** — hybrid bonding tools (CoWoS); structural winner
- **ENTG** — materials per wafer +50% 5nm→1.4nm; GS Buy $128
- **Rambus RMBS** — HBM4 memory interface IP royalty stream; under-appreciated
- **Ampere Computing** — pure-play ARM server CPU (currently private)
- **Hitachi 6501.T** — Hitachi Energy embedded; LPT capacity coming 2028

---

## E. Top Mispricing Surfaces (the "easiest bets" output for the dashboard)

1. **CLF (Cleveland-Cliffs) GOES franchise** — single largest mispriced AI-infra stack stock. Trades as commodity steel; embedded GOES monopoly not in any SOTP. Highest priority research action.

2. **GEV / CEG / TLN multi-year power-gen rent capture beyond consensus** — 7%→4% supply growth confirms GEV pricing power 2027-30 is materially above consensus; but the 2.0-yr efficiency doubling means the *durability* is shorter than the bull narrative implies. **Scale into 2027, prepare to take off through 2028-29.**

3. **MU + SK Hynix structurally underpriced through 2027** — HBM undersupply 5.1%/4.0% with TAM raised to $54B/$75B; server DRAM (ex-HBM) +39%/+22% demand vs 22-25% supply. Multi-year, not one cycle.

4. **Specialty contractor labor-rent capture (MYRG/PWR/EME/FIX)** — new Skilled Electrical Labor layer at 4% supply vs ~12% demand growth makes 2026-28 margin expansion materially above consensus. **Worth revisiting the IESC pass.**

5. **APH ascendant on rack-density mix** — server_kw 25→65 ramping shifts AI server economics from "more racks" to "denser racks"; connector $/server explodes. Re-rank APH up; re-rank IBIDEN/Unimicron lower for *volume* exposure but keep for *content/$* exposure (flag Ajinomoto as sole-source ABF play).

---

## F. Items Left As-Is (low confidence to change — keep for now)

- `hbm_gb_per_tflop = 1.38` — defensible (B200 192GB / 140 TFLOP ≈ 1.37)
- `ports_per_mw = 11000` — can't verify without SemiAnalysis primary source
- `pue_2025 = 1.40 → pue_2040 = 1.15` — best-of-class hyperscalers approach 1.10 with liquid; trajectory ok
- `dram_tb_per_server = 1.0` — too low for B200 platforms (up to 4 TB) but defensible as fleet-blended; flag for future ramp
- CoWoS/Fab/EDA scaling formula weights — relative weights look fine

---

## G. Implementation Checklist for `model.py`

1. Update calibration anchors (A1-A7) — simultaneous, not piecemeal
2. Replace single `Transformers / Switchgear` row with `Large Power Transformers` + `Distribution Transformers`
3. Add 3 new layers (GOES, Skilled Electrical Labor, Grid Interconnect Queue) to `LAYERS` and `LAYER_DEMAND_COL`
4. Update all per-layer `supply_growth_pct` per Section B
5. Update CoWoS lead time to ramp 1.0 → 1.5 in 2027
6. Make `tflop_per_w` and `server_kw` step functions over time (currently static)
7. Add `LAYERS[layer]["names_detail"]` dict with primary/secondary/kicker classification
8. Update `FLOW_NODES` and `FLOW_EDGES` to insert new layers in correct positions

---

*This validation doc supersedes the static numbers in `model.py` as of 2026-04-28. Refresh after Q2 2026 prints (mid-July).*

---

## ADDENDUM — Round 2 (silicon stack) — 2026-04-28 evening

PM flagged that memory and CPU were under-represented in the easiest-bets ranking. Dispatched `tech-ai-sector-analyst` (round 2) and `earnings-transcript-analyst` to review. Agents converged independently on the same findings.

### New layers added (3)

| Layer | `lead_time_yrs` | `supply_growth_pct` | `demand_driver` | Top names |
|---|---|---|---|---|
| **ABF Dielectric Film** | 4.0 | 0.06 | capex | Ajinomoto 2802.T (P, sole), Sekisui Chemical 4204.T (S), Mitsui Chemicals 4183.T (S) |
| **HBM Hybrid Bonding** | 2.0 | 0.18 | compute | BESI (P), ASMPT 0522.HK (P), Han Mi Semi (P), AMAT (S), TEL 8035.T (S) |
| **EUV Mask Inspection / Pellicles** | 3.0 | 0.10 | capex | Lasertec 6920.T (P), Mitsui Chemicals 4183.T (P), ASML (S) |

**Why these are distinct from existing layers:**
- ABF was hidden inside Substrates (0.20 supply growth) but is a true single-source monopoly
- HBM3e uses TC bonders (Han Mi/ASMPT); HBM4 ramping 2H26-1H27 transitions to hybrid bonding (BESI/AMAT/TEL) at 4× equipment intensity per die — this step change is invisible in the bit-supply HBM Memory layer
- Lasertec is monopoly on actinic EUV mask inspection; trading -30% from 2024 highs on stale "EUV peaking" narrative; A16 has more EUV layers than N2

### Scoring formula change

**Old:** `sum across layers (tightness × tier_weight)` — favored breadth, suppressed monopolies

**New (composite):**
- 50% **Breadth** — sum across layers, normalized by /3 (a 3-layer P-tier 100/100 name = 100)
- 30% **Depth** — max single-layer tightness × tier (rewards deeply-tight pure-plays)
- 20% **Monopoly Boost** — boolean 100/0 against curated `MONOPOLY_TICKERS` list

`MONOPOLY_TICKERS = {CLF, Ajinomoto 2802.T, Lasertec 6920.T, BESI, ASML, TSM, MU, GLW, Han Mi Semi, ASMPT 0522.HK, Mitsui Chemicals 4183.T}`

### Why memory wasn't surfacing (fixed now)

MU/Hynix/Samsung play 2 layers (HBM + Server DRAM); power names play 3-4 layers. Sum-only scoring drowned memory plays even when HBM was 92/100 tight. New formula puts MU at #8, BESI at #2, Lasertec at #6, Han Mi at #5, ASMPT at #7 — all top 10.

### CPU verdict

Leave loose. ARM share gain (Graviton/Cobalt/Axion/Grace) and AMD x86 gains are real but already captured under GPU and EDA layers. Optional cosmetic (not implemented): scale `cpu_per_server` 2.0 → 1.2 over 2025-30 to reflect Grace bundling. CPU is a beneficiary, not a bottleneck.

### Round 2 mispricing surfaces (top 5 silicon stack)

1. **Ajinomoto 2802.T** — sole ABF supplier, trades as food/staples; specialty chem re-rate catalyst 2026-27 as Fukushima capacity hits HBM4/CoWoS-L peak demand. **Most mispriced silicon-stack name** per round 2.
2. **BESI** — hybrid bonding tools monopoly into HBM4 transition; sell-side underestimates HBM4 unit volume vs trailing logic-on-logic.
3. **MU** — GS Feb 2026: HBM undersupply 5.1%/4.0% 2026/27 + server DRAM (ex-HBM) +39%/+22% demand vs 22-25% supply, customers booking 2028 allocation. Trades at ~12x normalized — cyclical-DRAM frame still dominates. **Override the cyclical quant by noting server DRAM is now 57% of total demand by 2027.**
4. **Lasertec 6920.T** — actinic EUV mask inspection monopoly; -30% from 2024 highs on stale narrative; A16 EUV layer count > N2; High-NA extends monopoly to ACTIS A300.
5. **Han Mi Semi 042700.KS** — TC bonder for Korean HBM ecosystem; 90%+ share for Hynix/Samsung HBM3e.

### Files / agent outputs

- `research/assumptions_semis_round2.md` — tech-ai round 2 full analysis (referenced by agent; raw write blocked by sandbox)
- `research/transcript_scan_memory_cpu_april2026.md` — earnings-transcript agent scoping doc (web access blocked; couldn't pull live transcripts)

### Refresh trigger

This addendum should be reviewed after MU FQ2 FY26 (May 2026) and SK Hynix Q1 2026 — both will validate or invalidate the multi-year HBM/server DRAM forward-commitment language that anchors the MU mispricing call.

---

## ADDENDUM — Round 3 (macro gap framework) — 2026-04-28 evening

PM shared `Token_and_Data_Build_Out_v4_2.xlsx` from colleague — adds an **"Efficiency Overlay"** sheet with a fully-sourced aggregate-GW demand vs supply gap framework. This is more thesis-aligned than my layer-level model and now sits as the headline view of the dashboard. Layer-level tightness scoring becomes the granular drilldown beneath it.

### What changed

**Anchor reconciliation (3 different "right" numbers):**
- 30 GW = AI-only inferred from token math (my original)
- 40 GW = hyperscaler AI energized fleet (tech-AI agent triangulation)
- **66 GW = TOTAL global DC operational capacity** (Cushman & Wakefield: US 40.6 + EMEA 10.3 + APAC 12.2). This is the colleague's anchor; broader than AI-only because power gen, transformers, and grid serve all DC, not just AI.

**Macro gap framework (the headline thesis):**
- Demand: gross tokens × compute-per-token-index (1 / fleet-weighted efficiency)
- Supply: anchor compounded at 4 phase rates (22% / 30% / 25% / 15%)
- Gap: demand − supply
- Capex: incremental supply × $18.9M/MW × 25% to power & grid

**Numbers reconcile to colleague's Excel to ±0.1 GW per year:**
- Peak gap **440 GW @ 2030**, 67% undersupplied
- Balance year **2035** (+19 GW gap = signal to fade)
- Overshoot starts **2036** ("fiber-optic moment")
- Cumulative power & grid capex 2025-42: **$7.9 trillion** (matches colleague exactly)

### Macro scenarios (per Excel rows 64-67)

| Name | Doubling | Fleet lag | Result |
|---|---|---|---|
| **Base — empirical** | 2.0yr | 6yr | Gap persists through 2034+. No air pocket for power names. |
| Bear — fast efficiency | 1.5yr | 4yr | Gap closes ~2032. Air-pocket risk for silicon names. |
| Bull — physics slowdown | 3.0yr | 8yr | Gap never closes through 2042. All tiers durable. |
| Infrastructure-only | (slow build rates) | 6yr | Gap even larger. |

### Items to follow up with colleague

- **T10-T15 tier numbering** in their supply chain map. PM speculated these might be years; my read is they're component tiers (turbines / substation / line hardware / galvanizing / gas-turbine components / etc). Confirm with colleague.
- **AZZ Inc** (galvanizing) — explicitly mentioned in colleague's note as part of the $7.9T flow but not currently in `LAYERS` or `LAYER_NAMES_DETAIL`. Worth adding as a sub-bottleneck adjacent to GOES.

### Files

- `Token_and_Data_Build_Out_v4_2.xlsx` (root of this repo) — colleague's canonical input
- `model.py::build_macro_gap()` — the framework implementation, sourced lines 52-61 of the Excel
- `model.py::MACRO_SCENARIOS` — the 4 scenarios from Excel rows 64-67
- `model.py::gap_summary()` — extracts peak / balance / overshoot for headline metrics


---

## Round 4 — colleague's 14-tier scaffolding (April 2026)

### What changed

Colleague shared two HTML deliverables alongside the Excel:
- `AI_Supply_Chain_Flow_Diagram_v3.html` — interactive 14-tier flow, 154 companies, FactSet EV/EBITDA + pivotal (★) + market cap
- `AI_Supply_Chain_Valuation_Grid_v5.html` — same scaffold + per-tier `insight` narrative

Confirmed: **T1-T15 are tiers, not years.** T6 (Hyperscalers) and T10 (DC Hub) are demand-side, so 14 active supply tiers. Tracks: silicon (T1-T6), dc (T7-T8), power (T9, T11-T14), defense (T15).

### Adopted

1. **Canonical T1-T15 tier numbering.** Added `LAYER_TIER` mapping in model.py — every model layer now also has a tier ID and track tag. Surfaces in dashboard as a pill on every card and a column in the easiest-bets table.
2. **Pivotal (★) ticker set.** 16 names colleague flagged as critical-path / sole-source within their tier. Renders as a gold ★ in dashboard. (Distinct from MONOPOLY_TICKERS which drives the +20% composite-score boost.)
3. **Four new layers** that didn't exist anywhere in the model:
   - **T12 Line Hardware & HVDC Cable** (PLPC ★ 18.7x, NKT ★ 14.3x, HUBB, Prysmian, TEL)
   - **T13 Steel Poles & Towers** (VMI ★ 14.1x, ACA ★ 12.4x — duopoly on engineered transmission structures)
   - **T14 Galvanizing** (AZZ ★ 12.5x ~40% NA share, VMI vertically integrated)
   - **T15 Defense Adjacent** (GHM ★ 33.7x, ESE ★ 26.1x, ATMU ★ 13.7x, plus BWXT/HII/GD/CW/TDG/HEI/IPGP)
4. **Deferred:** EV/EBITDA integration. PM has Bloomberg, not FactSet — will pull valuations later.

### The 16 pivotal ★ names

Sorted by colleague's EV/EBITDA (cheap first = highest mispricing per his framework):

| Ticker | Tier | Track | EV/EBITDA | Notes |
|---|---|---|---|---|
| CLF | T11 | power | 10.7x | GOES sole-source US — already in MONOPOLY |
| ACA | T13 | power | 12.4x | Steel pole duopolist — NEW LAYER |
| AZZ | T14 | power | 12.5x | Galvanizing duopolist — NEW LAYER |
| ATMU | T15 | defense | 13.7x | Turbine air filtration — NEW LAYER |
| VMI | T13 | power | 14.1x | Steel poles + galvanizing — NEW LAYER |
| NKT | T12 | power | 14.3x | HVDC subsea cable — NEW LAYER |
| SPXC | T11 | power | 18.1x | Transformer cores + switchgear — bumped to P-tier |
| PLPC | T12 | power | 18.7x | Pole-line hardware — NEW LAYER |
| HUBB | T8/T11 | dc/power | 20.0x | Connectors + grid hardware (multi-tier) |
| ESE | T2/T11/T15 | multi | 26.1x | Doble + ETS-Lindgren + Globe (3 tiers) |
| FIX | T7 | dc | 30.5x | Comfort Systems modular pre-fab |
| GHM | T15 | defense | 33.7x | Naval nuclear + AI cooling vacuum systems |
| POWL | T11 | power | 34.5x | Powell switchgear — bumped to P-tier |
| ACLS | T2 | silicon | 35.3x | Ion implant — added to Fab Equipment |
| MPWR | T3 | silicon | 64.4x | On-board PMIC for AI servers — added to UPS |
| ALAB | T5 | silicon | 77.3x | PCIe/CXL retimers |

### Updated MONOPOLY_TICKERS additions

- AZZ (galvanizing oligopoly)
- VMI, ACA (steel pole duopoly)
- NKT (HVDC subsea cable duopolist with Prysmian)
- PLPC (sole-source on certain pole-line specs)
- BWXT (naval nuclear sole-source)
- ATMU (installed-base lock-in on turbine inlet filtration)

### Bottleneck Map updates

- Reorganized columns: Materials / Power & Grid / Silicon / Platform & Net / Facility & Defense
- Galvanizing → Materials column (alongside GOES)
- Line Hardware & HVDC + Steel Poles & Towers → Power & Grid column
- Defense Adjacent → its own slot in Facility & Defense column
- Every card now shows a tier pill (T1-T15) and ★ next to pivotal tickers in the chip row

### What's next (deferred)

- **EV/EBITDA integration** — wait for Bloomberg pull from PM. Will go in as a "Valuation" column in the easiest-bets table next to Composite Score.
- **Per-tier `insight` narrative** from colleague's valuation grid HTML — could surface as a tooltip / expandable on each Bottleneck Map column header.
- **Add T1 Raw Materials & Specialty Chemicals as a separate layer** (currently we map ABF Dielectric Film to T1 but have no broader raw-materials layer covering Shin-Etsu, SUMCO, Entegris, Linde, Air Products, Albemarle).

### Files / lines

- `model.py` — 4 new layers in `LAYERS`, new entries in `LAYER_NAMES_DETAIL`, extended `MONOPOLY_TICKERS`, new `PIVOTAL_TICKERS` set, new `LAYER_TIER` + `TRACK_COLOR` mappings
- `dashboard_v2/app.py` — tier pills + ★ badges on bottleneck map cards, bet cards, per-layer cards, and full ranking table
- `research/colleague_flow_diagram_v3.json` — structured extract used to drive the integration
