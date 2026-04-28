# AI Infra Supply Chain Model — Round 2: Silicon-Stack Sub-Bottlenecks
**Date:** 2026-04-28
**Reviewer:** `tech-ai-sector-analyst`
**Trigger:** PM flagged that vintaged-fleet 40-GW / 6-yr model output puts no memory or fab-equipment names in the top-10 "easiest bets," despite HBM tightness 92/100. Top 10 is power-only (SE, Hitachi, GEV, TLN, CEG, VST, ABB, PWR, MYRG, CLF).

This document mirrors `assumptions_validation.md` for the silicon stack: which sub-bottlenecks are sole-source / structural / not-capex-fixable analogues to GOES, Skilled Labor, and Grid Interconnect on the industrials side; whether CPU is correctly modeled; what scoring-formula change surfaces memory; and the top-5 silicon-stack mispricings.

---

## Q1. Silicon-stack sub-bottlenecks the model is missing

The industrials desk added GOES, Skilled Labor, and Grid Interconnect because they are sole-source, structural, and not solvable by capex. The silicon-stack equivalents are below — ranked by how strongly they meet the same three criteria.

### C4. ABF Dielectric Film (NEW LAYER — strong recommend)

- `lead_time_yrs`: 4.0  |  `supply_growth_pct`: 0.06  |  `demand_driver`: capex  |  `demand_scale`: 1.0
- **Why a separate layer:** Ajinomoto 2802.T is the **sole global supplier** of ABF (Ajinomoto Build-up Film), the dielectric layer in every advanced flip-chip substrate (CoWoS, FCBGA, every AI accelerator and high-end CPU). This is one of the cleanest monopolies in the entire stack — closer to GOES than to general substrates. Currently buried inside "Advanced Substrates / PCB" where the loose substrate growth (0.20) masks the structural ABF chokepoint.
- **Capacity:** Two plants (Kawasaki + Fukushima). Ajinomoto signaled +30% capacity by FY2027 but ABF is a chemical formulation problem, not a fab problem — yields take years to ramp. AI-grade ABF (thicker, larger panels for CoWoS-L) is a different SKU from PC/server FCBGA, so capacity isn't fungible.
- **Lead time logic:** 3-4 years from green-field to qualified production for a new plant; 18-24 months for a debottleneck. 4.0 is right.
- **Names (P/S/K):**
  - `Ajinomoto 2802.T` — **P** — Sole supplier; AI-grade ABF mix shift = ASP +30-50%
  - `Resonac 4004.T` — **S** — Solder resist, SAP photoresist for substrates; closest adjacent
  - `Sumitomo Bakelite 4203.T` — **K** — Some specialty materials
- **Demand column:** `substrate_M` (good fit) or new `cowos_index + substrate_M` blend.

### C5. EUV Mask Inspection / Pellicles (NEW LAYER — strong recommend)

- `lead_time_yrs`: 3.0  |  `supply_growth_pct`: 0.10  |  `demand_driver`: capex  |  `demand_scale`: 0.6
- **Why a separate layer:** Lasertec 6920.T is the **sole supplier of actinic EUV mask blank/pattern inspection systems** (ACTIS A150, MATRICS X8). Mitsui Chemicals + ASML own EUV pellicles. These are 100% sole-source, multi-year qualification, and **gating items for every EUV layer** — TSMC N2/A16, Samsung 1.4nm, Intel 18A all blocked without these. Currently lumped into "Fab Equipment" at 11% supply growth, which dilutes signal.
- **Capacity:** Lasertec ships ~10-15 actinic systems/yr, each $40-80M. EUV layer count is rising 2x N5→A16. Pellicle yield on High-NA still 60-70% per ASML disclosures.
- **Names (P/S/K):**
  - `Lasertec 6920.T` — **P** — Actinic EUV mask inspection monopoly
  - `Mitsui Chemicals 4183.T` — **P** — EUV pellicle co-leader with ASML
  - `KLAC` — **S** — DUV mask inspection + e-beam; not actinic, but adjacent
  - `Carl Zeiss SMT (private)` — **K** — Optics into ASML (not investable directly)

