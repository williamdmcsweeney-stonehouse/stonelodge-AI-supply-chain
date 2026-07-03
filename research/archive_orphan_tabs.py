"""
Mark the stale orphan tabs in Token_and_Data_Build_Out_v4_2.xlsx as ARCHIVE, so the
workbook reads as ONE core model (Efficiency Overlay) + feeders + a labelled FLOPs
duration lens, with the dead weight clearly flagged.

Orphans (nothing references them by formula; model.py reads only Base + Macro Levers):
  - 'Summary'    : empty (A1:A1)
  - 'Robo Bull'  : legacy 900-user Bull scenario sheet (superseded by the Operating
                   Model scenario picker)
  - 'Bear'       : legacy 900-user Bear scenario sheet (ditto)

RENAME ONLY (no delete) — fully reversible, content preserved. KEEPS: Base, Macro
Levers (model.py reads both), Efficiency Overlay (core), and the FLOPs chain
(FLOPs to Power / Operating Model / Duration Lens = the deliberate duration lens).

  python research/archive_orphan_tabs.py

SAFETY: surgical zip edit; golden hash asserted; idempotent.
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
GOLDEN = "5aba31680bd17859"
RENAMES = {
    "Summary": "ARCHIVE - Summary (empty)",
    "Robo Bull": "ARCHIVE - Robo Bull (legacy)",
    "Bear": "ARCHIVE - Bear (legacy)",
}
# Tab order after consolidation: CORE first, then feeders, then the FLOPs duration
# lens, then the archives. (Any sheet not listed keeps its relative position at the end.)
ORDER = [
    "Efficiency Overlay",                 # THE core model
    "Base", "Macro Levers",               # feeders (model.py reads both)
    "FLOPs to Power", "Duration Lens", "Operating Model",   # FLOPs duration lens
    "ARCHIVE - Summary (empty)",
    "ARCHIVE - Robo Bull (legacy)",
    "ARCHIVE - Bear (legacy)",
]


def main():
    z = zipfile.ZipFile(XLSX)
    wb = z.read("xl/workbook.xml").decode()

    changed = 0
    for old, new in RENAMES.items():
        if f'name="{new}"' in wb:
            continue  # idempotent
        m = re.search(r'(<sheet name=")%s("[^>]*/>)' % re.escape(old), wb)
        if not m:
            print(f"  skip (not found): {old}")
            continue
        wb = wb[:m.start()] + m.group(1) + new + m.group(2) + wb[m.end():]
        changed += 1
        print(f"  rename: {old!r} -> {new!r}")

    # Reorder <sheet> elements (tab order only; sheetId / r:id untouched).
    block = re.search(r"<sheets>(.*?)</sheets>", wb, re.S)
    sheets = re.findall(r"<sheet [^>]*/>", block.group(1))
    name_of = lambda s: re.search(r'name="([^"]*)"', s).group(1)
    rank = {n: i for i, n in enumerate(ORDER)}
    ordered = sorted(sheets, key=lambda s: rank.get(name_of(s), 999))
    new_block = "<sheets>" + "".join(ordered) + "</sheets>"
    if new_block != "<sheets>" + block.group(1) + "</sheets>":
        wb = wb[:block.start()] + new_block + wb[block.end():]
        changed += 1
        print("  reordered tabs: core -> feeders -> FLOPs lens -> archives")

    if changed == 0:
        print("nothing to do (already archived + ordered)")
        return

    minidom.parseString(wb)

    tmp = str(XLSX) + ".NEW.xlsx"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            if item.filename == "xl/workbook.xml":
                out.writestr(item, wb.encode())
            else:
                out.writestr(item, z.read(item.filename))
    z.close()

    assert zipfile.ZipFile(tmp).testzip() is None
    import openpyxl
    names = openpyxl.load_workbook(tmp, data_only=True).sheetnames
    assert "Base" in names and "Macro Levers" in names and "Efficiency Overlay" in names

    # Golden-hash safety net (renamed sheets aren't read by model.py).
    model.EXCEL_PATH = tmp
    mv = model.build_macro_gap(model.build_token_demand("Base"))
    cols = ["gross_tokens_T", "fleet_eff_idx", "net_compute_demand_T", "demand_gw",
            "supply_gw", "gap_gw", "cumulative_power_grid_capex_b"]
    h = hashlib.sha256(mv[cols].round(6).to_csv().encode()).hexdigest()[:16]
    assert h == GOLDEN, f"GOLDEN MISMATCH {h}"
    os.replace(tmp, XLSX)
    model.EXCEL_PATH = XLSX
    print(f"OK: {changed} orphan tab(s) archived; golden hash {h} intact")


if __name__ == "__main__":
    main()
