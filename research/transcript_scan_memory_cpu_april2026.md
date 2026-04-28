---
name: Transcript Scan — Memory & CPU AI Supply Chain (April 2026)
description: Honest scoping of what could and could not be sourced from earnings call transcripts for MU/Hynix/Samsung/AMD/INTC/ARM/Lasertec/ASMPT/BESI/Ajinomoto/Advantest/IBIDEN. Includes triage plan and what the local research base DOES say.
type: project
analyst: earnings-transcript-analyst
date: 2026-04-28
status: SCOPE-CONSTRAINED — see Section 1
---

# Transcript Scan — Memory & CPU AI Supply Chain
**Date:** 2026-04-28
**Mission:** Validate (or contradict) the supply chain model's HBM/server-DRAM/CPU layer rankings using management commentary from the most recent 2–4 earnings calls per name.
**PM question:** Is memory/CPU tighter than the 22-layer model's current output suggests?

---

## 1. Tooling-state honesty notice (READ FIRST)

Both `WebSearch` and `WebFetch` were denied for this session. I was unable to retrieve a single live earnings call transcript from Motley Fool, Seeking Alpha, company IR pages, or any third-party source.

**Per the role's standing instruction — "if you can't reliably access a transcript (paywall, not yet released), say so explicitly — don't hallucinate quotes" — this scan returns ZERO verbatim management quotes for the requested companies.** The transcript-analyst memory at `W:\projects\stonelodge-backend\.claude\agent-memory\earnings-transcript-analyst\` confirms that none of MU, SK Hynix, Samsung Memory, AMD, INTC, ARM, Lasertec, ASMPT, BESI, Ajinomoto, Advantest, or IBIDEN has an established baseline in our coverage system — these are unscored names, and there is no archived first-person commentary for them in the local repo.

What follows is therefore **not** a transcript scan. It is:
1. A precise statement of which calls would need to be pulled (Section 2),
2. The supply-chain-relevant signals already documented in our local sell-side and structural research (Section 3) — these are NOT management quotes; they are paraphrased from GS notes, NVDA prepared remarks already in our archive, and the supply chain model's own assumption file,
3. A triage of which names are most likely to deliver a model-changing signal once transcripts are accessible (Section 4),
4. The action plan to make the actual scan possible (Section 5).

The PM should treat the synthesis at the end as a **scoped hypothesis list ranked by prior probability**, not as transcript-validated conclusions.

---

## 2. Calls that need to be pulled (call list)

| Company | Most-recent call | Status | Source |
|---|---|---|---|
| Micron (MU) | FQ2 FY2026 (March 2026 print) | Not accessed | fool.com/earnings/call-transcripts; investors.micron.com |
| SK Hynix (000660 KS) | Q1 2026 (late April 2026) | Not accessed | hynix.com IR; seekingalpha.com |
| Samsung Memory (005930 KS) | Q1 2026 (late April 2026) | Not accessed | samsung.com/global/ir |
| AMD | Q4 2025 (Feb 2026); Q1 2026 reports ~May 6, 2026 | Q4 not accessed; Q1 not yet released | ir.amd.com |
| Intel (INTC) | Q1 2026 (late April 2026) | Not accessed | intc.com/financial-info |
| Arm (ARM) | FQ4 FY2026 (May 2026) | Not yet released | investors.arm.com |
| Lasertec (6920 JP) | Q2 FY26 (Feb 2026); Q3 due May 2026 | Not accessed | lasertec.co.jp/en/ir |
| ASMPT (522 HK) | FY2025 (March 2026); Q1 update ~May 2026 | Not accessed | asmpacific.com/en/investor |
| BESI | Q1 2026 (late April 2026) | Not accessed | besi.com/investor-relations |
| Ajinomoto (2802 JP) | FY3/2026 full-year (early May 2026) | Not yet released | ajinomoto.co.jp/ir |
| Advantest (6857 JP) | FY3/2026 full-year (late April / early May 2026) | Not accessed | advantest.com/investors |
| IBIDEN (4062 JP) | FY3/2026 full-year (early May 2026) | Not yet released | ibiden.com/ir |

Note: Several Japanese names (Ajinomoto, IBIDEN, Advantest, ARM) report in early-to-mid May 2026 — i.e., **the most informative calls have not happened yet.** A re-run of this scan in mid-May 2026 will be materially higher-yield than today.

