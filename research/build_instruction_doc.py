"""
Generate the Word instruction document for the AI Power-Demand model:
  - how to use the Excel workbook (the four custom tabs) and the dashboard
  - a glossary of key terms
  - how the major assumptions were projected

  python research/build_instruction_doc.py  ->  research/AI_Power_Demand_Model_Guide.docx

Reproducible + version-controlled; re-run to regenerate.
"""
from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
import model  # noqa: E402

OUT = _REPO / "research" / "AI_Power_Demand_Model_Guide.docx"

INK = RGBColor(0x1A, 0x1A, 0x1A)
ACCENT = RGBColor(0x2C, 0x3E, 0x50)
MUTE = RGBColor(0x60, 0x6A, 0x78)


def _live_numbers():
    """Pull the headline figures live so the doc never drifts from the model."""
    tok = model.build_token_demand("Base")
    mt = model.build_macro_gap(tok)
    mf = model.build_macro_gap(tok, use_flops_demand=True)
    st_, sf = model.gap_summary(mt), model.gap_summary(mf)
    return {
        "tok_peak": st_["peak_gap_gw"], "tok_peak_yr": st_["peak_gap_year"],
        "tok_floor": mt.loc[2042, "demand_gw"], "tok_close": st_["overshoot_year"],
        "flops_peak": sf["peak_gap_gw"], "flops_peak_yr": sf["peak_gap_year"],
        "flops_floor": mf.loc[2042, "demand_gw"], "flops_close": sf["overshoot_year"],
        "tokens_2025": tok.loc[2025, "total_T"], "tokens_2042": tok.loc[2042, "total_T"],
        "capex": st_["cumulative_capex_2042_b"] / 1000.0,
    }


def h1(doc, text):
    p = doc.add_heading(text, level=1)
    for run in p.runs:
        run.font.color.rgb = ACCENT
    return p


def h2(doc, text):
    p = doc.add_heading(text, level=2)
    for run in p.runs:
        run.font.color.rgb = ACCENT
    return p


def para(doc, text, italic=False, size=10.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = italic
    r.font.size = Pt(size)
    r.font.color.rgb = INK
    return p


def bullet(doc, label, text):
    p = doc.add_paragraph(style="List Bullet")
    rb = p.add_run(f"{label} ")
    rb.bold = True
    rb.font.size = Pt(10.5)
    rb.font.color.rgb = INK
    rt = p.add_run(text)
    rt.font.size = Pt(10.5)
    rt.font.color.rgb = INK
    return p


def numbered(doc, text):
    p = doc.add_paragraph(style="List Number")
    r = p.add_run(text)
    r.font.size = Pt(10.5)
    r.font.color.rgb = INK
    return p


def kv_table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for i, htxt in enumerate(headers):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(htxt)
        run.bold = True
        run.font.size = Pt(9.5)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(val))
            run.font.size = Pt(9.5)
    return t


