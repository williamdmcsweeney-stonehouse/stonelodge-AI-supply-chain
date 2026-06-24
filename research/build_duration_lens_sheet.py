"""
Build a clean 'Duration Lens' presentation sheet INSIDE
Token_and_Data_Build_Out_v4_2.xlsx: a step-by-step walkthrough (tokens -> FLOPs ->
power), the token-base vs FLOPs-lens comparison, and a chart-ready data block whose
FLOPs line is LIVE-LINKED to the 'FLOPs to Power' tab (so stress-testing there
updates this chart). Bold headers reuse an existing style (no styles.xml edit).

  python research/build_duration_lens_sheet.py

SAFETY: surgical zip edit (every other sheet's XML copied byte-for-byte; golden
hash asserted). Idempotent: inserts first run, overwrites after.
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
SHEET = "Duration Lens"
GOLDEN = "fdd0de9ef53c8247"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
WS_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"
FP = "'FLOPs to Power'"      # the live-mechanics sheet; col I = power_GW_floored, row 8 = 2025
H = 47                       # existing bold cellXf index (no fill)

esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
# Full-precision cache so cache == formula exactly (clean tie-out audit, recalc-safe).
# Coerce to NATIVE float first — repr(np.float64(x)) emits 'np.float64(x)' (invalid XML).
def fmt(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return repr(float(v))


def cs(ref, text, bold=False):
    s = f' s="{H}"' if bold else ""
    return f'<c r="{ref}"{s} t="inlineStr"><is><t>{esc(text)}</t></is></c>'


def cn(ref, val, bold=False):
    s = f' s="{H}"' if bold else ""
    return f'<c r="{ref}"{s}><v>{fmt(val)}</v></c>'


def cf(ref, formula, cache):
    return f'<c r="{ref}"><f>{esc(formula)}</f><v>{fmt(cache)}</v></c>'


def fp_row(year):           # FLOPs to Power data row for a given year
    return 8 + (year - 2025)


def build_xml():
    tok = model.build_token_demand("Base")
    mt = model.build_macro_gap(tok)                       # token basis (committed)
    mf = model.build_macro_gap(tok, use_flops_demand=True)  # FLOPs lens
    st, sf = model.gap_summary(mt), model.gap_summary(mf)

    rows = {}
    R = [0]
    def add(cells):
        R[0] += 1
        rows[R[0]] = cells
    def blank():
        R[0] += 1

    add([cs("A1", "AI POWER DEMAND  —  THE DURATION LENS", bold=True)])
    add([cs("A2", "Token base (committed headline) vs the FLOPs lens. A token's power "
                  "cost varies ~50x by model, so convert tokens -> FLOPs -> power. Live "
                  "mechanics + stress-test inputs are on the 'FLOPs to Power' tab.")])
    blank()

    add([cs("A4", "1. THE QUESTION", bold=True)])
    add([cs("A5", "How big does AI power demand get, and how long does the shortage "
                  "last? FLOPs/token = 2 x active params; that is the honest power unit "
                  "a token-count model cannot see (routing/orchestration moves it).")])
    blank()

    add([cs(f"A{R[0]+1}", "2. THE CONVERSION  (one row = one year; full live version on 'FLOPs to Power')", bold=True)])
    hdr = R[0] + 1
    add([cs(f"A{hdr}", "step", bold=True), cs(f"B{hdr}", "2025", bold=True), cs(f"C{hdr}", "2035", bold=True)])
    y0, y1 = 2025, 2035
    r0, r1 = fp_row(y0), fp_row(y1)
    def conv(label, col, v0, v1):
        r = R[0] + 1
        add([cs(f"A{r}", label),
             cf(f"B{r}", f"{FP}!{col}{r0}", v0),
             cf(f"C{r}", f"{FP}!{col}{r1}", v1)])
    # Step labels avoid a leading '=' so they are unambiguously text, never a formula.
    n0, n1 = mf.loc[y0, "avg_n_active_b"], mf.loc[y1, "avg_n_active_b"]
    conv("tokens/day (T)", "B", mf.loc[y0, "gross_tokens_T"], mf.loc[y1, "gross_tokens_T"])
    conv("x  FLOPs per token (2 x N_active)", "F", 2 * n0 * 1e9, 2 * n1 * 1e9)
    conv("->  FLOPs per day", "G", mf.loc[y0, "flops_per_day"], mf.loc[y1, "flops_per_day"])
    conv("/  chip efficiency (TFLOP per W)", "E", model.tflop_per_w_for_year(y0), model.tflop_per_w_for_year(y1))
    conv("->  power (GW)", "I", mf.loc[y0, "demand_gw"], mf.loc[y1, "demand_gw"])
    blank()

    add([cs(f"A{R[0]+1}", "3. THE TUG-OF-WAR  (why power grows ~10x, not ~176x)", bold=True)])
    add([cs(f"A{R[0]+1}", "Tokens grow ~176x to 2042. But model size N falls ~3x (routing "
                          "to smaller models) and chip TFLOP/W rises ~7x. Together they "
                          "absorb most of it, so power grows ~10x.")])
    blank()

    add([cs(f"A{R[0]+1}", "4. TOKEN BASE  vs  FLOPs LENS", bold=True)])
    cmp_hdr = R[0] + 1
    add([cs(f"A{cmp_hdr}", "metric", bold=True), cs(f"B{cmp_hdr}", "Token base", bold=True),
         cs(f"C{cmp_hdr}", "FLOPs lens", bold=True)])
    r = R[0] + 1; add([cs(f"A{r}", "Peak gap (GW)"), cn(f"B{r}", round(st["peak_gap_gw"])), cn(f"C{r}", round(sf["peak_gap_gw"]))])
    r = R[0] + 1; add([cs(f"A{r}", "Peak year"), cn(f"B{r}", st["peak_gap_year"]), cn(f"C{r}", sf["peak_gap_year"])])
    r = R[0] + 1; add([cs(f"A{r}", "Demand floor 2042 (GW)"), cn(f"B{r}", round(mt.loc[2042, "demand_gw"])),
                       cf(f"C{r}", f"ROUND({FP}!I{fp_row(2042)},0)", round(mf.loc[2042, "demand_gw"]))])
    r = R[0] + 1; add([cs(f"A{r}", "Gap closes (overshoot)"), cn(f"B{r}", st["overshoot_year"]), cn(f"C{r}", sf["overshoot_year"])])
    r = R[0] + 1; add([cs(f"A{r}", "Read"), cs(f"B{r}", "timing / peak"), cs(f"C{r}", "duration / higher floor")])
    blank()

    chart_title_row = R[0] + 1
    chart_hdr = R[0] + 2
    chart_first = R[0] + 3
    chart_last = chart_first + len(model.YEARS) - 1
    add([cs(f"A{chart_title_row}", f"5. CHART THIS  (select A{chart_hdr}:D{chart_last}, then Insert > Line Chart)", bold=True)])
    add([cs(f"A{chart_hdr}", "year", bold=True), cs(f"B{chart_hdr}", "Token demand (GW)", bold=True),
         cs(f"C{chart_hdr}", "FLOPs demand (GW)", bold=True), cs(f"D{chart_hdr}", "Supply (GW)", bold=True)])
    for yi, y in enumerate(model.YEARS):
        r = chart_first + yi
        add([cn(f"A{r}", int(y)),
             cn(f"B{r}", round(float(mt.loc[y, "demand_gw"]), 1)),
             cf(f"C{r}", f"ROUND({FP}!I{fp_row(y)},1)", round(float(mf.loc[y, "demand_gw"]), 1)),
             cn(f"D{r}", round(float(mt.loc[y, "supply_gw"]), 1))])
    blank()

    add([cs(f"A{R[0]+1}", "6. STRESS-TEST IT", bold=True)])
    add([cs(f"A{R[0]+1}", "Edit inputs on 'FLOPs to Power' (anchor, training share, N, "
                          "TFLOP/W, retirement) — the FLOPs column above and this chart's "
                          "FLOPs line update live. Broader levers on 'Macro Levers'.")])
    blank()

    add([cs(f"A{R[0]+1}", "7. THE TAKEAWAY", bold=True)])
    add([cs(f"A{R[0]+1}", "The FLOPs lens does NOT raise the peak (~278 vs 332). It raises "
                          "the FLOOR (~708 vs 549, +29%) and extends the TIGHTNESS (gap "
                          "closes ~2036 vs 2034). The power/grid/cooling case is about "
                          "DURATION, not magnitude.")])

    last = R[0]
    body = "".join(f'<row r="{n}">{"".join(rows[n])}</row>' for n in sorted(rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:D{last}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="52"/><col min="2" max="4" width="18"/></cols>'
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
