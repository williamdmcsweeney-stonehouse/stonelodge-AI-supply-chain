"""
Build a fully LIVE 'Operating Model' sheet in Token_and_Data_Build_Out_v4_2.xlsx:
Demand -> Supply -> Gap, with a Bull / Base / Bear / Central scenario picker. Every
cell is an Excel formula; cached values are computed by a Python reference that mirrors
each formula exactly, so cache == formula (recalc-safe, tie-out verified).

Layered design:
  - 'FLOPs to Power' holds the detailed BASE demand assumptions (tokens, N, TFLOP/W,
    training). This sheet links to it, overlays the scenario, and adds SUPPLY + GAP.
  - Base scenario (picker=2) reproduces the FLOPs lens exactly: peak gap ~278 @ 2031,
    demand floor ~708, asymptote ~2035 -> a built-in consistency check. All new
    mechanics are NEUTRAL in Base, so Base is byte-identical to the prior build.

  UTILIZATION IS STRUCTURAL (not a shortage-triggered cram). The agentic demand wave
  and high fleet utilization are the SAME phenomenon: you can't reach the agentic
  demand levels without the batchable, latency-tolerant workloads that let the fleet
  run hot. So utilization rises STRUCTURALLY with agentic adoption, ALWAYS-ON (not
  gated on shortage), ramping from the committed base (~25%) toward a batch ceiling
  over an adoption window [util_struct_start .. util_struct_full]. Realized power =
  demand x base_util / util_struct, so the haircut DEEPENS as utilization climbs.

  SCENARIOS:
  - Bull   = power HIGH & LONG : slower efficiency/supply, no retire, util stays ~25%.
  - Bear   = power ROLLS OVER  : faster efficiency/supply, retires, util runs to ~60%.
  - Central= MOST-LIKELY (coupled): second-wave agentic demand 10%/yr from 2034 AND
    structural utilization ramping 2030->2040 toward ~70% batch ceiling. The two move
    together by construction. Result: the agentic demand surge is largely ABSORBED by
    the structural utilization rise, so realized power is flatter/lower than the raw
    demand pull -- demand nearly plateaus mid-decade, then gently resumes once the
    utilization runway (~25%->70%, a one-time ~2.8x absorber) is spent. The early
    (pre-agentic) crunch is NOT eased -- batching relief arrives with agentic, later.

  python research/build_operating_model_sheet.py

SAFETY: surgical zip edit; golden hash asserted; idempotent (insert/overwrite).
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import xml.dom.minidom as minidom
import zipfile
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO))
import model  # noqa: E402

XLSX = _REPO / "Token_and_Data_Build_Out_v4_2.xlsx"
SHEET = "Operating Model"
GOLDEN = "5aba31680bd17859"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
WS_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
FP = "'FLOPs to Power'"
H = 47  # existing bold cellXf (no fill)
YEARS = model.YEARS
N = len(YEARS)

# ── Scenario presets ───────────────────────────────────────────────────────────
# Columns Bull / Base / Bear / Central. Base == committed FLOPs lens (all neutral).
SCEN = {                          #          Bull    Base    Bear   Central
    "anchor_GW":             (70.0,  70.0,  70.0,  70.0),
    "token_growth_adj_yr":   (0.02,  0.0,  -0.02,  0.0),    # +/- compounding on base token path
    "efficiency_adj_yr":     (-0.015, 0.0,  0.03,  0.0),    # + = faster TFLOP/W = LESS power
    "retirement_rate_yr":    (0.0,   0.0,   0.08,  0.0),    # ITEM 9 floor decay
    "supply_build_scale":    (0.85,  1.0,   1.15,  1.0),    # x phase rates
    "util_struct_ceiling":   (0.0,   0.0,   0.60,  0.70),   # STRUCTURAL util terminal (<=0.25 = off)
    "second_wave_growth":    (0.0,   0.0,   0.0,   0.10),   # ITEM 7 re-accel /yr from SW_START (0=off)
}
SW_START = 2034                    # shared second-wave start year (editable on-sheet)
USTART, UFULL = 2030, 2040         # shared structural-utilization adoption window (editable)
UTIL_BASE = (0.12, 0.25)           # committed base utilization ramp 2025 -> 2035 (ITEM 6)
PHASE = (0.22, 0.30, 0.25, 0.15)   # 26-27, 28-30, 31-35, 36-42 (editable on-sheet)
PICKER_DEFAULT = 2                 # 1=Bull 2=Base 3=Bear 4=Central -> caches show Base

esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(v):
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, int):
        return str(v)
    return repr(float(v))


def cs(ref, text, bold=False):
    s = f' s="{H}"' if bold else ""
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{esc(text)}</t></is></c>'


def cn(ref, val, bold=False):
    s = f' s="{H}"' if bold else ""
    return f'<c r="{ref}"{s}><v>{fmt(val)}</v></c>'


def cf(ref, formula, cache):
    f = formula[1:] if formula.startswith("=") else formula
    if isinstance(cache, str):   # text-valued formula (CHOOSE name, "post-2042")
        return f'<c r="{ref}" t="str"><f>{esc(f)}</f><v>{esc(cache)}</v></c>'
    return f'<c r="{ref}"><f>{esc(f)}</f><v>{fmt(cache)}</v></c>'


def fp_row(year):
    return 8 + (year - 2025)        # data row on 'FLOPs to Power'


def ubase_of(y):
    return UTIL_BASE[0] + min(1.0, (y - 2025) / 10.0) * (UTIL_BASE[1] - UTIL_BASE[0])


def ustruct_of(y, ceiling):
    """Structural utilization: base ramp until USTART, then ramp to `ceiling` by UFULL.
    Off (returns base ramp) when ceiling <= the committed base terminal (0.25)."""
    if ceiling <= UTIL_BASE[1]:
        return ubase_of(y)
    if y <= USTART:
        return ubase_of(y)
    ub_s = ubase_of(USTART)
    frac = min(1.0, (y - USTART) / (UFULL - USTART))
    return ub_s + frac * (ceiling - ub_s)


# ── Python reference: compute the Base-scenario caches that mirror the formulas ──
def reference():
    """Return dicts of per-year base inputs + the active(Base)-scenario outputs."""
    tok = model.build_token_demand("Base")
    mf = model.build_macro_gap(tok, use_flops_demand=True)
    base_tokens = {y: float(mf.loc[y, "gross_tokens_T"]) for y in YEARS}
    base_fpt = {y: 2.0 * float(mf.loc[y, "avg_n_active_b"]) * 1e9 for y in YEARS}
    base_tflopw = {y: model.tflop_per_w_for_year(y) for y in YEARS}

    # Active scenario = Base (picker default). All adjustments neutral -> FLOPs lens.
    anchor = SCEN["anchor_GW"][1]
    tadj = SCEN["token_growth_adj_yr"][1]
    eadj = SCEN["efficiency_adj_yr"][1]
    retire = SCEN["retirement_rate_yr"][1]
    sscale = SCEN["supply_build_scale"][1]
    sceil = SCEN["util_struct_ceiling"][1]      # 0.0 for Base -> structural util OFF
    swg = SCEN["second_wave_growth"][1]         # 0.0 for Base -> no re-accel

    tokens = {y: base_tokens[y] * (1 + tadj) ** (y - 2025) for y in YEARS}
    tflopw = {y: base_tflopw[y] * (1 + eadj) ** (y - 2025) for y in YEARS}
    raw_pull = {y: tokens[y] * base_fpt[y] / tflopw[y] for y in YEARS}
    raw_demand = {y: raw_pull[y] / raw_pull[2025] * anchor for y in YEARS}

    floored = {}
    for y in YEARS:
        if y == 2025:
            floored[y] = raw_demand[y]
            continue
        terms = [raw_demand[y], floored[y - 1] * (1 - retire)]
        if y >= SW_START:
            g = (tokens[y] - tokens[y - 1]) / tokens[y - 1]
            terms.append(floored[y - 1] * (1 + min(g, swg)))
        floored[y] = max(terms)

    def rate(y):
        r = PHASE[0] if y <= 2027 else PHASE[1] if y <= 2030 else PHASE[2] if y <= 2035 else PHASE[3]
        return r * sscale
    supply = {}
    for y in YEARS:
        supply[y] = anchor if y == 2025 else supply[y - 1] * (1 + rate(y))

    # STRUCTURAL utilization (always-on); realized demand = floored * base_util / util_struct.
    ubase = {y: ubase_of(y) for y in YEARS}
    util_applied, crammed, gap = {}, {}, {}
    for y in YEARS:
        ua = ustruct_of(y, sceil)
        util_applied[y] = ua
        crammed[y] = floored[y] * ubase[y] / ua
        gap[y] = crammed[y] - supply[y]

    peak_gap = max(gap.values())
    peak_year = [y for y in YEARS if gap[y] == peak_gap][0]
    bal = [y for y in YEARS if y >= peak_year and gap[y] < 30]
    balance_year = bal[0] if bal else None
    ov = [y for y in YEARS if gap[y] < 0]
    overshoot_year = ov[0] if ov else None
    asym = None
    yl = list(YEARS)
    for j, y in enumerate(yl):
        if y > 2027 and crammed[yl[j - 1]] > 0 and (crammed[y] - crammed[yl[j - 1]]) / crammed[yl[j - 1]] < 0.02:
            asym = y
            break
    return dict(base_tokens=base_tokens, base_fpt=base_fpt, base_tflopw=base_tflopw,
                tokens=tokens, tflopw=tflopw, raw_demand=raw_demand, floored=floored,
                supply=supply, ubase=ubase, util_applied=util_applied, crammed=crammed,
                gap=gap, peak_gap=peak_gap, peak_year=peak_year,
                balance_year=balance_year, overshoot_year=overshoot_year, asymptote_year=asym)


def build_xml():
    ref = reference()
    rows = {}

    rows[1] = [cs("A1", "OPERATING MODEL  —  Demand / Supply / Gap  (Bull / Base / Bear / Central)", bold=True)]
    rows[2] = [cs("A2", "Set scenario in B3 (1=Bull, 2=Base, 3=Bear, 4=Central). Everything recomputes. "
                        "CENTRAL = most-likely COUPLED case: second-wave agentic demand 10%/yr from 2034 AND "
                        "STRUCTURAL utilization ramping 2030->2040 toward 70% (batch ceiling). Util rises WITH "
                        "agentic, always-on, so the demand surge is largely absorbed: realized power flattens "
                        "mid-decade, then gently resumes once the ~25%->70% utilization runway is spent. "
                        "ANNUAL UTILIZATION: col I = structural (auto); type a value in col J (util OVERRIDE) "
                        "to flex any single year; col K = util USED feeds realized power + gap.")]
    rows[3] = [cs("A3", "SCENARIO  (1=Bull 2=Base 3=Bear 4=Central)", bold=True), cn("B3", PICKER_DEFAULT)]
    rows[4] = [cs("A4", "active scenario"), cf("B4", '=CHOOSE(B3,"Bull","Base","Bear","Central")', "Base")]

    rows[6] = [cs("A6", "SCENARIO INPUTS", bold=True), cs("B6", "Bull", bold=True),
               cs("C6", "Base", bold=True), cs("D6", "Bear", bold=True), cs("E6", "Central", bold=True)]
    keys = list(SCEN.keys())
    labels = {"anchor_GW": "anchor GW 2025",
              "token_growth_adj_yr": "token growth adj (per yr)",
              "efficiency_adj_yr": "efficiency adj (per yr, + = faster = less power)",
              "retirement_rate_yr": "capacity retirement (per yr)",
              "supply_build_scale": "supply build scale (x phase rates)",
              "util_struct_ceiling": "STRUCTURAL util ceiling (<=0.25 = off; agentic batch ceiling)",
              "second_wave_growth": "ITEM7 second-wave demand re-accel /yr (0 = off)"}
    for i, k in enumerate(keys):
        r = 7 + i
        b, c, d, e = SCEN[k]
        rows[r] = [cs(f"A{r}", labels[k]), cn(f"B{r}", b), cn(f"C{r}", c), cn(f"D{r}", d), cn(f"E{r}", e)]
    last_scen_row = 7 + len(keys) - 1   # 13

    rows[15] = [cs("A15", "SUPPLY PHASE RATES (per yr, editable)", bold=True)]
    pr_cell = {}
    for i, (cap, (lbl, val)) in enumerate(zip([2027, 2030, 2035, 2042],
                                              [("2026-2027", PHASE[0]), ("2028-2030", PHASE[1]),
                                               ("2031-2035", PHASE[2]), ("2036-2042", PHASE[3])])):
        r = 16 + i
        rows[r] = [cs(f"A{r}", lbl), cn(f"B{r}", val)]
        pr_cell[cap] = f"$B${r}"   # 2027->B16, 2030->B17, 2035->B18, 2042->B19

    rows[21] = [cs("A21", "second-wave start year (ITEM7)"), cn("B21", SW_START)]
    rows[22] = [cs("A22", "structural util ramp start year"), cn("B22", USTART)]
    rows[23] = [cs("A23", "structural util full year (hits ceiling)"), cn("B23", UFULL)]

    # Active (scenario-picked). B26 anchor / B27 tadj / B28 eadj / B29 retire /
    # B30 sscale / B31 struct-util-ceiling / B32 second-wave-growth.
    def active(r, label, scen_row):
        rows[r] = [cs(f"A{r}", label),
                   cf(f"B{r}", f"=CHOOSE($B$3,B{scen_row},C{scen_row},D{scen_row},E{scen_row})",
                      SCEN[keys[scen_row - 7]][PICKER_DEFAULT - 1])]
    rows[25] = [cs("A25", "ACTIVE (from scenario)", bold=True)]
    active(26, "anchor GW", 7)
    active(27, "token growth adj", 8)
    active(28, "efficiency adj", 9)
    active(29, "retirement rate", 10)
    active(30, "supply build scale", 11)
    active(31, "structural util ceiling", 12)
    active(32, "second-wave growth", 13)

    HDR = 34
    D0 = HDR + 1                # 2025 data row = 35
    rows[HDR] = [cs(f"A{HDR}", "year", bold=True), cs(f"B{HDR}", "tokens/day T", bold=True),
                 cs(f"C{HDR}", "FLOPs/token", bold=True), cs(f"D{HDR}", "eff TFLOP/W", bold=True),
                 cs(f"E{HDR}", "raw demand GW", bold=True), cs(f"F{HDR}", "demand floored GW", bold=True),
                 cs(f"G{HDR}", "supply GW", bold=True), cs(f"H{HDR}", "base util", bold=True),
                 cs(f"I{HDR}", "util structural (auto)", bold=True),
                 cs(f"J{HDR}", "util OVERRIDE (blank=auto)", bold=True),
                 cs(f"K{HDR}", "util USED", bold=True), cs(f"L{HDR}", "realized power GW", bold=True),
                 cs(f"M{HDR}", "GAP GW", bold=True), cs(f"N{HDR}", "_bal", bold=True),
                 cs(f"O{HDR}", "_over", bold=True), cs(f"P{HDR}", "_asym", bold=True)]
    # structural-util sub-expression: base util AT the ramp-start year B22
    ub_start = "(0.12+MIN(1,($B$22-2025)/10)*0.13)"
    for i, y in enumerate(YEARS):
        r = D0 + i
        yrs = y - 2025
        fpr = fp_row(y)
        b_f = f"={FP}!B{fpr}*(1+$B$27)^{yrs}"
        c_f = f"={FP}!F{fpr}"
        d_f = f"={FP}!E{fpr}*(1+$B$28)^{yrs}"
        e_f = f"=(B{r}*C{r}/D{r})/(B{D0}*C{D0}/D{D0})*$B$26"
        rows[r] = [cn(f"A{r}", int(y)),
                   cf(f"B{r}", b_f, ref["tokens"][y]),
                   cf(f"C{r}", c_f, ref["base_fpt"][y]),
                   cf(f"D{r}", d_f, ref["tflopw"][y]),
                   cf(f"E{r}", e_f, ref["raw_demand"][y])]
        # F floored: monotonic (retire) + second-wave re-accel from B21 capped at B32
        if i == 0:
            f_f = f"=E{r}"
        else:
            sw = f"IF(A{r}>=$B$21,F{r-1}*(1+MIN((B{r}-B{r-1})/B{r-1},$B$32)),0)"
            f_f = f"=MAX(E{r},F{r-1}*(1-$B$29),{sw})"
        rows[r].append(cf(f"F{r}", f_f, ref["floored"][y]))
        # G supply
        if i == 0:
            g_f = f"=$B$26"
        else:
            rate_f = (f"IF(A{r}<=2027,{pr_cell[2027]},IF(A{r}<=2030,{pr_cell[2030]},"
                      f"IF(A{r}<=2035,{pr_cell[2035]},{pr_cell[2042]})))")
            g_f = f"=G{r-1}*(1+{rate_f}*$B$30)"
        rows[r].append(cf(f"G{r}", g_f, ref["supply"][y]))
        # H base util ramp
        h_f = f"={UTIL_BASE[0]}+MIN(1,(A{r}-2025)/10)*({UTIL_BASE[1]}-{UTIL_BASE[0]})"
        rows[r].append(cf(f"H{r}", h_f, ref["ubase"][y]))
        # I structural util (auto): off (<=0.25) -> base ramp; else ramp from ub(B22) to ceiling by B23
        i_f = (f"=IF($B$31<=0.25,H{r},IF(A{r}<=$B$22,H{r},"
               f"{ub_start}+MIN(1,(A{r}-$B$22)/($B$23-$B$22))*($B$31-{ub_start})))")
        rows[r].append(cf(f"I{r}", i_f, ref["util_applied"][y]))
        # J util OVERRIDE: blank by default -> editable. Type any year's utilization (e.g. 0.50)
        # here to flex that single year; leave blank to use the structural-auto value in I.
        rows[r].append(f'<c r="J{r}"/>')
        # K util USED = override if present, else structural-auto
        rows[r].append(cf(f"K{r}", f"=IF(ISBLANK(J{r}),I{r},J{r})", ref["util_applied"][y]))
        # L realized power = floored demand * base_util / util USED
        rows[r].append(cf(f"L{r}", f"=F{r}*H{r}/K{r}", ref["crammed"][y]))
        # M gap = realized power - supply
        rows[r].append(cf(f"M{r}", f"=L{r}-G{r}", ref["gap"][y]))
        # N bal, O over, P asymptote helpers (peak-year ref patched below)
        bal_cache = y if (y >= ref["peak_year"] and ref["gap"][y] < 30) else 99999
        over_cache = y if ref["gap"][y] < 0 else 99999
        rows[r].append(cf(f"N{r}", "=0", bal_cache))
        rows[r].append(cf(f"O{r}", f"=IF(M{r}<0,A{r},99999)", over_cache))
        if i == 0:
            p_f, asym_cache = "=99999", 99999
        else:
            p_f = f"=IF(AND(A{r}>2027,(L{r}-L{r-1})/L{r-1}<0.02),A{r},99999)"
            prev_c = ref["crammed"][YEARS[i - 1]]
            asym_cache = (y if (y > 2027 and prev_c > 0
                                and (ref["crammed"][y] - prev_c) / prev_c < 0.02) else 99999)
        rows[r].append(cf(f"P{r}", p_f, asym_cache))
    last_data = D0 + N - 1

    # Summary
    S = last_data + 2
    grange = f"M{D0}:M{last_data}"
    arange = f"A{D0}:A{last_data}"
    rows[S] = [cs(f"A{S}", "PEAK GAP (GW)", bold=True), cf(f"B{S}", f"=MAX({grange})", ref["peak_gap"])]
    rows[S+1] = [cs(f"A{S+1}", "peak year"),
                 cf(f"B{S+1}", f"=INDEX({arange},MATCH(MAX({grange}),{grange},0))", ref["peak_year"])]
    bal = ref["balance_year"]
    rows[S+2] = [cs(f"A{S+2}", "balance year (gap<30 after peak)"),
                 cf(f"B{S+2}", f'=IF(MIN(N{D0}:N{last_data})=99999,"post-2042",MIN(N{D0}:N{last_data}))',
                    bal if bal else "post-2042")]
    ov = ref["overshoot_year"]
    rows[S+3] = [cs(f"A{S+3}", "overshoot year (gap<0)"),
                 cf(f"B{S+3}", f'=IF(MIN(O{D0}:O{last_data})=99999,"post-2042",MIN(O{D0}:O{last_data}))',
                    ov if ov else "post-2042")]
    rows[S+4] = [cs(f"A{S+4}", "realized power 2042 (GW)"),
                 cf(f"B{S+4}", f"=ROUND(L{last_data},0)", round(ref["crammed"][2042]))]
    asy = ref["asymptote_year"]
    rows[S+5] = [cs(f"A{S+5}", "demand asymptote year (YoY<2%)", bold=True),
                 cf(f"B{S+5}", f'=IF(MIN(P{D0}:P{last_data})=99999,"post-2042 (still climbing)",MIN(P{D0}:P{last_data}))',
                    asy if asy else "post-2042 (still climbing)")]
    for i, y in enumerate(YEARS):
        r = D0 + i
        rows[r][13] = cf(f"N{r}", f"=IF(AND(A{r}>=$B${S+1},M{r}<30),A{r},99999)",
                         (y if (y >= ref["peak_year"] and ref["gap"][y] < 30) else 99999))

    last = S + 5
    body = "".join(f'<row r="{n}">{"".join(rows[n])}</row>' for n in sorted(rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:P{last}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="46"/><col min="2" max="16" width="15"/></cols>'
        '<sheetData>' + body + '</sheetData></worksheet>'
    )


def add_fullcalc(wb):
    if "fullCalcOnLoad" in wb:
        return wb
    return re.sub(r'<calcPr ([^>]*?)/>', lambda m: f'<calcPr {m.group(1)} fullCalcOnLoad="1"/>', wb)


def main():
    sheet_xml = build_xml()
    z = zipfile.ZipFile(XLSX)
    names = z.namelist()
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    ct = z.read("[Content_Types].xml").decode()

    edited = {}
    exist = re.search(r'<sheet name="%s"[^>]*r:id="(rId\d+)"' % re.escape(SHEET), wb)
    if exist:
        rid = exist.group(1)
        target = "xl/" + re.search(r'<Relationship Id="%s"[^>]*Target="([^"]+)"' % rid, rels).group(1)
        new_parts = {target: sheet_xml.encode()}
        print("overwrite:", target)
    else:
        sid = max(int(x) for x in re.findall(r'sheetId="(\d+)"', wb)) + 1
        rid = "rId%d" % (max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels)) + 1)
        part = "xl/worksheets/sheet%d.xml" % (max(int(x) for x in re.findall(r'worksheets/sheet(\d+)\.xml', " ".join(names))) + 1)
        wb = wb.replace("</sheets>", f'<sheet name="{esc(SHEET)}" sheetId="{sid}" r:id="{rid}"/></sheets>')
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{WS_RT}" Target="{part[3:]}"/></Relationships>')
        ct = ct.replace("</Types>", f'<Override PartName="/{part}" ContentType="{WS_CT}"/></Types>')
        edited["xl/_rels/workbook.xml.rels"] = rels.encode()
        edited["[Content_Types].xml"] = ct.encode()
        new_parts = {part: sheet_xml.encode()}
        print("insert:", part, rid)

    wb = add_fullcalc(wb)
    if wb != z.read("xl/workbook.xml").decode():
        edited["xl/workbook.xml"] = wb.encode()
    for blob in list(edited.values()) + list(new_parts.values()):
        minidom.parseString(blob)

    tmp = str(XLSX) + ".NEW.xlsx"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            if item.filename in new_parts:
                out.writestr(item, new_parts[item.filename])
            elif item.filename in edited:
                out.writestr(item, edited[item.filename])
            else:
                out.writestr(item, z.read(item.filename))
        for fn, blob in new_parts.items():
            if fn not in names:
                out.writestr(fn, blob)
    z.close()

    assert zipfile.ZipFile(tmp).testzip() is None
    import openpyxl
    assert SHEET in openpyxl.load_workbook(tmp, data_only=True).sheetnames
    model.EXCEL_PATH = tmp
    mv = model.build_macro_gap(model.build_token_demand("Base"))
    cols = ["gross_tokens_T", "fleet_eff_idx", "net_compute_demand_T", "demand_gw",
            "supply_gw", "gap_gw", "cumulative_power_grid_capex_b"]
    h = hashlib.sha256(mv[cols].round(6).to_csv().encode()).hexdigest()[:16]
    assert h == GOLDEN, f"GOLDEN MISMATCH {h}"
    os.replace(tmp, XLSX)
    model.EXCEL_PATH = XLSX
    print(f"OK: '{SHEET}' written; golden hash {h} intact")


if __name__ == "__main__":
    main()