def build():
    n = _live_numbers()
    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)

    # ── Title ──
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run("AI Power-Demand Model")
    tr.bold = True
    tr.font.size = Pt(24)
    tr.font.color.rgb = ACCENT
    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sr = sub.add_run("User Guide, Key Terms, and Assumption Methodology")
    sr.font.size = Pt(13)
    sr.font.color.rgb = MUTE
    dt = doc.add_paragraph()
    dt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = dt.add_run("Peckham Capital  ·  AI Infrastructure Supply Chain  ·  June 2026")
    dr.font.size = Pt(10)
    dr.font.color.rgb = MUTE

    # ── What this is ──
    h1(doc, "1.  What this model does")
    para(doc, "This model answers two questions for the AI-infrastructure thesis: "
              "how large does data-center power demand get, and how long does the resulting "
              "supply shortage (the \"gap\") last. It starts from a forecast of AI token "
              "usage, converts those tokens into electrical power, compares that demand "
              "against the pace at which power and grid capacity can physically be built, "
              "and reports the gap year by year out to 2042.")
    para(doc, "There are two lenses on the same engine:")
    bullet(doc, "Token base (the committed headline).",
           f"Peak gap {n['tok_peak']:.0f} GW in {n['tok_peak_yr']}; the gap closes around "
           f"{n['tok_close']}. This is the locked base case.")
    bullet(doc, "FLOPs / Duration lens.",
           f"A physically honest re-derivation. It produces a slightly lower peak "
           f"({n['flops_peak']:.0f} GW in {n['flops_peak_yr']}) but a materially higher demand "
           f"floor ({n['flops_floor']:.0f} GW vs {n['tok_floor']:.0f}) and a later close "
           f"(~{n['flops_close']}). Its message is duration, not magnitude.")
    para(doc, "Both lenses live in one Excel workbook and in a Streamlit dashboard. The "
              "Excel is the place to read and stress-test; the dashboard is the place to "
              "explore interactively.", italic=True)

    # ── How to use: Excel ──
    h1(doc, "2.  How to use it — the Excel workbook")
    para(doc, "File: Token_and_Data_Build_Out_v4_2.xlsx. The original sheets (Summary, "
              "Efficiency Overlay, Base, Robo Bull, Bear) are the token-demand source data "
              "and are unchanged. Four new tabs hold the power model. Edit only the input "
              "cells; everything else is a live formula that recomputes.")

    h2(doc, "Tab: Macro Levers")
    para(doc, "The master input list for the FLOPs lens. Column B holds each value; edit "
              "it and the dashboard and the FLOPs tabs pick it up. Use this when you want "
              "one place to set the assumptions.")

    h2(doc, "Tab: FLOPs to Power")
    para(doc, "The live conversion engine. Reading left to right, each row turns one "
              "year's tokens into power:")
    numbered(doc, "tokens/day — linked live to the Efficiency Overlay sheet.")
    numbered(doc, "× FLOPs per token (= 2 × N, the active-parameter count) → FLOPs per day.")
    numbered(doc, "÷ chip efficiency (TFLOP/W) → re-anchored so 2025 = 70 GW → power.")
    para(doc, "Two power columns are shown: power_raw_GW (the pure pull, which can dip as "
              "efficiency overtakes demand) and power_GW_floored (with the \"you don't tear "
              "down a power plant\" floor). Editable inputs: anchor, retirement rate, and "
              "per-year training share, N, and TFLOP/W.")

    h2(doc, "Tab: Duration Lens")
    para(doc, "A clean, write-from summary. Seven sections: the question, the conversion "
              "with a worked 2025-vs-2035 example, the tug-of-war, a token-base-vs-FLOPs "
              "comparison, a chart-ready data block (select the block and Insert → Line "
              "Chart), where to stress-test, and the takeaway. The FLOPs line is linked "
              "live, so it tracks any change you make on FLOPs to Power.")

    h2(doc, "Tab: Operating Model  (the main stress-test surface)")
    para(doc, "The full Demand → Supply → Gap chain with a Bull / Base / Bear switch. "
              "Set the scenario in cell B3 (1 = Bull, 2 = Base, 3 = Bear) and the entire "
              "sheet recomputes. The scenario table (editable) drives five levers:")
    bullet(doc, "anchor GW —", "the 2025 starting power level.")
    bullet(doc, "token growth adjustment —", "speeds or slows the base token path.")
    bullet(doc, "efficiency adjustment —", "+ means chips improve faster, which lowers power.")
    bullet(doc, "capacity retirement —", "how fast old data centers are retired (plateau vs cliff).")
    bullet(doc, "supply build scale —", "multiplies the build-pace phase rates (slower build = bigger gap).")
    para(doc, "The summary block reports peak gap, peak year, balance year (gap < 30 GW), "
              "overshoot year (gap < 0), and the 2042 floor. The Base scenario reproduces "
              "the Duration lens exactly, so it is a built-in consistency check.")
    kv_table(doc, ["Scenario", "Peak gap", "Peak year", "Read"], [
        ["Bull", "~526 GW", "2034", "power high and long"],
        ["Base", "~278 GW", "2031", "committed FLOPs lens"],
        ["Bear", "~121 GW", "2029", "power rolls over early"],
    ])
    para(doc, "Every formula in these tabs has been verified to recompute to its displayed "
              "value, so opening the file and letting Excel recalculate changes nothing.",
         italic=True)

    # ── How to use: dashboard ──
    h1(doc, "3.  How to use it — the dashboard")
    para(doc, "Launch: run.bat (serves on port 8502). The Macro tab shows the demand / "
              "supply / gap chart and headline metrics. The sidebar expander \"FLOPs demand "
              "& retirement\" exposes the same levers as the Macro Levers Excel tab. The "
              "\"Duration Lens\" panel on the Macro tab shows the tokens → FLOPs → power "
              "conversion live and the token-vs-FLOPs comparison. The dashboard reads its "
              "defaults from the Macro Levers Excel tab, so the two stay consistent.")

    # ── Key terms ──
    h1(doc, "4.  Key terms")
    glossary = [
        ("Token", "Roughly one word of AI input or output. The model's demand driver."),
        ("Power vs energy", "Power (gigawatts, GW) is the instantaneous draw — what the grid "
            "must supply. Energy (GWh) is power over time. A 1 GW data center uses 24 GWh per "
            "day. The thesis is about GW capacity, because that is what is hard to build."),
        ("FLOP", "One floating-point operation. The actual unit of compute work."),
        ("FLOPs per token (2N)", "A token costs about 2 × N floating-point operations to "
            "generate, where N is the number of active parameters in the model. Training a "
            "model costs about 6N per token (forward + backward pass)."),
        ("N (active parameters)", "The size of the model actually doing the work. For a "
            "sparse \"mixture of experts\" model, only the activated experts count, not the "
            "full parameter total. A token's power cost varies ~50x across model sizes."),
        ("TFLOP/W (chip efficiency)", "Trillions of operations per watt — how much compute a "
            "chip delivers per unit of electricity. Rises as silicon improves (Blackwell → "
            "Rubin), assumed to go from ~9 (2025) to ~60 (2042)."),
        ("MFU", "Model FLOPs Utilization — the fraction of a chip's peak speed actually "
            "achieved (~20-50%). It cancels out in the 2025 re-anchor, so a constant MFU "
            "does not move the curve."),
        ("PUE", "Power Usage Effectiveness — facility overhead (cooling, power conversion). "
            "A PUE of 1.4 means 40% extra power on top of the chips."),
        ("Utilization", "The share of all deployed AI chips actively computing at any moment "
            "(~12%). Dividing by it scales active power up to total fleet power."),
        ("Anchor (70 GW)", "The measured total data-center power in 2025, used to calibrate "
            "the model. Everything is expressed relative to this, so the messy physics "
            "(MFU, PUE) cancels and only relative change matters."),
        ("Gap", "Demand minus supply, in GW. Positive = shortage = pricing power for power / "
            "grid / cooling suppliers. Negative = oversupply."),
        ("Peak / balance / overshoot", "Peak = largest gap. Balance = first year the gap "
            "falls below 30 GW. Overshoot = first year the gap goes negative (oversupply)."),
        ("Monotonic floor / retirement", "Whether deployed capacity is ever torn down. The "
            "floor (retirement = 0) holds demand flat once built (plateau); higher retirement "
            "lets demand decline (cliff)."),
        ("Routing / orchestration", "Sending easy queries to smaller, cheaper models. It "
            "lowers N (FLOPs per token) without changing the token count — an efficiency a "
            "token-only model cannot see, but the FLOPs lens captures."),
        ("Agentic demand", "Reasoning models and multi-agent workflows that generate many "
            "more tokens per task. This is a token-count effect (it raises power via more "
            "tokens), captured in the Excel's enterprise agent multiplier."),
        ("Duration lens", "The FLOPs view of the model. Not a higher peak, but a higher "
            "demand floor and a later gap-close — the case for a longer-lived power thesis."),
    ]
    kv_table(doc, ["Term", "Definition"], glossary)

    # ── How assumptions were projected ──
    h1(doc, "5.  How the major assumptions were projected")

    h2(doc, "Token demand")
    para(doc, f"Tokens come from the existing build-out forecast (Base sheet), driven by AI "
              f"user counts, per-user intensity, an enterprise agent multiplier, and a "
              f"robotics contribution. Gross tokens grow from about {n['tokens_2025']:.0f} "
              f"trillion per day in 2025 to roughly {n['tokens_2042']:,.0f} trillion in 2042 "
              f"(~{n['tokens_2042']/n['tokens_2025']:.0f}x). This is an S-curve: explosive "
              f"early, decelerating later as AI saturates.")

    h2(doc, "The 70 GW anchor")
    para(doc, "2025 total data-center power is anchored at 70 GW — the mid-point of public "
              "estimates (JLL, Cushman & Wakefield, Goldman Sachs, McKinsey). Calibrating to "
              "a measured number lets the model track relative change and sidestep fragile "
              "absolute physics.")

    h2(doc, "Efficiency — the two engines")
    para(doc, "Power demand is a tug-of-war: tokens push it up, efficiency pulls it down. "
              "Efficiency has two separate engines, which the FLOPs lens deliberately keeps "
              "apart:")
    bullet(doc, "Hardware (TFLOP/W).",
           "Chip performance per watt, assumed to improve ~6-7x by 2042 — an aggressive but "
           "defensible read of the Blackwell → Rubin → next roadmap.")
    bullet(doc, "Model size / routing (N).",
           "Average active parameters fall ~3x as work routes to smaller models. Combined "
           "physical efficiency is therefore ~19x by 2040.")
    para(doc, "This ~19x is the crux. The original token model implied ~122x efficiency by "
              "2040 — only reachable by also banking algorithmic gains. But algorithmic gains "
              "historically get spent on more capability and more tokens (the Jevons effect), "
              "not on lower power. For a power forecast the honest denominator is the ~19x "
              "physical figure, which is why the FLOPs lens shows a higher floor and longer "
              "tightness.")

    h2(doc, "Supply build pace")
    para(doc, "Supply starts at the 70 GW anchor and compounds at phase rates — about "
              "22%/yr (2026-27), 30% (2028-30), 25% (2031-35), 15% (2036-42) — reflecting "
              "transformer, turbine, and grid-queue lead times. Slower build widens the gap; "
              "these rates are editable on the Operating Model tab.")

    h2(doc, "What was deliberately rejected")
    para(doc, "An expert review proposed lifting the enterprise agent multiplier from ~15x "
              "to ~180x by 2040 to capture agentic demand. This was rejected as structurally "
              "impossible: a blended multiplier that high implies more than 100% of tasks are "
              "agentic. Demand was kept on the existing forecast (enterprise carries the "
              "agent multiplier; consumers do not). The realistic future upgrade is an "
              "explicit penetration × intensity model, where adoption is capped at 100%.")

    h2(doc, "Bull / Base / Bear")
    para(doc, "The three scenarios flex the same five levers in opposite directions. Bull "
              "assumes slower efficiency gains and a slower build (power stays high and long); "
              "Bear assumes faster efficiency, faster build, and some retirement (power rolls "
              "over early). Base is the committed FLOPs lens. The spread — roughly 120 to 525 "
              "GW peak gap — is the honest range of outcomes to reason about.")

    # ── Footer note ──
    h1(doc, "6.  A note on trust")
    para(doc, "Every formula in the workbook's power tabs has been independently re-evaluated "
              "and ties out to its displayed value, and the committed base case is fingerprint-"
              "locked so accidental drift is caught. The absolute GW levels are anchored "
              "estimates — trust the shape and timing (when the gap peaks, when it closes) "
              "more than any single year's exact GW. The point of the model is not a precise "
              "number; it is a defensible framework for diving into the assumptions and "
              "dimensioning the most likely outcomes.", italic=True)

    doc.save(str(OUT))
    print("Wrote", OUT)


if __name__ == "__main__":
    build()