---

## 3. Supply-chain-relevant signals ALREADY in the local research base

These are NOT management transcript quotes. They are the structural data points already cited in `W:\projects\stonelodge-supply-chain\research\assumptions_validation.md` and in the tech-ai-sector-analyst's GS reference file. I reproduce them here so the PM can see what is already in the model versus what would need to come from new transcript work.

### 3a. HBM (sourced from GS Feb 2026 + NVDA prepared remarks already in our archive)

| Signal | Value | Source already in our archive | Implication for the model |
|---|---|---|---|
| HBM industry undersupply | 5.1% in 2026, 4.0% in 2027 | GS Feb 2026 (cited in `assumptions_validation.md` line 37) | Model uses `supply_growth 0.32`, `lead_time 1.75 yr` — consistent with the 92/100 tightness rank |
| ASIC HBM share | 33–36% | GS Feb 2026 | Risk: model may be under-counting non-NVDA HBM demand if ASIC ramp accelerates |
| HBM TAM | $54B 2026 / $75B 2027 (raised) | GS Feb 2026 | Larger absolute TAM = more revenue per point of share gain for MU |
| NVDA-quoted hardware visibility | Kress Q4 FY26 (Feb 25, 2026): "strategically secured inventory and capacity to meet demand beyond the next several quarters" | Already in `reference_management_tells.md` and session_ramp.md | This IS a verified transcript quote, but it's NVDA's, not the memory suppliers'. Implied read-through: NVDA has multi-quarter HBM commitments locked. |
| HBM bit growth | 30–35% real bit-supply growth | GS Feb 2026 | Demand growth (per content/accelerator data) running 50%+ — the 5.1% undersupply is the residual |

### 3b. Server DRAM (ex-HBM)

| Signal | Value | Source | Implication |
|---|---|---|---|
| Server DRAM demand | +39% (2026) / +22% (2027) | GS Feb 2026 (cited in `assumptions_validation.md` line 42) | Model uses `supply_growth 0.25`, lead time 1.25 yr |
| Server DRAM supply | +22–25% | GS Feb 2026 | **2026 demand–supply gap of ~14–17% is larger than HBM's 5.1% in absolute terms.** Server DRAM may be under-modeled relative to HBM. |
| Customer commitment behavior | "Customers asking 2028 allocation" | GS Feb 2026 (paraphrased in our archive) | This is a paraphrase, not a verified MU/Hynix CFO quote. Verifying it in the FQ2 MU call would be the single highest-value transcript-derived signal. |

### 3c. CPU / host processor

| Signal | Value | Source | Implication |
|---|---|---|---|
| 2025 server market unit growth | +1% YoY | GS Jan 2025 outlook + tech-ai-sector-analyst macro module | Net unit capacity ≈ flat |
| ARM server share | 1% (3Q22) → 7% (3Q24) → projected further gains via Graviton, Grace, Cobalt, Axion | GS reference doc | Model `supply_growth 0.22` for CPU/host may be too high if you read the layer as "x86 incumbents" — share is shifting to captive ARM silicon |
| AMD x86 server share gain | ~430bps/yr historic, moderating to ~200bps/yr | GS reference | CPU layer tightness depends on what counts as "supply" — ARM additions are largely captive (not on the merchant market) |
| Intel share loss | ~500bps decline expected 2025–26 | GS reference | INTC commentary on Q1 2026 call (when accessible) likely to focus on margin recovery, not unit volumes |

### 3d. AI silicon supply chain (Lasertec / ASMPT / BESI / Ajinomoto / Advantest / IBIDEN)

| Name | What we know structurally (NO transcript quote) | Source |
|---|---|---|
| Ajinomoto (2802 JP) | "Sole ABF dielectric film supplier — true monopoly" | `assumptions_validation.md` line 80 |
| BESI | "Hybrid bonding tools (CoWoS); structural winner" | `assumptions_validation.md` line 81 |
| ASMPT (522 HK) | HBM TC bonders — referenced in advanced packaging (CoWoS) layer | Implied by CoWoS lead-time bifurcation in `assumptions_validation.md` line 38 |
| Lasertec (6920 JP) | EUV pellicle / mask inspection monopoly — not directly cited in current model layers | Position is structural, but model doesn't currently isolate this layer |
| Advantest (6857 JP) | Memory test equipment — captures HBM test intensity | Implied by HBM tightness; no isolated layer in model |
| IBIDEN (4062 JP) | "AI substrate leader" — cited as 95%+ utilization on AI-grade substrate | `assumptions_validation.md` line 43 |

