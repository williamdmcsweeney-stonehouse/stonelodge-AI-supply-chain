"""
Build a fully LIVE 'Operating Model' sheet in Token_and_Data_Build_Out_v4_2.xlsx:
Demand -> Supply -> Gap, with a Bull / Base / Bear scenario picker. Every cell is an
Excel formula; cached values are computed by a Python reference that mirrors each
formula exactly, so cache == formula (recalc-safe, tie-out verified).

Layered design:
  - 'FLOPs to Power' holds the detailed BASE demand assumptions (tokens, N, TFLOP/W,
    training) and already flexes. This sheet links to it for the base per-year inputs,
    then overlays SCENARIO adjustments (token growth, efficiency pace, retirement,
    supply build pace, ITEM 10 shortage utilization) and adds SUPPLY and GAP.
  - Base scenario (picker=2) reproduces the FLOPs lens exactly: peak gap ~278 @ 2031,
    demand floor ~708, gap closes ~2036 -> a built-in consistency check. ITEM 10 is
    OFF in Bull+Base (ceiling 0) so Base is byte-identical to the prior build.

  ITEM 10 (shortage-responsive utilization / endogenous market clearing): in any year
  with a RAW shortage (floored demand > supply), average fleet utilization is crammed
  from the base 12%->25% ramp up to the scenario ceiling (Bear=0.40), and the power
  needed to serve the same demand falls as base_util/util_applied. Bear models "the
  fleet just gets used harder" — the single biggest bull-for-supply / bear-for-trade
  lever. Latency caps the ceiling (response time ~ 1/(1-util)): ~40% is cheap for
  interactive inference, ~50%+ needs a batch/agentic-heavy mix.

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
GOLDEN = "fdd0de9ef53c8247"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
WS_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
FP = "'FLOPs to Power'"
H = 47  # existing bold cellXf (no fill)
YEARS = model.YEARS
N = len(YEARS)

# ── Scenario presets ───────────────────────────────────────────────────────────
# Columns Bull / Base / Bear. Base == committed FLOPs lens (all adjustments neutral).
# Bull = power HIGH & LONG: efficiency improves slower, supply builds slower, no
#        retire, NO cramming (util stays on the base ramp -> demand stays high).
# Bear = power ROLLS OVER: efficiency faster, supply faster, capacity retires, AND
#        the fleet is crammed to 40% in shortage years (ITEM 10) -> gap collapses.
SCEN = {                       #              Bull    Base    Bear
    "anchor_GW":            (70.0,  70.0,  70.0),
    "token_growth_adj_yr":  (0.02,  0.0,  -0.02),   # +/- compounding on base token path
    "efficiency_adj_yr":    (-0.015, 0.0,  0.03),   # + = faster TFLOP/W gain = LESS power
    "retirement_rate_yr":   (0.0,   0.0,   0.08),   # ITEM 9 floor decay
    "supply_build_scale":   (0.85,  1.0,   1.15),   # x phase rates (slower build = bigger gap)
    "util_shortage_ceiling": (0.0,  0.0,   0.40),   # ITEM 10: 0 = off; >0 crams fleet in shortage yrs
}
UTIL_BASE = (0.12, 0.25)           # committed base utilization ramp 2025 -> 2035 (ITEM 6)
PHASE = (0.22, 0.30, 0.25, 0.15)   # 26-27, 28-30, 31-35, 36-42 (editable on-sheet)
PICKER_DEFAULT = 2                 # 1=Bull 2=Base 3=Bear -> caches show Base

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


# ── Python reference: compute the Base-scenario caches that mirror the formulas ──
def reference():
    """Return dicts of per-year base inputs + the active(Base)-scenario outputs."""
    # Mirror EXACTLY what 'FLOPs to Power' caches (committed FLOPs lens): FLOPs/token =
    # 2 x N_active (training share 0 there), and N from the committed _avg_n_active_b.
    tok = model.build_token_demand("Base")
    mf = model.build_macro_gap(tok, use_flops_demand=True)
    base_tokens = {y: float(mf.loc[y, "gross_tokens_T"]) for y in YEARS}
    base_fpt = {y: 2.0 * float(mf.loc[y, "avg_n_active_b"]) * 1e9 for y in YEARS}
    base_tflopw = {y: model.tflop_per_w_for_year(y) for y in YEARS}

    # Active scenario = Base (picker default). Adjustments all neutral -> reproduces FLOPs lens.
    anchor = SCEN["anchor_GW"][1]
    tadj = SCEN["token_growth_adj_yr"][1]
    eadj = SCEN["efficiency_adj_yr"][1]
    retire = SCEN["retirement_rate_yr"][1]
    sscale = SCEN["supply_build_scale"][1]
    ceiling = SCEN["util_shortage_ceiling"][1]      # ITEM 10: 0.0 for Base -> no cram

    tokens = {y: base_tokens[y] * (1 + tadj) ** (y - 2025) for y in YEARS}
    tflopw = {y: base_tflopw[y] * (1 + eadj) ** (y - 2025) for y in YEARS}
    raw_pull = {y: tokens[y] * base_fpt[y] / tflopw[y] for y in YEARS}
    raw_demand = {y: raw_pull[y] / raw_pull[2025] * anchor for y in YEARS}
    floored = {}
    for y in YEARS:
        floored[y] = raw_demand[y] if y == 2025 else max(raw_demand[y], floored[y - 1] * (1 - retire))

    def rate(y):
        r = PHASE[0] if y <= 2027 else PHASE[1] if y <= 2030 else PHASE[2] if y <= 2035 else PHASE[3]
        return r * sscale
    supply = {}
    for y in YEARS:
        supply[y] = anchor if y == 2025 else supply[y - 1] * (1 + rate(y))

    # ITEM 10: crank utilization in raw-shortage years, haircut demand by base/applied.
    ubase = {y: ubase_of(y) for y in YEARS}
    util_applied, crammed, gap = {}, {}, {}
    for y in YEARS:
        raw_gap = floored[y] - supply[y]
        ua = max(ubase[y], ceiling) if (ceiling > 0 and raw_gap > 0) else ubase[y]
        util_applied[y] = ua
        crammed[y] = floored[y] * ubase[y] / ua
        gap[y] = crammed[y] - supply[y]

    peak_gap = max(gap.values())
    peak_year = [y for y in YEARS if gap[y] == peak_gap][0]
    bal = [y for y in YEARS if y >= peak_year and gap[y] < 30]
    balance_year = bal[0] if bal else None
    ov = [y for y in YEARS if gap[y] < 0]
    overshoot_year = ov[0] if ov else None
    return dict(base_tokens=base_tokens, base_fpt=base_fpt, base_tflopw=base_tflopw,
                tokens=tokens, tflopw=tflopw, raw_demand=raw_demand, floored=floored,
                supply=supply, ubase=ubase, util_applied=util_applied, crammed=crammed,
                gap=gap, peak_gap=peak_gap, peak_year=peak_year,
                balance_year=balance_year, overshoot_year=overshoot_year)


def build_xml():
    ref = reference()
    rows = {}

    # Header / instructions
    rows[1] = [cs("A1", "OPERATING MODEL  —  Demand / Supply / Gap  (Bull / Base / Bear)", bold=True)]
    rows[2] = [cs("A2", "Set scenario in B3 (1=Bull, 2=Base, 3=Bear). Everything recomputes. "
                        "Base inputs (tokens, N, TFLOP/W, training) live on 'FLOPs to Power'; "
                        "this sheet overlays the scenario and adds supply + gap. ITEM 10: a "
                        "shortage utilization ceiling (Bear=40%) crams the fleet in short years.")]
    rows[3] = [cs("A3", "SCENARIO  (1=Bull  2=Base  3=Bear)", bold=True), cn("B3", PICKER_DEFAULT)]
    rows[4] = [cs("A4", "active scenario"), cf("B4", '=CHOOSE(B3,"Bull","Base","Bear")', "Base")]

    # Scenario input table (Bull col B, Base col C, Bear col D)
    rows[6] = [cs("A6", "SCENARIO INPUTS", bold=True), cs("B6", "Bull", bold=True),
               cs("C6", "Base", bold=True), cs("D6", "Bear", bold=True)]
    keys = list(SCEN.keys())
    labels = {"anchor_GW": "anchor GW 2025",
              "token_growth_adj_yr": "token growth adj (per yr)",
              "efficiency_adj_yr": "efficiency adj (per yr, + = faster = less power)",
              "retirement_rate_yr": "capacity retirement (per yr)",
              "supply_build_scale": "supply build scale (x phase rates)",
              "util_shortage_ceiling": "shortage util ceiling (ITEM 10; 0 = off)"}
    for i, k in enumerate(keys):
        r = 7 + i
        b, c, d = SCEN[k]
        rows[r] = [cs(f"A{r}", labels[k]), cn(f"B{r}", b), cn(f"C{r}", c), cn(f"D{r}", d)]
    last_scen_row = 7 + len(keys) - 1   # 12

    # Editable supply phase rates (shared; scaled by the active supply_build_scale)
    rows[14] = [cs("A14", "SUPPLY PHASE RATES (per yr, editable)", bold=True)]
    pr_cell = {}
    for i, (cap, (lbl, val)) in enumerate(zip([2027, 2030, 2035, 2042],
                                              [("2026-2027", PHASE[0]), ("2028-2030", PHASE[1]),
                                               ("2031-2035", PHASE[2]), ("2036-2042", PHASE[3])])):
        r = 15 + i
        rows[r] = [cs(f"A{r}", lbl), cn(f"B{r}", val)]
        pr_cell[cap] = f"$B${r}"   # 2027->B15, 2030->B16, 2035->B17, 2042->B18

    # Active (scenario-picked) inputs.  B21 anchor / B22 tadj / B23 eadj / B24 retire /
    # B25 sscale / B26 util ceiling.
    def active(r, label, scen_row):
        rows[r] = [cs(f"A{r}", label),
                   cf(f"B{r}", f"=CHOOSE($B$3,B{scen_row},C{scen_row},D{scen_row})",
                      SCEN[keys[scen_row - 7]][PICKER_DEFAULT - 1])]
    rows[20] = [cs("A20", "ACTIVE (from scenario)", bold=True)]
    active(21, "anchor GW", 7)
    active(22, "token growth adj", 8)
    active(23, "efficiency adj", 9)
    active(24, "retirement rate", 10)
    active(25, "supply build scale", 11)
    active(26, "shortage util ceiling", 12)

    # Per-year engine
    HDR = 29
    D0 = HDR + 1                # 2025 data row = 30
    rows[HDR] = [cs(f"A{HDR}", "year", bold=True), cs(f"B{HDR}", "tokens/day T", bold=True),
                 cs(f"C{HDR}", "FLOPs/token", bold=True), cs(f"D{HDR}", "eff TFLOP/W", bold=True),
                 cs(f"E{HDR}", "raw demand GW", bold=True), cs(f"F{HDR}", "demand floored GW", bold=True),
                 cs(f"G{HDR}", "supply GW", bold=True), cs(f"H{HDR}", "base util", bold=True),
                 cs(f"I{HDR}", "util applied", bold=True), cs(f"J{HDR}", "demand crammed GW", bold=True),
                 cs(f"K{HDR}", "GAP GW", bold=True), cs(f"L{HDR}", "_bal", bold=True),
                 cs(f"M{HDR}", "_over", bold=True)]
    for i, y in enumerate(YEARS):
        r = D0 + i
        yrs = y - 2025
        fpr = fp_row(y)
        # B tokens = FLOPs!B * (1+tadj)^yrs ; C fpt = FLOPs!F ; D tflopw = FLOPs!E * (1+eadj)^yrs
        b_f = f"={FP}!B{fpr}*(1+$B$22)^{yrs}"
        c_f = f"={FP}!F{fpr}"
        d_f = f"={FP}!E{fpr}*(1+$B$23)^{yrs}"
        # E raw demand = (B*C/D) / (B$D0*C$D0/D$D0) * anchor
        e_f = f"=(B{r}*C{r}/D{r})/(B{D0}*C{D0}/D{D0})*$B$21"
        rows[r] = [cn(f"A{r}", int(y)),
                   cf(f"B{r}", b_f, ref["tokens"][y]),
                   cf(f"C{r}", c_f, ref["base_fpt"][y]),
                   cf(f"D{r}", d_f, ref["tflopw"][y]),
                   cf(f"E{r}", e_f, ref["raw_demand"][y])]
        # F floored
        if i == 0:
            f_f = f"=E{r}"
        else:
            f_f = f"=MAX(E{r},F{r-1}*(1-$B$24))"
        rows[r].append(cf(f"F{r}", f_f, ref["floored"][y]))
        # G supply
        if i == 0:
            g_f = f"=$B$21"
        else:
            rate_f = (f"IF(A{r}<=2027,{pr_cell[2027]},IF(A{r}<=2030,{pr_cell[2030]},"
                      f"IF(A{r}<=2035,{pr_cell[2035]},{pr_cell[2042]})))")
            g_f = f"=G{r-1}*(1+{rate_f}*$B$25)"
        rows[r].append(cf(f"G{r}", g_f, ref["supply"][y]))
        # H base util ramp = 0.12 + MIN(1,(yr-2025)/10)*(0.25-0.12)
        h_f = f"={UTIL_BASE[0]}+MIN(1,(A{r}-2025)/10)*({UTIL_BASE[1]}-{UTIL_BASE[0]})"
        rows[r].append(cf(f"H{r}", h_f, ref["ubase"][y]))
        # I util applied = IF(ceiling>0 AND raw shortage, MAX(base, ceiling), base)
        i_f = f"=IF(AND($B$26>0,F{r}-G{r}>0),MAX(H{r},$B$26),H{r})"
        rows[r].append(cf(f"I{r}", i_f, ref["util_applied"][y]))
        # J crammed demand = F * base_util / util_applied
        rows[r].append(cf(f"J{r}", f"=F{r}*H{r}/I{r}", ref["crammed"][y]))
        # K gap = crammed - supply
        rows[r].append(cf(f"K{r}", f"=J{r}-G{r}", ref["gap"][y]))
        # L bal candidate, M over candidate (helpers for summary; peak-year ref patched below)
        bal_cache = y if (y >= ref["peak_year"] and ref["gap"][y] < 30) else 99999
        over_cache = y if ref["gap"][y] < 0 else 99999
        rows[r].append(cf(f"L{r}", "=0", bal_cache))      # patched below to real peak-year cell
        rows[r].append(cf(f"M{r}", f"=IF(K{r}<0,A{r},99999)", over_cache))
    last_data = D0 + N - 1

    # Summary
    S = last_data + 2          # peak gap row
    grange = f"K{D0}:K{last_data}"
    arange = f"A{D0}:A{last_data}"
    rows[S] = [cs(f"A{S}", "PEAK GAP (GW)", bold=True), cf(f"B{S}", f"=MAX({grange})", ref["peak_gap"])]
    rows[S+1] = [cs(f"A{S+1}", "peak year"),
                 cf(f"B{S+1}", f"=INDEX({arange},MATCH(MAX({grange}),{grange},0))", ref["peak_year"])]
    bal = ref["balance_year"]
    rows[S+2] = [cs(f"A{S+2}", "balance year (gap<30 after peak)"),
                 cf(f"B{S+2}", f'=IF(MIN(L{D0}:L{last_data})=99999,"post-2042",MIN(L{D0}:L{last_data}))',
                    bal if bal else "post-2042")]
    ov = ref["overshoot_year"]
    rows[S+3] = [cs(f"A{S+3}", "overshoot year (gap<0)"),
                 cf(f"B{S+3}", f'=IF(MIN(M{D0}:M{last_data})=99999,"post-2042",MIN(M{D0}:M{last_data}))',
                    ov if ov else "post-2042")]
    rows[S+4] = [cs(f"A{S+4}", "demand floor 2042 (GW)"),
                 cf(f"B{S+4}", f"=ROUND(F{last_data},0)", round(ref["floored"][2042]))]
    # Patch the balance helper L to reference the real peak-year cell B{S+1}.
    for i, y in enumerate(YEARS):
        r = D0 + i
        rows[r][11] = cf(f"L{r}", f"=IF(AND(A{r}>=$B${S+1},K{r}<30),A{r},99999)",
                         (y if (y >= ref["peak_year"] and ref["gap"][y] < 30) else 99999))

    last = S + 4
    body = "".join(f'<row r="{n}">{"".join(rows[n])}</row>' for n in sorted(rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:M{last}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="40"/><col min="2" max="13" width="15"/></cols>'
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