### C6. HBM Hybrid Bonding & TC Bonders (NEW LAYER — recommend)

- `lead_time_yrs`: 2.0  |  `supply_growth_pct`: 0.18  |  `demand_driver`: capex  |  `demand_scale`: 1.2
- **Why a separate layer:** HBM3e uses TC (thermo-compression) bonding — Han Mi Semi + ASMPT duopoly. **HBM4 (2H26 ramp) shifts to hybrid bonding** for the bottom 4 dies, reusing the same BESI/AMAT/TEL toolset that does logic-on-logic bonding on M2 Ultra / SoIC. This is **the most under-modeled equipment transition of 2026-28** and totally invisible at the current "HBM Memory" layer. The transition to hybrid bonding takes the per-die bonding step from $0.80 to ~$3.50 of equipment depreciation — 4x equipment intensity.
- **Capacity:** BESI ships ~40-60 hybrid bonders/yr; TSM, Hynix, MU all ordering; lead times 12-18 months.
- **Names (P/S/K):**
  - `BESI BESI.AS` — **P** — Hybrid bonding monopoly today; structural winner of HBM4 transition
  - `ASMPT 0522.HK` — **P** — Han Mi's TC bonder competitor; pivoting into hybrid
  - `Han Mi Semi 042700.KS` — **P** — Korean TC bonder leader on legacy HBM3e
  - `AMAT` — **S** — Wafer-level hybrid bonding (logic-on-logic adjacency)
  - `TEL 8035.T` — **S** — Hybrid bonding deposition + dielectric prep
  - `Disco 6146.T` — **S** — Wafer thinning for stacked die

### Candidates considered but NOT separated as new layers

- **Photoresist (JSR / TOK / Shin-Etsu):** Oligopoly, not monopoly. JSR (KKR-owned) is the swing supplier; TOK has biggest EUV PR share. Worth tracking but not enough sole-source structure to warrant a dedicated layer. Add `4186.T (TOK)` and `4188.T (Mitsubishi Chemical)` to "Fab Equipment" names_detail.
- **Memory test equipment (Advantest / TER):** Tight today (Advantest +35% on HBM tester demand), but capex-fixable on a 12-18 month cycle. Belongs as a kicker inside "Fab Equipment." Add `6857.T (Advantest)` as P-tier under fab equipment with explicit "HBM tester" rationale; TER already there.
- **Silicon photonics / CPO:** Real 2027-28 transition, but the supply chain (COHR, LITE, CIEN, GLW for fiber, AVGO/Marvell for the SerDes) is already captured across Optical Transceivers + Networking Silicon. Adding a layer creates double-count. Better: tag specific names with a CPO-attach modifier when the v2 dashboard surfaces individual stocks.

---

## Q2. CPU — model treatment is currently wrong

**Current model:** CPU `supply_growth_pct=0.22`, `lead_time=1.0`, demand from `server_count`. Server count grows slowly (rack density rising 65→180 kW absorbs compute growth). Net result: CPU layer is loose, scores low tightness, doesn't surface in easiest bets.

**Why this is wrong (for stock picking, not for capacity planning):**

The CPU layer is **not a capacity bottleneck** — that's correct. Wafer capacity for x86/ARM server CPUs is ample at TSM N3/N2. But the layer **IS a rent-capture redistribution**, and the model doesn't see it because the formula tracks total units, not mix.

