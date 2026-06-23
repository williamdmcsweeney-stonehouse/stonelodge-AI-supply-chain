"""
Write a 'FLOPs to Power' snapshot sheet INTO Token_and_Data_Build_Out_v4_2.xlsx,
so the tokens -> FLOPs -> power conversion is visible in the workbook the analyst
actually works in (next to 'Efficiency Overlay' and 'Macro Levers'). Idempotent:
inserts the sheet the first time, OVERWRITES it on later runs.

  python research/refresh_flops_sheet_in_buildout.py

SAFETY: surgical zip-level edit. Every existing sheet's XML (and its cached formula
values, which model.py reads via data_only=True) is copied byte-for-byte. Only the
FLOPs sheet part is added/replaced, plus (on first insert) the three control files.
The committed-base golden hash is asserted before the file is swapped in.

This is a STATIC snapshot of the FLOPs basis computed from model.py using the
current 'Macro Levers' tab values. Re-run after changing inputs/levers.
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
GOLDEN = "fdd0de9ef53c8247"
WS_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"
WS_RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet"

esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_rows():
    lev = {**model.load_macro_levers(), "use_flops_demand": True}  # this sheet is the FLOPs lens
    tok = model.build_token_demand(scenario="Base")
    m = model.build_macro_gap(tok, **lev)
    header = [
        ("FLOPs to Power (committed-base snapshot, FLOPs basis)", "", "", "", "", "", ""),
        ("Regenerate: python research/refresh_flops_sheet_in_buildout.py (reflects Macro Levers tab)", "", "", "", "", "", ""),
        ("year", "tokens_per_day_T", "avg_N_active_B", "FLOPs_per_token", "FLOPs_per_day", "fleet_TFLOP_per_W", "power_GW"),
    ]
    data = []
    for y in model.YEARS:
        r = m.loc[y]
        data.append((
            int(y),
            round(float(r["gross_tokens_T"]), 1),
            round(float(r["avg_n_active_b"]), 0),
            2.0 * float(r["avg_n_active_b"]) * 1e9,
            float(r["flops_per_day"]),
            round(model.tflop_per_w_for_year(y), 1),
            round(float(r["demand_gw"]), 0),
        ))
    return header, data


def cell(ref, val):
    if isinstance(val, str):
        return "" if val == "" else f'<c r="{ref}" t="inlineStr"><is><t>{esc(val)}</t></is></c>'
    return f'<c r="{ref}"><v>{("%.8g" % val)}</v></c>'


def make_sheet_xml(header, data):
    cols = "ABCDEFG"
    body, rn = [], 0
    for tup in list(header) + list(data):
        rn += 1
        cells = "".join(cell(f"{cols[i]}{rn}", v) for i, v in enumerate(tup) if v != "")
        body.append(f'<row r="{rn}">{cells}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<dimension ref="A1:G{rn}"/><sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="15"/>'
        '<cols><col min="1" max="1" width="10"/><col min="2" max="7" width="18"/></cols>'
        '<sheetData>' + "".join(body) + '</sheetData></worksheet>'
    )


def main():
    header, data = build_rows()
    sheet_xml = make_sheet_xml(header, data)

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
        edited = {"xl/workbook.xml": wb.encode(), "xl/_rels/workbook.xml.rels": rels.encode(),
                  "[Content_Types].xml": ct.encode()}
        new_parts = {part: sheet_xml.encode()}
        print("insert new sheet part:", part, "as", rid, "sheetId", sid)

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
    print(f"OK: '{SHEET_NAME}' written into {XLSX.name}; golden hash {h} intact")


if __name__ == "__main__":
    main()
