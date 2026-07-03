"""
Archive the FLOPs duration-lens model tabs from Token_and_Data_Build_Out_v4_2.xlsx so
the workbook is ONE model (Efficiency Overlay) + feeders + the stale-orphan tombstones.

Removes: 'Operating Model', 'Duration Lens', 'FLOPs to Power'. These are a SEPARATE
(FLOPs-basis) way to compute the same demand/supply/gap — the "other model" that should
have been consolidated. They are fully REGENERABLE:
  - FLOPs lens lives in model.py (build_macro_gap(..., use_flops_demand=True))
  - tabs regenerable via research/refresh_flops_sheet_in_buildout.py,
    research/build_operating_model_sheet.py, research/build_duration_lens_sheet.py
  - and the prior versions are in git history.
Deletion (not rename) is used because renaming would leave #REF / garbage cross-links
in the archived tabs (their token root, the Efficiency Overlay layout, has changed).

KEEPS: Efficiency Overlay (core), Base + Macro Levers (model.py reads both), and the
already-renamed ARCHIVE orphans.

  python research/archive_flops_lens_tabs.py

SAFETY: surgical zip edit; calcChain dropped (fullCalcOnLoad rebuilds it); golden hash
asserted; never openpyxl-saves.
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
GOLDEN = "c2ce9ee43f5f7c16"
DELETE = ["Operating Model", "Duration Lens", "FLOPs to Power"]


def main():
    z = zipfile.ZipFile(XLSX)
    wb = z.read("xl/workbook.xml").decode()
    rels = z.read("xl/_rels/workbook.xml.rels").decode()
    ct = z.read("[Content_Types].xml").decode()

    drop_parts = set()
    for name in DELETE:
        m = re.search(r'<sheet name="%s"[^>]*r:id="(rId\d+)"\s*/>' % re.escape(name), wb)
        if not m:
            print(f"  skip (not found): {name}")
            continue
        rid = m.group(1)
        rm = re.search(r'<Relationship Id="%s"[^>]*Target="([^"]+)"[^>]*/>' % rid, rels)
        target = "xl/" + rm.group(1)
        # strip <sheet> and <Relationship>
        wb = wb[:m.start()] + wb[m.end():]
        rels = rels[:rm.start()] + rels[rm.end():]
        # strip Content_Types override for the part
        ct = re.sub(r'<Override PartName="/%s"[^>]*/>' % re.escape(target), "", ct)
        drop_parts.add(target)
        # a worksheet may have its own _rels — drop it too
        srels = target.replace("worksheets/", "worksheets/_rels/") + ".rels"
        drop_parts.add(srels)
        print(f"  delete: {name}  ({target})")

    # calcChain references cells by sheet index; deleting sheets invalidates it.
    # Drop it (and its plumbing); fullCalcOnLoad rebuilds the chain on open.
    if "xl/calcChain.xml" in z.namelist():
        drop_parts.add("xl/calcChain.xml")
        ct = re.sub(r'<Override PartName="/xl/calcChain\.xml"[^>]*/>', "", ct)
        rels = re.sub(r'<Relationship [^>]*Target="calcChain\.xml"[^>]*/>', "", rels)
        print("  drop: xl/calcChain.xml (rebuilt on open)")

    for blob in (wb, rels, ct):
        minidom.parseString(blob)

    edited = {"xl/workbook.xml": wb.encode(),
              "xl/_rels/workbook.xml.rels": rels.encode(),
              "[Content_Types].xml": ct.encode()}

    tmp = str(XLSX) + ".NEW.xlsx"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
        for item in z.infolist():
            if item.filename in drop_parts:
                continue
            if item.filename in edited:
                out.writestr(item, edited[item.filename])
            else:
                out.writestr(item, z.read(item.filename))
    z.close()

    assert zipfile.ZipFile(tmp).testzip() is None
    import openpyxl
    names = openpyxl.load_workbook(tmp, data_only=True).sheetnames
    for d in DELETE:
        assert d not in names, f"{d} still present"
    assert "Efficiency Overlay" in names and "Base" in names and "Macro Levers" in names

    model.EXCEL_PATH = tmp
    mv = model.build_macro_gap(model.build_token_demand("Base"))
    cols = ["gross_tokens_T", "fleet_eff_idx", "net_compute_demand_T", "demand_gw",
            "supply_gw", "gap_gw", "cumulative_power_grid_capex_b"]
    h = hashlib.sha256(mv[cols].round(6).to_csv().encode()).hexdigest()[:16]
    assert h == GOLDEN, f"GOLDEN MISMATCH {h}"
    os.replace(tmp, XLSX)
    model.EXCEL_PATH = XLSX
    print(f"OK: FLOPs lens tabs archived; remaining sheets: {names}; golden hash {h} intact")


if __name__ == "__main__":
    main()