**Critical gap:** Of these six, only Ajinomoto, BESI, and IBIDEN appear in the model's layer definitions or names list (`names_detail`). Lasertec, ASMPT, and Advantest are mentioned in upstream constraints but are not isolated layers. **If their April-May 2026 calls signal capacity tightness, they may justify new layers.**

---

## 4. Hypothesis ranking — what the transcript scan IS LIKELY to find

These are **prior-probability rankings**, not transcript-validated findings. They're built from (a) the sell-side data already in our archive and (b) the management-tells framework from `reference_management_tells.md` applied to what we'd EXPECT to hear.

### Highest prior probability of "supply tighter than consensus"

1. **SK Hynix Q1 2026 call** — base case is Kwak Noh-Jung repeats some version of the "HBM sold out through 2026, allocating into 2027" language they've used since 2024. If the language extends into 2027 commitments (multi-year visibility), that's a model input. **Expected confidence score 8–9/10 if accessed.**

2. **Micron FQ2 FY2026 call (March 2026)** — Mehrotra/Murphy historically guide one quarter ahead with narrow ranges in HBM-tight cycles. **The single highest-value verification item: did either of them volunteer 2027 customer commitment language?** If yes → server-DRAM layer is under-modeled. The GS paraphrase ("customers asking 2028 allocation") needs a first-person source.

3. **Advantest FY3/2026 call (late April / early May 2026)** — If Advantest is guiding HBM test capacity tighter, that's a forward-looking proxy for HBM ramp velocity (test capacity is typically 6–9 months ahead of memory ship). **Highest-value INDIRECT signal in the list.**

### Medium prior probability of inflection

4. **BESI Q1 2026** — hybrid bonding tool order language. If "TC bonder bookings stretching to 2027" appears, packaging layer tightness extends.

5. **ASMPT FY2025 (March 2026)** — TC bonder commentary and OSAT customer mix. Less differentiated from BESI but adds confirmation.

6. **IBIDEN FY3/2026 (early May)** — substrate utilization; will likely repeat 95%+ utilization language. Whether they signal NEW capacity expansion vs. price discipline is the key differentiator.

### Lower prior probability of model-changing signal

7. **Samsung Memory Q1 2026** — Samsung has historically been promotional on HBM4 readiness without converting to NVDA qualification. Tone-without-substance risk.

8. **AMD Q4 2025** — server share commentary already well-reflected in consensus. Lisa Su's language tends to be precise but rarely surprises on supply.

9. **Intel Q1 2026** — INTC is in a turnaround context. **Per our turnaround CEO protocol (`reference_management_tells.md`): CEO confidence becomes a LAGGING indicator. Weight CFO Q&A 2× ahead of CEO. Watch for KPI specificity collapse and analyst question hardening.** Don't trust an upbeat Tan/Zinsner quote at face value.

10. **ARM FQ4 FY2026 (May)** — royalty rate inflection commentary; lower direct relevance to supply chain tightness modeling.

11. **Ajinomoto FY3/2026 (early May)** — semiconductor segment is small inside a food conglomerate; commentary tends to be terse. Useful for ABF pricing language but unlikely to produce QoQ shift signal.

12. **Lasertec Q3 FY26 (May)** — EUV mask inspection is genuinely monopoly-position; commentary tends to be confident-but-reserved. Watch for any change in customer concentration disclosure.

---

## 5. Action plan to convert this scoping doc into a real scan

1. **Restore web access** — either WebSearch+WebFetch permissions for this agent, or have the user paste transcript text into the conversation directly. With raw transcript text, I can run the full Confidence Score / QoQ shift / management-tells framework on each name.

2. **Re-run after May 8, 2026** — by that date, MU FQ2 (already out), Hynix Q1, Samsung Q1, AMD Q1, INTC Q1, BESI Q1, Advantest FY3/26, IBIDEN FY3/26, and Ajinomoto FY3/26 will all have been reported. Running the scan in the second week of May captures the full Q1 2026 print cycle.

