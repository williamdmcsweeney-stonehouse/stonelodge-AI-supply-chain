"""
Write a LIVE-FORMULA 'FLOPs to Power' sheet INTO Token_and_Data_Build_Out_v4_2.xlsx.

The tokens -> FLOPs -> power conversion is pure arithmetic, so it is built as real
Excel formulas that recompute when you edit the inputs:

  tokens/day  --(linked live to the 'Efficiency Overlay' sheet)-->
  FLOPs/token = (2*(1-train) + 6*train) * N        <- 2N inference, 6N training
  FLOPs/day   = tokens/day * FLOPs/token
  power_GW    = (FLOPs/day / TFLOP/W) re-anchored so 2025 = anchor_GW

Editable inputs (yellow-ish, by convention): anchor_GW, training share per year,
avg active params N per year (encodes the routing mix), and fleet TFLOP/W per year.
NOTE: a CONSTANT inference/training split cancels in the 2025 re-anchor (same caveat
as MFU); only a split that VARIES by year bends the power curve. Likewise MFU and the
86400 s/day constant cancel, so they do not appear here.

  python research/refresh_flops_sheet_in_buildout.py

SAFETY: surgical zip-level edit. Every existing sheet's XML (and its cached formula
values, which model.py reads via data_only=True) is copied byte-for-byte. Only the
FLOPs sheet part is added/replaced (+ control files on first insert, + a calcPr
fullCalcOnLoad flag so Excel recomputes on open). The committed-base golden hash is
asserted before the file is swapped in.

Formula cells carry cached values computed from model.py, so with the defaults
(training=0) the sheet reproduces the committed FLOPs basis (70 GW -> ~708 GW).
Re-run after changing the model.
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
SHEET_NAME = "FLOPs to Power"
GOLDEN = "c2ce9ee43f5f7c16"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
WS_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"

# 'Efficiency Overlay' layout: years run across columns starting at C (2025); row 5 =
# Total Tokens/Day, row 7 = Retail Tokens/Day, row 9 = AI Users (M). The model's
# committed base bumps RETAIL to a 1400-user basis vs the sheet's 1100, so
# committed tokens/day = Total + Retail*(1400/users2025 - 1). We reference that live.
EO = "'Efficiency Overlay'"
ROW0 = 8  # first data row (2025); input cells sit above

esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
# Full-precision cache (native float; numpy->float) so downstream sheets that link
# here tie out exactly, even through catastrophic cancellation near the gap crossover.
def fmt(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    return repr(float(v))
eo_col = lambda k: chr(ord("C") + k)  # 2025->C, 2026->D, ...


def c_str(ref, text):
    return f'<c r="{ref}" t="inlineStr"><is><t>{esc(text)}</t></is></c>'


def c_num(ref, val):
    return f'<c r="{ref}"><v>{fmt(val)}</v></c>'


def c_fml(ref, formula, cache):
    # NOTE: the <f> element must NOT include a leading '=' (Excel adds it on display).
    return f'<c r="{ref}"><f>{esc(formula)}</f><v>{fmt(cache)}</v></c>'


def make_sheet_xml():
    """Build the worksheet XML (formulas + cached values that EQUAL the formulas)."""
    lev = {**model.load_macro_levers(), "use_flops_demand": True}
    tok = model.build_token_demand(scenario="Base")
    m = model.build_macro_gap(tok, **lev)
    ys = model.YEARS

    ANCHOR, RETIRE = 70.0, 0.0
    tokens = [float(m.loc[y, "gross_tokens_T"]) for y in ys]
    n_b = [float(m.loc[y, "avg_n_active_b"]) for y in ys]
    tflop = [model.tflop_per_w_for_year(y) for y in ys]
    train = [0.0 for _ in ys]                                      # default: pure inference
    fpt = [(2.0 * (1 - train[i]) + 6.0 * train[i]) * n_b[i] * 1e9 for i in range(len(ys))]
    fpd = [tokens[i] * 1e12 * fpt[i] for i in range(len(ys))]
    raw = [(fpd[i] / tflop[i]) / (fpd[0] / tflop[0]) * ANCHOR for i in range(len(ys))]  # pure pull
    floored = [raw[0]]                                             # ITEM 9 floor (cache == formula)
    for i in range(1, len(ys)):
        floored.append(max(raw[i], floored[i - 1] * (1 - RETIRE)))

    rows = {}  # row number -> list of cell xml
    rows[1] = [c_str("A1", "FLOPs to Power  ·  LIVE formulas (tokens -> FLOPs -> power)")]
    rows[2] = [c_str("A2", "Edit the inputs below; FLOPs and power recompute. Tokens are linked "
                           "live to the 'Efficiency Overlay' sheet.")]
    rows[3] = [c_str("A3", "anchor_GW_2025"), c_num("B3", ANCHOR)]
    rows[4] = [c_str("A4", "retail_uplift_to_1400_user_basis"),
               c_fml("B4", f"1400/{EO}!C9-1", 1400.0 / 1100.0 - 1.0)]
    rows[5] = [c_str("A5", "capacity_retirement_rate_per_yr (ITEM 9: 0=plateau, 1=cliff)"),
               c_num("B5", RETIRE)]
    rows[6] = [c_str("A6", "training share = 6N FLOPs/token vs 2N inference. A CONSTANT split "
                           "cancels in the re-anchor; VARY it by year to bend the power curve.")]
    rows[7] = [
        c_str("A7", "year"), c_str("B7", "tokens_day_T"), c_str("C7", "training_share"),
        c_str("D7", "avg_N_active_B"), c_str("E7", "fleet_TFLOP_per_W"),
        c_str("F7", "FLOPs_per_token"), c_str("G7", "FLOPs_per_day"),
        c_str("H7", "power_raw_GW"), c_str("I7", "power_GW_floored"),
    ]

    for i, y in enumerate(ys):
        r = ROW0 + i
        ec = eo_col(i)
        i_cell = (f"H{r}" if i == 0
                  else f"MAX(H{r},I{r-1}*(1-$B$5))")
        rows[r] = [
            c_num(f"A{r}", int(y)),
            c_fml(f"B{r}", f"{EO}!{ec}5+{EO}!{ec}7*$B$4", tokens[i]),
            c_num(f"C{r}", train[i]),
            c_num(f"D{r}", n_b[i]),
            c_num(f"E{r}", tflop[i]),
            c_fml(f"F{r}", f"(2*(1-C{r})+6*C{r})*D{r}*1000000000", fpt[i]),
            c_fml(f"G{r}", f"B{r}*1000000000000*F{r}", fpd[i]),
            c_fml(f"H{r}", f"(G{r}/E{r})/($G${ROW0}/$E${ROW0})*$B$3", raw[i]),
            c_fml(f"I{r}", i_cell, floored[i]),
        ]

    last = ROW0 + len(ys) - 1
    body = "".join(f'<row r="{n}">{"".join(rows[n])}</row>' for n in sorted(rows))
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:I{last}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="40"/><col min="2" max="9" width="17"/></cols>'
        '<sheetData>' + body + '</sheetData></worksheet>'
    )


def add_fullcalc(wb_xml: str) -> str:
    if "fullCalcOnLoad" in wb_xml:
        return wb_xml
    return re.sub(r'<calcPr ([^>]*?)/>', lambda mm: f'<calcPr {mm.group(1)} fullCalcOnLoad="1"/>', wb_xml)


def main():
    sheet_xml = make_sheet_xml()

    z = zipfile.ZipFile(XLSX)
    names = z.namelist()
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    ct = z.read("[Content_Types].xml").decode()

    edited = {}
    exist = re.search(r'<sheet name="%s"[^>]*r:id="(rId\d+)"' % re.escape(SHEET_NAME), wb)
    if exist:
        rid = exist.group(1)
        target = "xl/" + re.search(r'<Relationship Id="%s"[^>]*Target="([^"]+)"' % rid, rels).group(1)
        new_parts = {target: sheet_xml.encode()}
        print("overwrite existing sheet part:", target)
    else:
        sid = max(int(x) for x in re.findall(r'sheetId="(\d+)"', wb)) + 1
        rid = "rId%d" % (max(int(x) for x in re.findall(r'Id="rId(\d+)"', rels)) + 1)
        part = "xl/worksheets/sheet%d.xml" % (max(int(x) for x in re.findall(r'worksheets/sheet(\d+)\.xml', " ".join(names))) + 1)
        wb = wb.replace("</sheets>", f'<sheet name="{esc(SHEET_NAME)}" sheetId="{sid}" r:id="{rid}"/></sheets>')
        rels = rels.replace("</Relationships>", f'<Relationship Id="{rid}" Type="{WS_RT}" Target="{part[3:]}"/></Relationships>')
        ct = ct.replace("</Types>", f'<Override PartName="/{part}" ContentType="{WS_CT}"/></Types>')
        edited["xl/_rels/workbook.xml.rels"] = rels.encode()
        edited["[Content_Types].xml"] = ct.encode()
        new_parts = {part: sheet_xml.encode()}
        print("insert new sheet part:", part, "as", rid, "sheetId", sid)

    wb_fc = add_fullcalc(wb)            # force recalc on open so formulas refresh
    if wb_fc != z.read("xl/workbook.xml").decode():
        edited["xl/workbook.xml"] = wb_fc.encode()

    for blob in list(edited.values()) + list(new_parts.values()):
        minidom.parseString(blob)  # well-formedness gate

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

    # Verify before swapping in.
    assert zipfile.ZipFile(tmp).testzip() is None, "bad CRC"
    import openpyxl
    assert SHEET_NAME in openpyxl.load_workbook(tmp, data_only=True).sheetnames
    model.EXCEL_PATH = tmp
    mv = model.build_macro_gap(model.build_token_demand(scenario="Base"))
    cols = ["gross_tokens_T", "fleet_eff_idx", "net_compute_demand_T", "demand_gw",
            "supply_gw", "gap_gw", "cumulative_power_grid_capex_b"]
    h = hashlib.sha256(mv[cols].round(6).to_csv().encode()).hexdigest()[:16]
    assert h == GOLDEN, f"GOLDEN HASH MISMATCH {h} (input data would be broken)"
    os.replace(tmp, XLSX)
    model.EXCEL_PATH = XLSX
    print(f"OK: live-formula '{SHEET_NAME}' written into {XLSX.name}; golden hash {h} intact")


if __name__ == "__main__":
    main()