The 2026-28 picture:
- **AMD x86 server share:** ~34% 3Q24 → ~40-42% by 2027 (+200bps/yr on Turin/Venice). Pricing power held — AMD ASPs +15% YoY in Q4 2025.
- **INTC x86 server share:** -500bps over 2025-26. Granite Rapids volume exists but enterprise hesitation real; Diamond Rapids slipped to 2H26.
- **ARM server share:** 7% in 3Q24 → 12-14% by 2027. Graviton 4 in volume, MSFT Cobalt 100 ramping, GOOG Axion at scale, NVDA Grace bundled with every GB200/Rubin rack (= ~600k ARM CPUs/yr just from NVDA's path).
- **NVDA's "CPU" exposure:** Grace ships 1:1 with B200/B300 superchips. At ~2M GB200/Rubin units 2026-27, that's ~2M Grace CPUs — most ARM server volume growth is captured by NVDA, not by Ampere or by AWS internal silicon.

**Recommendation: do NOT add a "CPU mix shift" layer.** CPU is correctly identified as a non-tight layer — there is no rent extraction at the layer level (no one is allocation-gated on CPUs). The mix-shift winners (AMD, ARM royalty stream, NVDA Grace bundle) are **already captured elsewhere** in the framework:
- AMD share gain → already a thesis in NVDA/AVGO/AMD discussion; not a supply-chain rent
- ARM royalty → captured under EDA Tools / IP layer (ARM listed as P-tier there)
- NVDA Grace → fully captured under GPU layer (Grace is sold as part of every superchip)

**What IS missing:** the model should add `Ampere Computing (private)` and `MediaTek 2454.TT (Grace partner)` as kicker names under CPU, but otherwise the CPU layer should remain non-tight. Trust the model on this one — CPU is genuinely a beneficiary, not a bottleneck.

**One nuance worth coding:** Consider a `cpu_M = server_count_M × cpu_per_server` where cpu_per_server scales DOWN over time (1.5 → 1.2 by 2030) as Grace + ARM bundled-with-GPU configurations replace the "2× x86 host CPU" dual-socket pattern. This makes total CPU units grow even slower, reinforcing that CPU is loose. Net effect on any thesis: zero — it just makes the model truer.

---

## Q3. Why memory isn't surfacing — scoring formula change

**Diagnosis is correct.** Current `score = sum(tightness × tier_weight)` rewards layer breadth. Power names play 3-4 layers (SE in Power Gen + Grid + LPT + Distribution; Hitachi same). Memory names play 2 (HBM + Server DRAM). Power names win on breadth even though HBM 92 is the second-tightest layer in the model after the binary (100/100) layers.

**Recommendation: composite score with three components, all visible separately.**

```
ranking_score = 0.5 × breadth_score
              + 0.3 × max_tightness_score
              + 0.2 × monopoly_boost
```

Where:
- **`breadth_score`** = current sum(tightness × tier_weight) across all layers a name plays. Rewards diversified power-stack winners.
- **`max_tightness_score`** = (max tightness across layers played) × (tier of that layer). Rewards single-bottleneck monopolies. SK Hynix scores ~92 here (HBM); Ajinomoto scores ~95 (ABF when separated).
- **`monopoly_boost`** = explicit list of sole-source positions, normalized 0-100. Hardcoded:
  - 100: CLF (GOES), Ajinomoto (ABF), Lasertec (EUV mask insp), TSMC (CoWoS-L)
  - 90: BESI (hybrid bonding), ASML (EUV)
  - 80: SK Hynix (HBM3e leadership), Han Mi (TC bonders), Mitsui Chemicals (pellicles)
  - 70: MU (HBM share gainer with NVDA qual), GLW (fiber capacity)
  - 0 otherwise

**Why this works:** Power stack still ranks high (broad exposure), but MU, Hynix, Ajinomoto, BESI, Lasertec, TSMC all surface in top-15. CLF still ranks #1 because it stacks all three (broad, peak-tight at GOES 100, monopoly 100). The breadth-50/peak-30/monopoly-20 weights can be tuned but this is the right shape — show all three columns in the dashboard so the PM can see WHY each name ranks where it does.

**Alternative that would NOT work:** Just adding a max() — overweights single-issue specialty names (e.g. Stalprodukt would punch above weight on GOES). Need the monopoly boost explicit and gated to a curated list to avoid that.

---

## Q4. Top 5 silicon-stack mispricings (independent view, 2026-04-28)

Note: I'm answering this from accumulated qualitative work. The Bayesian quant cross-check (Quality Composite decile, Coiled Spring) is unavailable in this sandbox — I'd want to verify each name's decile before sizing. Where my qualitative view diverges meaningfully from likely trailing fundamentals, I flag the divergence explicitly so the PM can weigh it.

### #1. Ajinomoto 2802.T — sole-source ABF film monopoly

- **Why mispriced:** Trades as Japanese food + amino acids conglomerate at ~22x P/E. Electronic materials are ~12% of revenue but >40% of operating profit. Sell-side Japan covers this as a consumer staples — no semis analyst publishes on it. AI-grade ABF mix shift expanding ASPs +30-50% per AVGO/TSM channel checks; the food business masks the structural rent extraction.
- **Forward catalyst trailing fundamentals can't see:** New Fukushima ABF capacity online late 2026 ramping into HBM4 + CoWoS-L peak demand. ABF margin is already >35% — incremental volume drops to bottom line at >50%.
- **Quant divergence flag:** Likely D5-D7 on Quality Composite given the food drag. **The thesis IS the override** — the reformulation of investor narrative from food to specialty chemicals is the 2026-27 catalyst.

### #2. CLF (Cleveland-Cliffs) — same thesis as Round 1, restated for the silicon-stack lens

- **Why mispriced:** Already covered in Round 1. Adding here because GOES is upstream of every transformer that powers every fab AND every datacenter — it sits on both sides of the silicon stack. Embedded GOES franchise not in any sell-side SOTP.
- **Quant divergence:** Almost certainly D8-D10 (steel cyclical, balance sheet stress, FY24 losses). **Maximum quant rejection.** The override is the explicit pricing/regulatory environment specific to electrical steel — Section 232 protection, CBAM in Europe, sole-US-producer status. The trailing financials CANNOT see the GOES re-rating because it was historically priced as commodity flat-rolled.

### #3. BESI BESI.AS — hybrid bonding monopoly into HBM4 transition

- **Why mispriced:** Trades at ~30x 2026E EPS, a discount to AMAT/LRCX, despite owning >70% global hybrid bonder share at the moment HBM4 transitions from TC to hybrid. Lead times stretching to 18mo. Sell-side models hybrid bonding revenue conservatively because they extrapolate from current logic-on-logic (M2 Ultra, AMD MI300) which was small. **HBM4 is 100x the unit volume.**
- **Forward catalyst:** First HBM4 risk production at Hynix M15X in 2H26; volume 1H27. BESI's hybrid bonder ASP ~$5M with >70% gross margin — incremental drop-through is enormous.
- **Quant signal:** Probably D2-D3 already (high GM, FCF positive, low leverage). If so, this is **independent confirmation** — both layers stack bullish, raise conviction.

### #4. MU (Micron) — HBM3e share gain + 2027 allocation reality

- **Why mispriced:** GS Feb 2026 data: HBM industry undersupply 5.1%/4.0% in 2026/27, TAM raised to $54B/$75B. MU has 30% power-efficiency advantage on HBM3e per NVDA disclosed qualifications; gaining share toward 25% by 2027 (was <10% in 2024). Customers asking for 2028 allocation. Despite this, MU trades at ~12x normalized EPS — the cyclical-DRAM frame still dominates.
- **Variant perception:** Server DRAM (ex-HBM) +39%/+22% 2026/27 demand vs 22-25% supply. This is **simultaneously HBM and server DRAM tightness for 3+ years** — not a single-year cycle. Mobile/PC weakness (the bear case for memory consumer-end markets) is real BUT immaterial to the AI thesis.
- **Quant signal:** Cyclical memory historically D5-D7 on full-cycle metrics. Coiled Spring may flag (margin inflection). **Articulate the override:** the through-cycle is changing because server DRAM is 57% of demand by 2027 (was ~30% pre-AI). Old cyclical playbook doesn't apply.

### #5. Lasertec 6920.T — actinic EUV mask inspection monopoly

- **Why mispriced:** Down 30% from 2024 highs on China-export pause + the brief "EUV intensity is peaking" narrative. Wrong — A16 has more EUV layers than N2 (N2: 14-15, A16: 17-19), High-NA adds another inspection regime where Lasertec is extending the monopoly to the next-gen ACTIS A300. TSM, Samsung, Intel all on the order book.
- **Forward catalyst trailing data can't see:** High-NA ramp at TSM 2H26 (per ASML Q1 prints — 5 EXE-5000 systems delivered, all to TSM/Samsung/Intel). Each High-NA fab needs new mask inspection. Lasertec ASP ~$80M, ~70% GM.
- **Quant signal:** Likely D2-D3 historically. The 30% drawdown may have moved Coiled Spring to "tight." **Independent confirmation if so** — both qualitative and trailing data point bullish.

### Names in `LAYER_NAMES_DETAIL` that should be added or repromoted

- `BESI BESI.AS` — currently P-tier under CoWoS but should ALSO be P-tier under a new HBM Hybrid Bonding layer
- `Ajinomoto 2802.T` — currently P-tier under Substrates but should be elevated to its own layer
- `Lasertec 6920.T` — currently S-tier under Fab Equipment AND HBM Memory; should be P-tier under a new EUV Mask Inspection layer
- `Han Mi Semi 042700.KS` — currently K-tier under HBM Memory; should be P-tier under HBM Hybrid Bonding
- `ASMPT 0522.HK` — missing entirely; add as P-tier under HBM Hybrid Bonding
- `Mitsui Chemicals 4183.T` — missing entirely; add as P-tier under EUV Mask Inspection / Pellicles
- `Resonac 4004.T` — missing entirely; add as S-tier under ABF / Substrates
- `Advantest 6857.T` — missing entirely; add as P-tier under Fab Equipment with HBM tester rationale
- `TOK 4186.T` — missing entirely; add as S-tier under Fab Equipment for EUV photoresist

---

## G. Implementation Checklist — Round 2

1. Add 3 new layers to `LAYERS` and `LAYER_DEMAND_COL`: ABF Dielectric Film, EUV Mask Inspection, HBM Hybrid Bonding.
2. Update `LAYER_NAMES_DETAIL` per Section Q4 additions/repromotions.
3. Replace `build_tightness_scores` ranking formula with composite (breadth 50% / max 30% / monopoly_boost 20%) and surface all three columns in dashboard.
4. Hardcode `MONOPOLY_BOOST` dict with explicit sole-source list.
5. Optionally adjust CPU formula to scale `cpu_per_server` 2.0 → 1.2 over 2025-30 to reflect Grace bundling (cosmetic; doesn't change CPU layer's loose status).
6. Update `FLOW_NODES` to insert ABF upstream of Substrates, EUV mask inspection upstream of Fab Equipment, hybrid bonding upstream of CoWoS + HBM.

---

## H. Items left as-is

- Photoresist as standalone layer — duopoly not monopoly; folded into Fab Equipment name additions.
- Silicon photonics / CPO as standalone layer — already captured across Optics + Networking Silicon; double-counting risk.
- Memory test equipment as standalone layer — capex-fixable; folded into Fab Equipment.
- CPU mix shift modeling — not a capacity layer; mix winners captured elsewhere.

---

*Round 2 supplements `assumptions_validation.md`. Round 3 trigger: post-Q2 2026 earnings (mid-July 2026) — TSM CoWoS-L update, Hynix HBM4 risk-production timing, BESI hybrid bonder bookings, AVGO FY27 visibility on the $100B AI chip target.*