3. **Build coverage baselines first** — none of these 12 names has an established baseline in our transcript-analyst memory. Per the framework, **the first call analyzed is calibration, not signal — minimum 4 quarters per name before QoQ shift detection is reliable.** First-time pull should be 3–4 calls each, not just the latest one.

4. **Priority ordering for the first real scan** (when access is restored):
   - Tier 1 (highest expected information value): SK Hynix, Micron, Advantest
   - Tier 2: BESI, ASMPT, IBIDEN
   - Tier 3: Samsung, AMD, INTC (apply turnaround protocol), Lasertec, Ajinomoto, ARM

5. **Cross-check against the assumptions_validation.md numbers** — every transcript quote that contradicts `supply_growth_pct` or `lead_time_yrs` in the model should generate an explicit model-update note.

---

## 6. Synthesis (HYPOTHESIS, not validated)

**Caveat:** none of the three "highest tightness" claims below is supported by a first-person management quote pulled in this session. They are derivatives of sell-side and structural data ALREADY in our archive — i.e., they are what the model itself is informed by. They are listed here so the PM can see WHERE the highest-probability transcript validations would land if/when the scan can actually be run.

**Q: Which 3 companies are MOST LIKELY (prior probability) to have management language saying "supply WAY tighter than consensus"?**
1. **SK Hynix** — HBM allocation through 2027 is the base case
2. **Micron** — server DRAM 2028 allocation commentary is the highest-value verification target
3. **Advantest** — HBM test capacity is the leading-edge proxy

**Q: Which 2 layers in the model are MOST LIKELY under-modeled?**
1. **Server DRAM (ex-HBM)** — current `supply_growth 0.25` may overstate available bits given the ~14–17% 2026 demand–supply gap cited in GS Feb 2026. The 92/100 tightness rank for HBM is well-supported, but server DRAM ranks lower in the model and arguably shouldn't.
2. **HBM-adjacent test/bonding capacity** — model treats CoWoS/advanced packaging as one layer with bifurcated lead time (1.0 → 1.5 yr in 2027). The TC bonder + memory test + hybrid bonding sub-stack may warrant decomposition similar to the LPT/Distribution Transformer split done for grid layers.

**Q: Single most likely mispriced memory/CPU name based on what we'd expect to find?**
- **Micron (MU).** Reason: per `capstone_competitive_map.md` (tech-ai-sector-analyst), "the HBM portion of DRAM has been re-rated from a memory commodity into an AI-accelerator-attached premium product. This is the first time in Micron's history I can credibly argue a portion of its business has compounder-like characteristics." The HBM 5.1%/4.0% undersupply combined with server DRAM 14–17% gap implies multi-year not single-cycle pricing power. **Critical:** the kill condition flagged in `capstone_kill_conditions.md` is "HBM revenue growth decelerating below 50% YoY while DRAM ASPs decline sequentially for two quarters." The transcript scan needs to verify that Mehrotra's FQ2 forward language stays well above this kill threshold.

**No supporting verbatim quote can be provided in this session.** The PM should not treat the MU mispricing call as transcript-validated — it is structural-data-validated only. The single sentence to verify in the actual MU FQ2 call is whether Mehrotra or Murphy used multi-year forward commitment language ("through 2027," "into 2028") on either HBM or server DRAM. If yes, the call is confirmed. If no, it weakens.

---

## 7. What the PM should actually do with this document

1. **Treat the structural numbers in Section 3 as already-priced into the model** (they came from the same GS notes that informed the assumptions update on 2026-04-28).
2. **Defer the "tighter than consensus" verdict** until a real transcript scan can be run — ideally mid-May 2026 once the Q1 print cycle completes.
3. **The single highest-information action this analyst can take next** is to either (a) get web access restored, or (b) receive raw transcript text from the user for MU FQ2 + Hynix Q1 + Advantest FY3/26 — those three calls would deliver ~70% of the model-updating signal at minimal additional cost.
4. **Recognize the transcript-analyst coverage gap.** None of the 12 names listed in this scan has an established baseline. Building those baselines (4 quarters of language analysis per name) is a 1–2 week investment that would unlock memory and CPU as ongoing detection targets, not just one-shot research items.

---

*Generated 2026-04-28 by earnings-transcript-analyst. Status: SCOPE-CONSTRAINED due to no web access. Next action: re-run with web access OR after May 8, 2026 when full Q1 2026 print cycle is in.*
