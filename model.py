"""
AI Infrastructure Supply Chain Model — Stonehouse Capital Management

Translates token demand into supply chain bottleneck signals across every
layer of the AI infrastructure stack, from silicon design to grid power.

Calibration anchor: ~30 GW total hyperscaler AI infrastructure in 2025.
"""

from __future__ import annotations  # PEP 604 / PEP 585 compatibility on Python 3.9+

import os
import numpy as np
import pandas as pd
from pathlib import Path
# openpyxl is lazy-imported inside load_excel_scenario so this module loads
# even in environments where openpyxl install has hiccupped (Streamlit Cloud
# has occasionally failed to satisfy the wheel — module-level imports here
# would surface as a redacted ImportError on the cloud entrypoint).

# Excel input — prefer v4_2 (with Efficiency Overlay sheet) in this repo;
# fall back to the legacy file in stonelodge-backend if v4_2 not present.
_REPO_ROOT = Path(__file__).parent
_BACKEND_ROOT = Path(
    os.environ.get("STONEHOUSE_BACKEND", "")
    or _REPO_ROOT.parent / "stonelodge-backend"
)
_LEGACY_EXCEL = (
    _BACKEND_ROOT
    / "data/research/Technology and AI Analyst"
    / "AI Edge and Robotics/Token and Data Build Out.xlsx"
)
_V4_EXCEL = _REPO_ROOT / "Token_and_Data_Build_Out_v4_2.xlsx"
EXCEL_PATH = _V4_EXCEL if _V4_EXCEL.exists() else _LEGACY_EXCEL

YEARS = list(range(2025, 2043))


# ── Supply chain layer registry ───────────────────────────────────────────────
# demand_driver:
#   "inference"   — scales with cloud tokens/day (inference load)
#   "compute"     — scales with total compute GW deployed
#   "capex"       — scales with new capacity additions (YoY delta of compute)
#   "server"      — scales with server unit count
#   "networking"  — scales with networking ports
#   "optics"      — scales with optical port count

LAYERS = {
    # ── Power / Energy ────────────────────────────────────────────────────────
    "Power Generation": {
        "unit": "GW", "color": "#e74c3c",
        "names": ["GEV", "CEG", "VST", "TLN", "SE", "MHI 7011.T", "Hitachi 6501.T", "NRG", "AES", "DUK", "SO"],
        "lead_time_yrs": 8.0, "supply_growth_pct": 0.04,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "Utility-scale power for AI data centers. Supply growth 4% per industrials desk (was 7%) — GEV +59% orders are demand, not supply",
    },
    "Grid Interconnect Queue": {
        "unit": "GW queued", "color": "#7d3c98",
        "names": ["GEV", "SE", "Hitachi 6501.T", "PWR", "MYRG", "CEG", "TLN", "AEP", "EXC", "DUK", "VST", "ABB"],
        "lead_time_yrs": 6.0, "supply_growth_pct": 0.05,
        "demand_driver": "capex", "demand_scale": 1.3,
        "description": "PJM 8+ year queue, ERCOT 2,000+ requests. Distinct from generation — having a turbine ≠ being able to plug in. Behind-the-meter nuclear (CEG/TLN) is the partial bypass",
    },
    "GOES (Electrical Steel)": {
        "unit": "kt", "color": "#641e16",
        "names": ["CLF", "POSCO 005490.KS", "JFE 5411.T", "Nippon Steel 5401.T", "Stalprodukt", "ThyssenKrupp", "Baoshan"],
        "lead_time_yrs": 4.0, "supply_growth_pct": 0.03,
        "demand_driver": "compute", "demand_scale": 0.6,
        "description": "Grain-oriented electrical steel — single US producer (CLF Butler PA, Zanesville OH). Physics-limited expansion. Upstream of every transformer. Mispriced as commodity steel",
    },
    "Large Power Transformers (LPT)": {
        "unit": "GW-equiv", "color": "#c0392b",
        "names": ["Hitachi 6501.T", "GEV (Prolec)", "SE", "HUBB", "ABB", "SPXC", "WEG", "POWL"],
        "lead_time_yrs": 3.5, "supply_growth_pct": 0.08,
        "demand_driver": "compute", "demand_scale": 0.7,
        "description": "Large power transformers + GSUs. Lead times 100-210 weeks (worsened from 128). Hitachi VA online 2028, SE Charlotte 2027. WoodMac deficit 30%→5% by 2030",
    },
    "Distribution Transformers": {
        "unit": "GW-equiv", "color": "#922b21",
        "names": ["ETN", "NVT", "HUBB", "ABB", "Schneider", "Legrand", "POWL", "ATKR"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.18,
        "demand_driver": "compute", "demand_scale": 0.4,
        "description": "Distribution-class transformers. Capacity catching up; supply expansion ~10-14%/yr per industrials channel checks",
    },
    "UPS / Backup Power": {
        "unit": "GW-equiv", "color": "#e67e22",
        "names": ["ETN", "VRT", "Schneider", "GNRC", "CMI", "CAT", "Kohler", "Delta 2308.TT"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.20,
        "demand_driver": "compute", "demand_scale": 0.9,
        "description": "Uninterruptible power + emergency backup generation. Some 48V direct-DC architecture cannibalization",
    },
    "Liquid Cooling": {
        "unit": "GW-thermal", "color": "#d35400",
        "names": ["VRT", "MOD", "Nidec 6594.T", "Boyd (ETN)", "Munters", "SPXC", "Asetek", "EMR", "JCI", "TT"],
        "lead_time_yrs": 0.75, "supply_growth_pct": 0.55,
        "demand_driver": "compute", "demand_scale": 0.8,
        "description": "Mandatory above 35 kW/rack; B200/GB200 builds 100% liquid by physics. Supply growth raised to 55% (VRT 2025 actuals +60% YoY in liquid)",
    },
    "Skilled Electrical Labor": {
        "unit": "M FTE", "color": "#5d4037",
        "names": ["MYRG", "PWR", "EME", "FIX", "IESC", "APG", "MTZ", "DY", "PRIM"],
        "lead_time_yrs": 4.5, "supply_growth_pct": 0.04,
        "demand_driver": "capex", "demand_scale": 1.1,
        "description": "MSFT President called it #1 problem March 2026; 4-5yr apprenticeship; no capex fix. Likely the LAST binding constraint to clear",
    },

    # ── Silicon / Compute ─────────────────────────────────────────────────────
    "GPU / AI Accelerators": {
        "unit": "EFLOP/s", "color": "#8e44ad",
        "names": ["NVDA", "AVGO (XPU)", "GOOG (TPU)", "AMZN (Trainium)", "AMD", "MRVL", "ALAB", "Cerebras"],
        "lead_time_yrs": 1.25, "supply_growth_pct": 0.45,
        "demand_driver": "inference", "demand_scale": 1.0,
        "description": "Primary AI compute. NVDA dominant; custom ASICs (AVGO TPU/Anthropic, AMZN Trainium 3) gaining share. Supply growth normalizing to 45% (was 55%)",
    },
    "HBM Memory": {
        "unit": "TB total", "color": "#9b59b6",
        "names": ["SK Hynix 000660.KS", "MU", "Samsung 005930.KS", "Lasertec 6920.T", "Disco 6146.T", "TEL 8035.T", "Han Mi Semi"],
        "lead_time_yrs": 1.75, "supply_growth_pct": 0.32,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "GS Feb 2026: industry undersupply 5.1%/4.0% in 2026/27, TAM $54B/$75B, ASIC HBM share 33-36%. Real bit-supply growth 30-35%",
    },
    "CoWoS / Advanced Packaging": {
        "unit": "kwspm", "color": "#1abc9c",
        "names": ["TSM", "ASE 3711.TT", "AMKR", "INTC IFS", "BESI", "ONTO", "Disco 6146.T", "TEL 8035.T"],
        "lead_time_yrs": 1.5, "supply_growth_pct": 0.32,
        "demand_driver": "capex", "demand_scale": 1.2,
        "description": "TSMC CoWoS-L: 80→130k WPM end-26 (+62%). Easing 2H26 then HBM4 retightens 2027. BESI hybrid bonding tools = structural winner",
    },
    "Fab Equipment": {
        "unit": "WFE $B", "color": "#2980b9",
        "names": ["AMAT", "LRCX", "KLAC", "ASML", "TEL 8035.T", "TER", "ENTG", "MKSI", "AEHR", "Lasertec"],
        "lead_time_yrs": 1.5, "supply_growth_pct": 0.11,
        "demand_driver": "capex", "demand_scale": 1.5,
        "description": "GS WFE: $98B 2024 → $109B 2026 = ~11% over 2yr. Supply growth recalibrated DOWN from 20% — fab equip is CapEx-driven, not unit-driven",
    },
    "EDA Tools / IP": {
        "unit": "design starts", "color": "#16a085",
        "names": ["SNPS", "CDNS", "ARM", "Siemens EDA", "ALAB", "Rambus RMBS", "CEVA"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.14,
        "demand_driver": "capex", "demand_scale": 0.6,
        "description": "Custom-silicon wave (AVGO $21B Anthropic, TPU v7, Trainium 3, OpenAI 2027) drives design starts. Duopoly with pricing power. Demand 20%+ vs supply 14%",
    },
    "CPU / Host Processors": {
        "unit": "M units", "color": "#27ae60",
        "names": ["AMD (EPYC)", "INTC", "ARM", "AMZN (Graviton)", "MSFT (Cobalt)", "GOOG (Axion)", "Ampere", "AAPL (M-series)"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.22,
        "demand_driver": "server", "demand_scale": 1.0,
        "description": "x86 server +1% units 2025; ARM +600bps share to 7%; AMD +200bps/yr; INTC -500bps over 2025-26",
    },
    "Server DRAM": {
        "unit": "TB total", "color": "#2ecc71",
        "names": ["SK Hynix 000660.KS", "MU", "Samsung 005930.KS", "Nanya 2408.TT", "Winbond 2344.TT"],
        "lead_time_yrs": 1.25, "supply_growth_pct": 0.25,
        "demand_driver": "server", "demand_scale": 1.0,
        "description": "GS Feb 2026: server DRAM (ex-HBM) +39%/+22% 2026/27 demand vs 22-25% supply. Customers asking for 2028 allocation — multi-year shortage",
    },
    "Advanced Substrates / PCB": {
        "unit": "M units", "color": "#f1c40f",
        "names": ["IBIDEN 4062.T", "Unimicron 3037.TT", "TTM", "AT&S", "Shinko 6967.T", "SEMCO 009150.KS"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.20,
        "demand_driver": "capex", "demand_scale": 0.8,
        "description": "AI substrate suppliers at 95%+ utilization. ABF supply broken out as separate sole-source layer (Ajinomoto monopoly)",
    },
    "ABF Dielectric Film": {
        "unit": "M wafers", "color": "#a04000",
        "names": ["Ajinomoto 2802.T", "Sekisui Chemical 4204.T", "Mitsui Chemicals 4183.T"],
        "lead_time_yrs": 4.0, "supply_growth_pct": 0.06,
        "demand_driver": "capex", "demand_scale": 0.4,
        "description": "Sole-source by Ajinomoto (ABF). Every advanced AI/CPU substrate uses ABF film. Fukushima capacity hits HBM4/CoWoS-L peak demand 2026-27. Trades as food/staples — true monopoly mispriced",
    },
    "HBM Hybrid Bonding": {
        "unit": "tools/yr", "color": "#76448a",
        "names": ["BESI", "ASMPT 0522.HK", "Han Mi Semi 042700.KS", "AMAT", "TEL 8035.T"],
        "lead_time_yrs": 2.0, "supply_growth_pct": 0.18,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "HBM3e uses TC bonders (Han Mi/ASMPT). HBM4 ramping 2H26-1H27 transitions bottom 4 dies to hybrid bonding (BESI/AMAT/TEL) — 4x equipment intensity per die. Step change not captured in HBM bit-supply metric",
    },
    "EUV Mask Inspection / Pellicles": {
        "unit": "tools/yr", "color": "#1f618d",
        "names": ["Lasertec 6920.T", "Mitsui Chemicals 4183.T", "ASML"],
        "lead_time_yrs": 3.0, "supply_growth_pct": 0.10,
        "demand_driver": "capex", "demand_scale": 0.3,
        "description": "Lasertec actinic EUV mask inspection monopoly. A16 has more EUV layers than N2; High-NA extends monopoly through ACTIS A300. Trades -30% from 2024 highs on stale EUV-peaking narrative",
    },

    # ── Networking ────────────────────────────────────────────────────────────
    "Scale-Out Networking Silicon": {
        "unit": "Tb/s ports", "color": "#3498db",
        "names": ["AVGO", "MRVL", "NVDA (Mellanox)", "ANET", "CSCO (Silicon One)", "HPE (Juniper)", "ALAB", "CRDO", "MTSI"],
        "lead_time_yrs": 0.75, "supply_growth_pct": 0.45,
        "demand_driver": "networking", "demand_scale": 1.0,
        "description": "AVGO Tomahawk 6 (102.4T) volume; Tomahawk 7 in dev; ANET silicon attach +50% in 2025. NVDA Mellanox/Spectrum ~$15B/yr (cross-tier). HPE+Juniper closed Jan 2025 — Mist AI + cloud networking ~40% of HPE",
    },
    "Co-Packaged Optics (CPO)": {
        "unit": "M optical lanes", "color": "#48c9b0",
        "names": ["AVGO", "MRVL", "NVDA", "TSM", "ASE 3711.TT", "COHR", "LITE", "INTC IFS"],
        "lead_time_yrs": 1.5, "supply_growth_pct": 0.25,
        "demand_driver": "networking", "demand_scale": 1.6,
        "description": "Architectural step-change from pluggable transceivers to optics integrated onto switch ASIC package — first volume 2027-28 (TH6+CPO, NVDA Quantum/Spectrum-X CPO). Switch-silicon owners (AVGO, MRVL, NVDA) capture optics value + advanced packaging (TSM SoIC, ASE 2.5D) becomes structurally critical. Supply ramp gated by packaging capacity, not transceiver assembly",
    },
    "DPU / SmartNICs": {
        "unit": "M units", "color": "#5dade2",
        "names": ["NVDA (BlueField)", "AMD (Pensando)", "INTC (IPU)", "MRVL (OCTEON)", "AVGO", "ALAB"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.35,
        "demand_driver": "server", "demand_scale": 1.4,
        "description": "DPU per AI server for east-west networking offload + storage acceleration. NVDA BlueField-3 dominant; AMD Pensando in cloud (AZR), Intel IPU (Google E2000). 1 DPU per AI server today → 2-4 per rack at 800G+. Currently lumped into GPU revenue for NVDA — structurally separate",
    },
    "Optical Transceivers": {
        "unit": "M ports", "color": "#e74c3c",
        "names": ["COHR", "LITE", "CIEN", "FN", "MTSI", "AAOI", "MXL", "POET", "CRDO",
                  "Innolight 300308.SZ", "Eoptolink 300502.SZ", "Accelink 002281.SZ", "Hisense Broadband"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.35,
        "demand_driver": "optics", "demand_scale": 1.0,
        "description": "800G fully ramping; 1.6T early 2026; CPO transition (2027-28). COHR/LITE plus Chinese majors (Innolight ~25%, Eoptolink ~15%) supply most global AI optics. MaxLinear (MXL) PAM4 DSP/CDR exposure. ADRs not directly tradeable for Chinese names — watch only for share-shift signals",
    },
    "Fiber / Physical Cabling": {
        "unit": "km M", "color": "#7f8c8d",
        "names": ["GLW", "Prysmian", "CommScope", "BDC", "Furukawa 5801.T", "Sumitomo 5802.T", "Fujikura 5803.T"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.30,
        "demand_driver": "optics", "demand_scale": 0.8,
        "description": "Corning capacity-constrained 2024-26; Prysmian/CommScope at ceiling; MTP/MPO connector chokepoint",
    },
    "High-Speed Connectors": {
        "unit": "M units", "color": "#95a5a6",
        "names": ["APH", "TE Connectivity", "Molex", "MOG.A", "Bel Fuse", "Hirose 6806.T", "JAE 6807.T"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.35,
        "demand_driver": "server", "demand_scale": 1.2,
        "description": "APH 2025 +28% organic; demand +40%+ given rack-density. Amphenol has 40%+ share in PCIe 5.0/6.0 connectors",
    },
    "Active Electrical Cables (AEC)": {
        "unit": "M units", "color": "#a9cce3",
        "names": ["CRDO", "AVGO", "MRVL", "MTSI", "APH", "Molex"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.50,
        "demand_driver": "server", "demand_scale": 1.5,
        "description": "AEC replaces passive copper above 400G/lane and competes with short-reach optics inside rack. CRDO ~80% share — 2025 +245%. Margin pool growing as rack density rises and copper hits Shannon limit at 224G PAM4",
    },

    # ── Physical Infrastructure ────────────────────────────────────────────────
    "Data Center Construction": {
        "unit": "GW capacity adds", "color": "#bdc3c7",
        "names": ["PWR", "MYRG", "FIX", "EME", "APG", "MTZ", "DY", "PRIM", "Turner"],
        "lead_time_yrs": 2.0, "supply_growth_pct": 0.12,
        "demand_driver": "capex", "demand_scale": 1.0,
        "description": "Specialty contractor labor capacity grows 5-8%/yr; PWR $44B / FIX $12.5B record backlogs reflect demand not supply",
    },
    "DC REITs / Co-lo": {
        "unit": "MW leased", "color": "#ecf0f1",
        "names": ["EQIX", "DLR", "IRM", "AMT", "IREN", "CORZ", "APLD", "NEXTDC", "Keppel DC"],
        "lead_time_yrs": 3.0, "supply_growth_pct": 0.10,
        "demand_driver": "compute", "demand_scale": 0.5,
        "description": "New supply land+power-gated, not capital-gated; PJM queue determines supply. 30-48mo for net-new wholesale",
    },

    # ── Grid Buildout Pipeline (T12-T14, colleague Round 4) ───────────────────
    "Line Hardware & HVDC Cable": {
        "unit": "M units", "color": "#5b2c6f",
        "names": ["PLPC", "HUBB", "TEL", "Prysmian", "Nexans", "NKT", "Southwire"],
        "lead_time_yrs": 2.5, "supply_growth_pct": 0.09,
        "demand_driver": "capex", "demand_scale": 0.7,
        "description": "Pole-line hardware (PLPC) + HVDC subsea/long-haul cables (NKT, Prysmian). HVDC cable order books extend through 2030; PLPC sole-source on certain hardware specs. Distinct from transformers — connects them",
    },
    "Steel Poles & Towers": {
        "unit": "kt fabricated", "color": "#7b241c",
        "names": ["VMI", "ACA", "TRN", "NUE", "STLD", "Sabre"],
        "lead_time_yrs": 2.0, "supply_growth_pct": 0.07,
        "demand_driver": "capex", "demand_scale": 0.6,
        "description": "Tubular steel poles + lattice transmission towers. VMI/ACA effective duopoly on engineered transmission structures. Lead time 60-100 weeks; transmission buildout drives volume",
    },
    "Galvanizing": {
        "unit": "kt coated", "color": "#641e16",
        "names": ["AZZ", "VMI"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.05,
        "demand_driver": "capex", "demand_scale": 0.5,
        "description": "Hot-dip galvanizing for transmission structures. AZZ ~40% North American share (largest pure-play); VMI vertically integrated. Required corrosion protection for any outdoor steel. Quiet duopoly mispriced as cyclical",
    },
    "Defense Adjacent": {
        "unit": "$B revenue", "color": "#1a5276",
        "names": ["GHM", "ESE", "ATMU", "IPGP", "BWXT", "HII", "GD", "CW", "TDG", "HEI"],
        "lead_time_yrs": 3.0, "supply_growth_pct": 0.08,
        "demand_driver": "capex", "demand_scale": 0.4,
        "description": "AI-driven geopolitical demand: turbine air filtration (ATMU), vacuum/EW systems (GHM), DC test/utility (ESE), naval nuclear (BWXT/HII), high-power lasers (IPGP). Compute buildout + reshoring overlap; not yet priced as AI play",
    },
}


def load_excel_scenario(sheet_name: str) -> pd.DataFrame:
    """
    Load a scenario sheet. Keeps first occurrence of duplicate row labels
    (prevents mix-% rows from overwriting the token-count rows).
    """
    import openpyxl  # lazy import — see top-of-file note

    wb = openpyxl.load_workbook(str(EXCEL_PATH), data_only=True)
    ws = wb[sheet_name]

    header_row = None
    rows_list = []

    for row in ws.iter_rows(values_only=True):
        if row[0] is None and row[1] == 2025:
            header_row = list(row)
            continue
        if header_row is None:
            continue
        if row[0] is not None:
            label = str(row[0]).strip()
            values = {}
            for i, year in enumerate(header_row):
                if isinstance(year, int) and 2025 <= year <= 2042:
                    values[year] = row[i] if row[i] is not None else 0.0
            if values:
                rows_list.append((label, values))

    # First occurrence wins — avoids mix% rows overwriting token rows
    seen = set()
    data = {}
    for label, values in rows_list:
        if label not in seen:
            seen.add(label)
            data[label] = values

    return pd.DataFrame(data).T


def build_token_demand(
    scenario: str = "Base",
    ai_users_2025_M: float = 1100,
    agent_multiplier_scale: float = 1.0,
    humanoid_units_scale: float = 1.0,
    enterprise_intensity_scale: float = 1.0,
    edge_fraction_2025: float = 0.20,
    edge_fraction_2040: float = 0.65,
) -> pd.DataFrame:
    """
    Build the token demand curve from Excel + user overrides.
    Returns DataFrame indexed by year with columns:
        retail_T, enterprise_T, robotics_cloud_T, robotics_edge_T,
        total_cloud_T, total_T  (all in Trillions tokens/day)
    """
    df = load_excel_scenario(scenario)

    # AI user scale factor vs base
    try:
        base_users_2025 = float(df.loc["AI Users (M's)", 2025])
    except Exception:
        base_users_2025 = 1100.0
    user_scale = ai_users_2025_M / base_users_2025

    rows = []
    for year in YEARS:
        try:
            retail = float(df.loc["Retail", year]) * user_scale * enterprise_intensity_scale
        except Exception:
            retail = 0.0

        try:
            ent_raw = float(df.loc["Enterprise Used Per Day (T)", year])
            base_agent = float(df.loc["Agent Multiplier", year])
            enterprise = ent_raw * agent_multiplier_scale * enterprise_intensity_scale
        except Exception:
            enterprise = 0.0

        try:
            robotics_total = float(df.loc["Usage per day (token) (T's)", year])
            robotics_total *= (1.0 + (humanoid_units_scale - 1.0) * 0.4)
        except Exception:
            robotics_total = 0.0

        t = min(1.0, (year - 2025) / (2040 - 2025))
        edge_frac = edge_fraction_2025 + t * (edge_fraction_2040 - edge_fraction_2025)
        robotics_cloud = robotics_total * (1.0 - edge_frac)
        robotics_edge = robotics_total * edge_frac

        total_cloud = retail + enterprise + robotics_cloud

        rows.append({
            "year": year,
            "retail_T": max(0.0, retail),
            "enterprise_T": max(0.0, enterprise),
            "robotics_cloud_T": max(0.0, robotics_cloud),
            "robotics_edge_T": max(0.0, robotics_edge),
            "total_cloud_T": max(0.0, total_cloud),
            "total_T": max(0.0, retail + enterprise + robotics_total),
        })

    return pd.DataFrame(rows).set_index("year")


# ── MACRO GAP FRAMEWORK ───────────────────────────────────────────────────────
# Implements the "Efficiency Overlay" framework from Token_and_Data_Build_Out_v4_2
# (colleague's sheet, sourced and cited). Operates at the AGGREGATE GW level —
# global DC operational capacity, demand vs supply, and the resulting gap.
#
# This is the headline thesis output. Layer-level tightness scoring (the existing
# build_infrastructure_demand_vintaged + build_tightness_scores) provides the
# granular drilldown beneath this aggregate view.
#
# Sources (per Excel rows 52-61):
# [1] Epoch AI 2024 — hardware efficiency doubling ~2 yr
# [3] Hyperscaler GPU refresh 4-5yr; enterprise 7-8yr → fleet lag = 6 yr midpoint
# [4][5][6] Cushman & Wakefield — US 40.6 / EMEA 10.3 / APAC 12.2 = 63 GW base
# [7] JLL 2026 Global DC Outlook — 200 GW by 2030 forecast
# [9] JLL — $11.3M/MW shell+core construction cost
# [10] JLL — AI workload share 25% (2025) → 50% (2030); $15M/MW AI fit-out
#
# Macro gap scenarios (per Excel rows 64-67):
#   Bear (fast efficiency):    doubling=1.5, lag=4, gap closes ~2032
#   Base (empirical):          doubling=2.0, lag=6, gap persists through 2034+
#   Bull (physics slowdown):   doubling=3.0, lag=8, gap never closes through 2042
#   Infrastructure-only:       supply phase rates 0.15/0.20/0.20/0.12

MACRO_SCENARIOS = {
    "Base — empirical (Stonehouse)": {
        "doubling": 2.0, "lag": 6,
        "supply_rates": (0.22, 0.30, 0.25, 0.15),
        "note": "Gap persists through 2034+. No air pocket for power names. Default.",
    },
    "Bear — fast efficiency": {
        "doubling": 1.5, "lag": 4,
        "supply_rates": (0.22, 0.30, 0.25, 0.15),
        "note": "Gap closes ~2032. Air-pocket risk for silicon names; power names fade earlier.",
    },
    "Bull — physics slowdown": {
        "doubling": 3.0, "lag": 8,
        "supply_rates": (0.22, 0.30, 0.25, 0.15),
        "note": "Gap never closes through 2042. All tiers critical, durable rent capture.",
    },
    "Infrastructure-only (slow build)": {
        "doubling": 2.0, "lag": 6,
        "supply_rates": (0.15, 0.20, 0.20, 0.12),
        "note": "Models realistic physical build pace. Gap even larger; peak ~2031-32.",
    },
}


def build_macro_gap(
    token_df: pd.DataFrame,
    anchor_gw_2025: float = 66.0,                        # Cushman & Wakefield total DC capacity
    efficiency_doubling_years: float = 2.0,              # Epoch AI [1]
    fleet_lag_years: int = 6,                            # 4-5yr hyperscaler + 7-8yr enterprise = 6 [3]
    supply_phase_rates: tuple = (0.22, 0.30, 0.25, 0.15),  # 26-27, 28-30, 31-35, 36-42
    cost_shell_per_mw_M: float = 11.3,                   # JLL [9]
    cost_ai_fitout_per_mw_M: float = 15.0,               # JLL [10]
    ai_workload_share: float = 0.50,                     # AI share of new builds (50% by 2030)
    power_grid_share: float = 0.25,                      # Power & grid share of total DC capex
) -> pd.DataFrame:
    """Aggregate demand vs supply gap framework (colleague's Efficiency Overlay).

    Returns DataFrame indexed by year with columns:
      gross_tokens_T              — gross token demand from Excel
      new_eff_idx                 — frontier (newest GPU) efficiency index, 2025=1.0
      fleet_eff_idx               — fleet-weighted efficiency: replace 1/lag of fleet/yr
      compute_per_token_idx       — 1 / fleet_eff_idx
      net_compute_demand_T        — gross × compute_per_token_idx (monotonic non-decreasing)
      demand_gw                   — net compute demand × (anchor / 2025 gross tokens)
      supply_gw                   — anchor compounded at phase rates
      incremental_supply_gw       — YoY supply addition
      gap_gw                      — demand - supply (positive = undersupplied)
      gap_pct                     — gap / demand
      annual_total_capex_b        — $B total DC capex from incremental supply
      annual_power_grid_capex_b   — power & grid share (25%)
      cumulative_power_grid_capex_b — running total
    """
    cost_per_mw_blended_M = cost_shell_per_mw_M + cost_ai_fitout_per_mw_M * ai_workload_share

    rows: list[dict] = []
    fleet_eff_prev = 1.0
    net_demand_prev = 0.0
    supply_prev = anchor_gw_2025
    cumulative_power_capex = 0.0

    for year in YEARS:
        yrs = year - 2025

        # 1. Frontier efficiency (newest GPU generation)
        new_eff_idx = 2.0 ** (yrs / efficiency_doubling_years)

        # 2. Fleet-weighted efficiency: each year, 1/lag of fleet replaced by frontier
        if year == 2025:
            fleet_eff_idx = 1.0
        else:
            fleet_eff_idx = (1 - 1.0 / fleet_lag_years) * fleet_eff_prev + (1.0 / fleet_lag_years) * new_eff_idx
        fleet_eff_prev = fleet_eff_idx

        compute_per_token_idx = 1.0 / fleet_eff_idx

        # 3. Demand
        gross_tokens_T = float(token_df.loc[year, "total_T"])
        net_compute_demand_T = gross_tokens_T * compute_per_token_idx
        # Monotonic: deployed fleet doesn't get torn down even if efficiency improves
        net_compute_demand_T = max(net_compute_demand_T, net_demand_prev)
        net_demand_prev = net_compute_demand_T

        # Convert to GW using 2025 anchor ratio (66 GW per 124.3 T tokens/day)
        anchor_ratio = anchor_gw_2025 / float(token_df.loc[2025, "total_T"])
        demand_gw = net_compute_demand_T * anchor_ratio

        # 4. Supply (phase-rate compounding)
        if year == 2025:
            supply_gw = anchor_gw_2025
        else:
            if year <= 2027:
                rate = supply_phase_rates[0]
            elif year <= 2030:
                rate = supply_phase_rates[1]
            elif year <= 2035:
                rate = supply_phase_rates[2]
            else:
                rate = supply_phase_rates[3]
            supply_gw = supply_prev * (1.0 + rate)
        incremental_supply_gw = supply_gw - supply_prev if year > 2025 else 0.0
        supply_prev = supply_gw

        # 5. Gap
        gap_gw = demand_gw - supply_gw
        gap_pct = gap_gw / demand_gw if demand_gw > 0 else 0.0

        # 6. Capex (flows from supply additions, in $B)
        # incremental_supply_gw × 1000 MW/GW × $cost/MW (in $M) / 1000 → $B
        annual_total_capex_b = incremental_supply_gw * 1000.0 * cost_per_mw_blended_M / 1000.0
        annual_power_grid_capex_b = annual_total_capex_b * power_grid_share
        cumulative_power_capex += annual_power_grid_capex_b

        rows.append({
            "year": year,
            "gross_tokens_T": gross_tokens_T,
            "new_eff_idx": new_eff_idx,
            "fleet_eff_idx": fleet_eff_idx,
            "compute_per_token_idx": compute_per_token_idx,
            "net_compute_demand_T": net_compute_demand_T,
            "demand_gw": demand_gw,
            "supply_gw": supply_gw,
            "incremental_supply_gw": incremental_supply_gw,
            "gap_gw": gap_gw,
            "gap_pct": gap_pct,
            "annual_total_capex_b": annual_total_capex_b,
            "annual_power_grid_capex_b": annual_power_grid_capex_b,
            "cumulative_power_grid_capex_b": cumulative_power_capex,
        })

    return pd.DataFrame(rows).set_index("year")


def gap_summary(macro_df: pd.DataFrame) -> dict:
    """Summarize the macro gap for headline metrics."""
    peak_gap_year = int(macro_df["gap_gw"].idxmax())
    peak_gap_gw = float(macro_df["gap_gw"].max())
    peak_gap_pct = float(macro_df.loc[peak_gap_year, "gap_pct"])

    # Balance year — first year after peak where gap < 30 GW (or hits negative)
    balance_year = None
    for y in macro_df.index:
        if y < peak_gap_year:
            continue
        if macro_df.loc[y, "gap_gw"] < 30:
            balance_year = int(y)
            break

    # Overshoot year — first year gap goes negative
    overshoot_year = None
    for y in macro_df.index:
        if macro_df.loc[y, "gap_gw"] < 0:
            overshoot_year = int(y)
            break

    return {
        "peak_gap_gw": peak_gap_gw,
        "peak_gap_year": peak_gap_year,
        "peak_gap_pct": peak_gap_pct,
        "balance_year": balance_year,
        "overshoot_year": overshoot_year,
        "cumulative_capex_2042_b": float(macro_df.loc[2042, "cumulative_power_grid_capex_b"]),
    }


def tflop_per_w_for_year(year: int) -> float:
    """
    Share-weighted fleet TFLOP/W ramping by GPU generation.
    H100=5.65, H200=7.0, B200=9.0, GB200=~15, Rubin VR200=25-30.
    Annualized arch cadence post-Blackwell collapses doubling to ~2 yr.
    """
    points = {2025: 9.0, 2026: 11.0, 2027: 14.0, 2028: 18.0, 2030: 25.0, 2035: 40.0, 2042: 60.0}
    yrs = sorted(points)
    if year <= yrs[0]:
        return points[yrs[0]]
    if year >= yrs[-1]:
        return points[yrs[-1]]
    for i in range(len(yrs) - 1):
        if yrs[i] <= year <= yrs[i + 1]:
            t = (year - yrs[i]) / (yrs[i + 1] - yrs[i])
            return points[yrs[i]] + t * (points[yrs[i + 1]] - points[yrs[i]])
    return 9.0


def server_kw_for_year(year: int) -> float:
    """
    Average kW per AI server (rack-blended). GB200 NVL72 = 132 kW/rack.
    Rubin VR200 NVL144 (Kyber vertical) approaches 600 kW/rack-assembly.
    Ramp reflects shift from 8× HGX (16 kW) to rack-scale (NVL36/NVL72/NVL144).
    """
    points = {2025: 65.0, 2026: 90.0, 2027: 120.0, 2028: 150.0, 2030: 180.0, 2035: 240.0, 2042: 320.0}
    yrs = sorted(points)
    if year <= yrs[0]:
        return points[yrs[0]]
    if year >= yrs[-1]:
        return points[yrs[-1]]
    for i in range(len(yrs) - 1):
        if yrs[i] <= year <= yrs[i + 1]:
            t = (year - yrs[i]) / (yrs[i + 1] - yrs[i])
            return points[yrs[i]] + t * (points[yrs[i + 1]] - points[yrs[i]])
    return 65.0


def build_infrastructure_demand(
    token_df: pd.DataFrame,
    # Calibration anchors — see research/assumptions_validation.md
    # Default = "high-conviction only" package: efficiency doubling 2.5→2.0 (the one
    # change with strongest evidence per tech-ai-sector-analyst). Other agent-recommended
    # changes (7M tokens/kWh, 12% utilization, 38 GW anchor) compound to break the 30 GW
    # 2025 anchor calibration. Surface those as preset scenarios in the v2 dashboard.
    tokens_per_kwh_2025: float = 3_600_000,            # H100-blended fleet baseline
    efficiency_doubling_years: float = 2.0,            # post-Blackwell cadence (was 2.5) — HIGH CONVICTION
    inference_utilization_2025: float = 0.067,         # 30 GW 2025 anchor calibration
    inference_utilization_2035: float = 0.18,
    pue_2025: float = 1.40,
    pue_2040: float = 1.15,
    hbm_gb_per_tflop: float = 1.38,
    ports_per_mw: float = 11_000,
    server_kw_override: float | None = None,           # if None, ramps via server_kw_for_year
    tflop_per_w_override: float | None = None,         # if None, ramps via tflop_per_w_for_year
    dram_tb_per_server: float = 1.0,
) -> pd.DataFrame:
    """Translate token demand into infrastructure demand by layer."""
    rows = []

    for year in YEARS:
        yrs = year - 2025
        cloud_tokens = token_df.loc[year, "total_cloud_T"]

        # ── Efficiency ────────────────────────────────────────────────────────
        efficiency = tokens_per_kwh_2025 * (2 ** (yrs / efficiency_doubling_years))

        # ── Active inference power ─────────────────────────────────────────────
        kwh_per_day = (cloud_tokens * 1e12) / efficiency
        inference_mw = kwh_per_day / 24_000

        # ── Total deployed compute (inference ÷ utilization) ──────────────────
        t_util = min(1.0, yrs / (2035 - 2025))
        util = inference_utilization_2025 + t_util * (
            inference_utilization_2035 - inference_utilization_2025
        )
        total_compute_mw = inference_mw / util

        # ── YoY compute additions (capex driver) ──────────────────────────────
        if year == 2025:
            compute_delta_mw = total_compute_mw * 0.35  # assume ~35% new in 2025
        else:
            prev_compute = rows[-1]["total_compute_gw"] * 1000 if rows else 0
            compute_delta_mw = max(0, total_compute_mw - prev_compute)

        # ── PUE ───────────────────────────────────────────────────────────────
        t_pue = min(1.0, yrs / (2040 - 2025))
        pue = pue_2025 + t_pue * (pue_2040 - pue_2025)
        cooling_mw = total_compute_mw * (pue - 1.0)
        power_total_gw = (total_compute_mw + cooling_mw) / 1000

        # ── Compute (EFLOP/s) — gen-cadence step function ────────────────────
        tflop_per_w = tflop_per_w_override if tflop_per_w_override is not None else tflop_per_w_for_year(year)
        compute_eflops = total_compute_mw * 1e6 * tflop_per_w / 1e18

        # ── HBM ──────────────────────────────────────────────────────────────
        hbm_tb = total_compute_mw * 1e3 * tflop_per_w * hbm_gb_per_tflop / 1e6

        # ── CoWoS / Packaging — driven by new capacity additions ──────────────
        cowos_index = compute_delta_mw * 0.5 + total_compute_mw * 0.1

        # ── Fab Equipment — driven by capex (new semiconductor capacity) ──────
        fab_index = compute_delta_mw * 1.2 + hbm_tb * 0.02

        # ── EDA Tools ─────────────────────────────────────────────────────────
        eda_index = compute_delta_mw * 0.3

        # ── Server count — rack density ramps as GB200 NVL72 → Rubin NVL144 ──
        server_kw = server_kw_override if server_kw_override is not None else server_kw_for_year(year)
        server_count_M = (total_compute_mw * 1000) / server_kw / 1e6

        # ── Server DRAM ───────────────────────────────────────────────────────
        server_dram_tb = server_count_M * 1e6 * dram_tb_per_server

        # ── CPU/Host ──────────────────────────────────────────────────────────
        cpu_M = server_count_M * 2  # ~2 CPUs per server

        # ── Substrates ───────────────────────────────────────────────────────
        substrate_M = server_count_M * 12  # chips per server

        # ── Networking ────────────────────────────────────────────────────────
        port_speed_factor = 1.0 if year < 2027 else (2.0 if year >= 2030 else 1.5)
        networking_tbps = (inference_mw * ports_per_mw * 0.4) / (1e6 / port_speed_factor)

        # ── Optics ────────────────────────────────────────────────────────────
        optics_ports_M = networking_tbps * 2.0

        # ── Physical / Construction ───────────────────────────────────────────
        construction_index = compute_delta_mw / 1000  # GW added per year

        # ── Connectors ───────────────────────────────────────────────────────
        connectors_M = server_count_M * 40  # ~40 high-speed connectors/server

        rows.append({
            "year": year,
            "efficiency_tokens_per_kwh": efficiency,
            "inference_mw": inference_mw,
            "total_compute_gw": total_compute_mw / 1000,
            "compute_delta_gw": compute_delta_mw / 1000,
            "power_total_gw": power_total_gw,
            "cooling_gw": cooling_mw / 1000,
            "compute_eflops": compute_eflops,
            "hbm_tb": hbm_tb,
            "cowos_index": cowos_index,
            "fab_index": fab_index,
            "eda_index": eda_index,
            "server_count_M": server_count_M,
            "server_dram_tb": server_dram_tb,
            "cpu_M": cpu_M,
            "substrate_M": substrate_M,
            "networking_tbps": networking_tbps,
            "optics_ports_M": optics_ports_M,
            "construction_index": construction_index,
            "connectors_M": connectors_M,
        })

    return pd.DataFrame(rows).set_index("year")


# ── Vintaged-fleet variant ────────────────────────────────────────────────────
# GPUs deployed in year Y run at year-Y frontier efficiency for `fleet_life_years`
# before retiring. The deployed fleet's blended efficiency lags frontier by ~half
# the fleet life, because old vintages persist. This is materially more accurate
# than the instantaneous-efficiency model — and pushes the power inflection LATER
# than the simple model says (efficiency improvements take years to mark-to-market
# across the installed base).

def build_infrastructure_demand_vintaged(
    token_df: pd.DataFrame,
    initial_anchor_gw: float = 40.0,                   # 2025 deployed power anchor (slider)
    tokens_per_kwh_2025: float = 3_600_000,            # FRONTIER 2025 (newest GPU eff)
    efficiency_doubling_years: float = 2.0,            # frontier doubling rate
    fleet_life_years: int = 6,                         # GPU/server lifecycle
    inference_utilization_2025: float = 0.067,
    inference_utilization_2035: float = 0.18,
    pue_2025: float = 1.40,
    pue_2040: float = 1.15,
    hbm_gb_per_tflop: float = 1.38,
    ports_per_mw: float = 11_000,
    server_kw_override: float | None = None,
    tflop_per_w_override: float | None = None,
    dram_tb_per_server: float = 1.0,
    initial_vintage_decay: float = 0.65,               # newer vintages get more weight in 2025 init
) -> pd.DataFrame:
    """
    Vintaged fleet model — GPUs persist at their build-year efficiency for ~6 yr.

    Each year:
      1. Retire cohorts older than fleet_life_years
      2. Compute remaining fleet's max inference output (MW × build-eff × util)
      3. If demand > existing capacity, add new cohort at frontier efficiency
      4. Total power = total_fleet_mw × PUE
      5. Blended fleet efficiency = MW-weighted avg of active vintages

    Returns same columns as `build_infrastructure_demand` plus:
      - frontier_eff_tokens_per_kwh: efficiency of NEW capacity in this year
      - fleet_blended_eff_tokens_per_kwh: weighted-avg efficiency of installed fleet
      - fleet_age_avg_yrs: weighted-avg vintage age
    """
    def frontier_eff(year: int) -> float:
        return tokens_per_kwh_2025 * 2 ** ((year - 2025) / efficiency_doubling_years)

    def util_for(year: int) -> float:
        t = min(1.0, (year - 2025) / (2035 - 2025))
        return inference_utilization_2025 + t * (inference_utilization_2035 - inference_utilization_2025)

    def pue_for(year: int) -> float:
        t = min(1.0, (year - 2025) / (2040 - 2025))
        return pue_2025 + t * (pue_2040 - pue_2025)

    # ── Initialize 2025 fleet ─────────────────────────────────────────────────
    # Anchor: total_compute_mw × PUE_2025 = initial_anchor_gw × 1000
    initial_compute_mw = initial_anchor_gw * 1000.0 / pue_2025

    # Distribute across vintages [2025-fleet_life+1 .. 2025] with exp-decay weights
    vintage_years = list(range(2025 - fleet_life_years + 1, 2026))
    raw_w = [initial_vintage_decay ** (2025 - y) for y in vintage_years]
    norm = sum(raw_w)
    weights = {y: w / norm for y, w in zip(vintage_years, raw_w)}

    cohorts: dict[int, dict] = {}
    for y, w in weights.items():
        cohorts[y] = {"mw": initial_compute_mw * w, "eff": frontier_eff(y)}

    rows = []
    for year in YEARS:
        yrs = year - 2025

        # 1. Retire old cohorts
        cutoff = year - fleet_life_years + 1
        cohorts = {y: c for y, c in cohorts.items() if y >= cutoff}

        u = util_for(year)
        pue = pue_for(year)
        f_eff = frontier_eff(year)

        # 2. Existing fleet capability (tokens/day at inference util)
        existing_mw = sum(c["mw"] for c in cohorts.values())
        existing_eff_total = sum(c["mw"] * c["eff"] for c in cohorts.values())
        existing_tokens_capacity = existing_eff_total * u * 24_000

        # 3. Demand
        cloud_tokens = token_df.loc[year, "total_cloud_T"]
        demanded_tokens = cloud_tokens * 1e12

        # 4. Add new cohort if shortfall
        if year == 2025:
            new_mw = 0.0  # initialized — don't double-count
        else:
            shortfall = demanded_tokens - existing_tokens_capacity
            if shortfall > 0:
                new_mw = shortfall / (u * 24_000 * f_eff)
                cohorts[year] = {"mw": new_mw, "eff": f_eff}
            else:
                new_mw = 0.0  # over-supplied — old fleet runs at lower load (not modeled)

        # 5. Total fleet
        total_compute_mw = sum(c["mw"] for c in cohorts.values())
        compute_delta_mw = new_mw

        if total_compute_mw > 0:
            blended_eff = sum(c["mw"] * c["eff"] for c in cohorts.values()) / total_compute_mw
            avg_age = sum((year - y) * c["mw"] for y, c in cohorts.items()) / total_compute_mw
        else:
            blended_eff = f_eff
            avg_age = 0.0

        # 6. Power
        cooling_mw = total_compute_mw * (pue - 1.0)
        power_total_gw = (total_compute_mw + cooling_mw) / 1000

        # 7. Inference MW = u × total fleet MW (drives networking)
        inference_mw = u * total_compute_mw

        # 8. Downstream demand columns (same structure as base model)
        tflop_per_w = tflop_per_w_override if tflop_per_w_override is not None else tflop_per_w_for_year(year)
        compute_eflops = total_compute_mw * 1e6 * tflop_per_w / 1e18
        hbm_tb = total_compute_mw * 1e3 * tflop_per_w * hbm_gb_per_tflop / 1e6
        cowos_index = compute_delta_mw * 0.5 + total_compute_mw * 0.1
        fab_index = compute_delta_mw * 1.2 + hbm_tb * 0.02
        eda_index = compute_delta_mw * 0.3
        server_kw = server_kw_override if server_kw_override is not None else server_kw_for_year(year)
        server_count_M = (total_compute_mw * 1000) / server_kw / 1e6
        server_dram_tb = server_count_M * 1e6 * dram_tb_per_server
        cpu_M = server_count_M * 2
        substrate_M = server_count_M * 12
        port_speed_factor = 1.0 if year < 2027 else (2.0 if year >= 2030 else 1.5)
        networking_tbps = (inference_mw * ports_per_mw * 0.4) / (1e6 / port_speed_factor)
        optics_ports_M = networking_tbps * 2.0
        construction_index = compute_delta_mw / 1000
        connectors_M = server_count_M * 40

        rows.append({
            "year": year,
            "frontier_eff_tokens_per_kwh": f_eff,
            "fleet_blended_eff_tokens_per_kwh": blended_eff,
            "efficiency_tokens_per_kwh": blended_eff,           # alias for compat
            "fleet_age_avg_yrs": avg_age,
            "n_active_cohorts": len(cohorts),
            "inference_mw": inference_mw,
            "total_compute_gw": total_compute_mw / 1000,
            "compute_delta_gw": compute_delta_mw / 1000,
            "power_total_gw": power_total_gw,
            "cooling_gw": cooling_mw / 1000,
            "compute_eflops": compute_eflops,
            "hbm_tb": hbm_tb,
            "cowos_index": cowos_index,
            "fab_index": fab_index,
            "eda_index": eda_index,
            "server_count_M": server_count_M,
            "server_dram_tb": server_dram_tb,
            "cpu_M": cpu_M,
            "substrate_M": substrate_M,
            "networking_tbps": networking_tbps,
            "optics_ports_M": optics_ports_M,
            "construction_index": construction_index,
            "connectors_M": connectors_M,
        })

    return pd.DataFrame(rows).set_index("year")


# Map each layer name to its demand column in infra_df
LAYER_DEMAND_COL = {
    "Power Generation": "power_total_gw",
    "Grid Interconnect Queue": "construction_index",
    "GOES (Electrical Steel)": "power_total_gw",
    "Large Power Transformers (LPT)": "power_total_gw",
    "Distribution Transformers": "power_total_gw",
    "UPS / Backup Power": "power_total_gw",
    "Liquid Cooling": "cooling_gw",
    "Skilled Electrical Labor": "construction_index",
    "GPU / AI Accelerators": "compute_eflops",
    "HBM Memory": "hbm_tb",
    "CoWoS / Advanced Packaging": "cowos_index",
    "Fab Equipment": "fab_index",
    "EDA Tools / IP": "eda_index",
    "CPU / Host Processors": "cpu_M",
    "Server DRAM": "server_dram_tb",
    "Advanced Substrates / PCB": "substrate_M",
    "ABF Dielectric Film": "substrate_M",
    "HBM Hybrid Bonding": "hbm_tb",
    "EUV Mask Inspection / Pellicles": "fab_index",
    "Scale-Out Networking Silicon": "networking_tbps",
    "Co-Packaged Optics (CPO)": "networking_tbps",
    "DPU / SmartNICs": "networking_tbps",
    "Optical Transceivers": "optics_ports_M",
    "Fiber / Physical Cabling": "optics_ports_M",
    "High-Speed Connectors": "connectors_M",
    "Active Electrical Cables (AEC)": "networking_tbps",
    "Data Center Construction": "construction_index",
    "DC REITs / Co-lo": "total_compute_gw",
    # Round 4 — grid buildout pipeline + defense; all capex-driven (scales with new GW additions)
    "Line Hardware & HVDC Cable": "construction_index",
    "Steel Poles & Towers": "construction_index",
    "Galvanizing": "construction_index",
    "Defense Adjacent": "construction_index",
}


def build_tightness_scores(
    infra_df: pd.DataFrame,
    custom_supply_growth: dict | None = None,
) -> pd.DataFrame:
    """
    Tightness score 0-100 per layer per year.

    While demand is growing:
        score = demand_growth / (supply_growth × lag_adj) × 50, capped 0-100
    After demand peaks (demand_growth < 0):
        score decays by (1 - 1/lead_time) per year, reflecting supply
        commitments already in the pipeline that can't be cancelled.
        Long-lead-time layers (power gen: 8yr) decay slowly → supply
        overhang persists for years after the inflection.
        Short-lead-time layers (GPU: 1.25yr) drop quickly.
    """
    scores = {}

    for layer, col in LAYER_DEMAND_COL.items():
        if col not in infra_df.columns:
            continue
        supply_growth = (custom_supply_growth or {}).get(
            layer, LAYERS[layer]["supply_growth_pct"]
        )
        lead_time = LAYERS[layer]["lead_time_yrs"]
        demand_series = infra_df[col].values

        layer_scores = [50.0]  # anchor base year

        # Fraction of prior score that bleeds over each year when demand turns.
        # lead_time=8 → 87.5% persists; lead_time=1.25 → 20% persists.
        decay_factor = 1.0 - 1.0 / max(lead_time, 1.0)

        for i in range(1, len(YEARS)):
            d_prev = demand_series[i - 1]
            d_curr = demand_series[i]
            prev_score = layer_scores[-1]

            if d_prev <= 0:
                layer_scores.append(0.0)
                continue

            demand_growth = (d_curr - d_prev) / d_prev

            # Lead time penalty: supply less responsive with longer lead time
            lag_adj = min(1.0, 1.0 / max(lead_time, 0.5))
            effective_supply = supply_growth * lag_adj

            if demand_growth >= 0:
                ratio = demand_growth / max(effective_supply, 0.005)
                score = min(100.0, ratio * 50.0)
            else:
                # Demand declining → committed supply still arriving (overhang)
                # Score decays at lead-time-dependent rate rather than cliff to 0
                score = prev_score * decay_factor

            layer_scores.append(score)

        scores[layer] = layer_scores

    return pd.DataFrame(scores, index=YEARS)


def power_inflection_year(infra_df: pd.DataFrame) -> int | None:
    """First year where YoY power demand growth turns negative (efficiency wins)."""
    power = infra_df["power_total_gw"]
    for i in range(1, len(YEARS)):
        if power.iloc[i] < power.iloc[i - 1]:
            return YEARS[i]
    return None


# ── Supply chain topology (for flow chart) ───────────────────────────────────
# Each node: id, label, x (0-1), y (0-1), layer_key (maps to tightness score)
# Edges: (source_id, target_id)

FLOW_NODES = [
    # Demand inputs (left side)
    {"id": "retail",     "label": "Retail\nUsers",        "x": 0.02, "y": 0.25},
    {"id": "enterprise", "label": "Enterprise\nKnowledge", "x": 0.02, "y": 0.50},
    {"id": "robotics",   "label": "Robotics\n& AV",        "x": 0.02, "y": 0.75},

    # Cloud inference
    {"id": "cloud_tokens", "label": "Cloud\nToken Demand", "x": 0.17, "y": 0.50},

    # Silicon design / upstream
    {"id": "eda",     "label": "EDA Tools\nSNPS CDNS",      "x": 0.32, "y": 0.08, "layer": "EDA Tools / IP"},
    {"id": "fab_eq",  "label": "Fab\nEquipment\nAMAT LRCX", "x": 0.32, "y": 0.20, "layer": "Fab Equipment"},
    {"id": "cowos",   "label": "CoWoS\nPackaging\nTSM ASE", "x": 0.32, "y": 0.36, "layer": "CoWoS / Advanced Packaging"},

    # Core compute
    {"id": "gpu",  "label": "GPU / AI\nAccelerators\nNVDA AMD", "x": 0.48, "y": 0.30, "layer": "GPU / AI Accelerators"},
    {"id": "hbm",  "label": "HBM\nMemory\nMU Hynix",           "x": 0.48, "y": 0.50, "layer": "HBM Memory"},
    {"id": "cpu",  "label": "CPU / Host\nINTC AMD",             "x": 0.48, "y": 0.68, "layer": "CPU / Host Processors"},
    {"id": "dram", "label": "Server\nDRAM\nMU Samsung",         "x": 0.48, "y": 0.84, "layer": "Server DRAM"},

    # Server platform
    {"id": "substrate", "label": "Substrates\nPCB\nTTM IBIDEN", "x": 0.57, "y": 0.92, "layer": "Advanced Substrates / PCB"},
    {"id": "server",    "label": "AI Server\nPlatform",          "x": 0.62, "y": 0.50},
    {"id": "connectors","label": "Connectors\nAPH TE",           "x": 0.62, "y": 0.76, "layer": "High-Speed Connectors"},

    # Networking
    {"id": "net_silicon", "label": "Network\nSilicon\nAVGO MRVL", "x": 0.75, "y": 0.35, "layer": "Scale-Out Networking Silicon"},
    {"id": "optics",      "label": "Optical\nTransceivers\nCOHR", "x": 0.75, "y": 0.55, "layer": "Optical Transceivers"},
    {"id": "fiber",       "label": "Fiber\nCabling\nGLW",          "x": 0.75, "y": 0.70, "layer": "Fiber / Physical Cabling"},

    # Facility
    {"id": "dc_build",  "label": "DC\nConstruction\nMYRG PWR",   "x": 0.87, "y": 0.25, "layer": "Data Center Construction"},
    {"id": "dc_reit",   "label": "DC REITs\nEQIX DLR",            "x": 0.87, "y": 0.42, "layer": "DC REITs / Co-lo"},
    {"id": "cooling",   "label": "Cooling\nVRT Nidec",             "x": 0.87, "y": 0.58, "layer": "Liquid Cooling"},

    # Power
    {"id": "ups",       "label": "UPS/\nBackup\nETN GNRC",        "x": 0.97, "y": 0.30, "layer": "UPS / Backup Power"},
    {"id": "tx",        "label": "LPT\n6501.T GEV-Prolec",         "x": 0.97, "y": 0.50, "layer": "Large Power Transformers (LPT)"},
    {"id": "power_gen", "label": "Power Gen\nGEV Nuclear",         "x": 0.97, "y": 0.70, "layer": "Power Generation"},
]

FLOW_EDGES = [
    ("retail",     "cloud_tokens"),
    ("enterprise", "cloud_tokens"),
    ("robotics",   "cloud_tokens"),
    ("cloud_tokens","gpu"),
    ("cloud_tokens","hbm"),
    ("cloud_tokens","cpu"),
    ("eda",        "fab_eq"),
    ("fab_eq",     "cowos"),
    ("cowos",      "gpu"),
    ("cowos",      "hbm"),
    ("gpu",        "server"),
    ("hbm",        "server"),
    ("cpu",        "server"),
    ("dram",       "server"),
    ("substrate",  "server"),
    ("connectors", "server"),
    ("server",     "net_silicon"),
    ("server",     "dc_build"),
    ("net_silicon","optics"),
    ("optics",     "fiber"),
    ("dc_build",   "dc_reit"),
    ("dc_reit",    "cooling"),
    ("cooling",    "ups"),
    ("ups",        "tx"),
    ("tx",         "power_gen"),
]


# ── Names detail registry — for the "easiest bets" surface ────────────────────
# tier: P = primary play (highest exposure), S = secondary, K = kicker (small / private / restricted)
# Used by v2 dashboard to weight stock-level mispricing scores
LAYER_NAMES_DETAIL = {
    "Power Generation": [
        ("GEV", "P", "Gas turbine slots through 2030; backlog 100→110 GW; pricing +10-20%/kW Q1 2026"),
        ("CEG", "P", "Existing nuclear PPAs; behind-the-meter bypass for AI"),
        ("VST", "P", "Texas merchant + nuclear restart optionality"),
        ("TLN", "P", "AMZN nuclear PPA precedent; behind-the-meter"),
        ("SE", "P", "Siemens Energy €146B backlog; Grid Tech 25-27% growth"),
        ("MHI 7011.T", "S", "Japanese turbine doubling under-followed in US"),
        ("Hitachi 6501.T", "S", "Hitachi Energy embedded; LPT capacity 2028"),
        ("NRG", "S", "Independent power producer"),
        ("AES", "S", "Renewables + grid storage"),
        ("DUK", "K", "Regulated utility — slower growth"),
        ("SO", "K", "Regulated utility"),
        ("OKLO", "K", "SMR pre-revenue; not investable 2026-28"),
    ],
    "Grid Interconnect Queue": [
        ("GEV", "P", "Owns interconnect supply chain"),
        ("SE", "P", "Grid Technologies €146B"),
        ("Hitachi 6501.T", "P", "Hitachi Energy LPT + grid"),
        ("PWR", "P", "Quanta — interconnect EPC"),
        ("MYRG", "P", "Specialty contractor labor"),
        ("CEG", "P", "Behind-the-meter nuclear bypass"),
        ("TLN", "P", "Behind-the-meter nuclear bypass"),
        ("AEP", "S", "Transmission utility"),
        ("EXC", "S", "Transmission utility"),
        ("DUK", "S", "Transmission utility"),
        ("VST", "S", "Behind-the-meter merchant"),
        ("ABB", "S", "Grid automation"),
    ],
    "GOES (Electrical Steel)": [
        ("CLF", "P", "Single US producer (Butler PA, Zanesville OH); embedded GOES franchise NOT in any sell-side SOTP — largest mispricing"),
        ("POSCO 005490.KS", "P", "Korean GOES major"),
        ("JFE 5411.T", "P", "Japanese GOES producer"),
        ("Nippon Steel 5401.T", "P", "Japanese GOES producer"),
        ("Stalprodukt", "S", "Polish small-cap"),
        ("ThyssenKrupp", "S", "European GOES capacity"),
        ("Baoshan 600019.SS", "S", "Chinese — restricted"),
    ],
    "Large Power Transformers (LPT)": [
        ("Hitachi 6501.T", "P", "Hitachi Energy embedded; VA capacity online 2028"),
        ("GEV (Prolec)", "P", "Prolec GE accretion; transformer-attach to turbines"),
        ("SE", "P", "Siemens Energy Charlotte NC online early 2027"),
        ("HUBB", "P", "Hubbell — utility transformer franchise"),
        ("ABB", "P", "Grid automation + transformers"),
        ("SPXC", "P", "SPX Technologies — transformer cores + medium-voltage switchgear; pivotal in colleague's T11"),
        ("WEG", "S", "Brazilian electric equipment"),
        ("POWL", "P", "Powell Industries — switchgear; pivotal at 34.5x in colleague's T11"),
    ],
    "Distribution Transformers": [
        ("ETN", "P", "Eaton Q4 2025 backlog $19.6B; Electrical Americas $13.2B (+31%)"),
        ("NVT", "P", "nVent — pure-play electrical"),
        ("HUBB", "P", "Hubbell distribution"),
        ("ABB", "P", "Distribution automation"),
        ("Schneider", "P", "Schneider Electric — global breadth"),
        ("Legrand", "S", "European distribution"),
        ("POWL", "S", "Powell Industries"),
        ("ATKR", "S", "Atkore — electrical raceways"),
    ],
    "UPS / Backup Power": [
        ("ETN", "P", "Eaton UPS franchise"),
        ("VRT", "P", "Vertiv FY26 guide $13.5-14B; Americas +44% YoY"),
        ("Schneider", "P", "Schneider Electric UPS"),
        ("GNRC", "P", "Generac — backup gen"),
        ("CMI", "P", "Cummins — gensets"),
        ("CAT", "S", "Caterpillar — gensets"),
        ("Kohler", "S", "Private — gensets"),
        ("Delta 2308.TT", "S", "Taiwanese UPS"),
        ("MPWR", "P", "Monolithic Power — on-board PMIC / 48V conversion for AI servers; pivotal at 64.4x in colleague's T3 (rack power density tailwind)"),
    ],
    "Liquid Cooling": [
        ("VRT", "P", "Vertiv — installed-base advantage; Thermokay closing"),
        ("MOD", "P", "Modine — CDU + cold plate"),
        ("Nidec 6594.T", "P", "Japanese cooling motors"),
        ("Boyd (ETN)", "P", "Boyd acquired by Eaton 2025 ($9.5B)"),
        ("Munters", "S", "Swedish thermal — MTRS.ST"),
        ("SPXC", "S", "Specialty cooling"),
        ("Asetek", "S", "Direct-to-chip cooling"),
        ("EMR", "K", "Emerson — diversified"),
        ("JCI", "K", "Johnson Controls — building HVAC"),
        ("TT", "K", "Trane Tech — commercial HVAC"),
    ],
    "Skilled Electrical Labor": [
        ("MYRG", "P", "MYR Group — specialty contractor"),
        ("PWR", "P", "Quanta — record $44B backlog YE25"),
        ("EME", "P", "EMCOR — labor arbitrage not in multiples"),
        ("FIX", "P", "Comfort Systems — record $12.5B backlog Q1 2026"),
        ("IESC", "P", "IES Holdings — rethink prior cut given labor rent"),
        ("APG", "S", "API Group"),
        ("MTZ", "S", "MasTec"),
        ("DY", "S", "Dycom"),
        ("PRIM", "S", "Primoris Services"),
    ],
    "GPU / AI Accelerators": [
        ("NVDA", "P", "Dominant; $1T Blackwell+Rubin orders through 2027"),
        ("AVGO", "P", "Custom XPU; $21B Anthropic deal validates ASIC share gain"),
        ("GOOG (TPU)", "P", "TPU v6/v7 internal silicon"),
        ("AMZN (Trainium)", "P", "Trainium 3 ramping"),
        ("AMD", "S", "MI355X — gaining slowly; lagging perf/W"),
        ("MRVL", "S", "Trainium attach"),
        ("ALAB", "S", "PCIe/CXL retimers"),
        ("Cerebras", "K", "Private — IPO pending"),
    ],
    "HBM Memory": [
        ("SK Hynix 000660.KS", "P", "Clear leader; NVDA qualified"),
        ("MU", "P", "Micron — gaining share, 30% power efficiency advantage"),
        ("Samsung 005930.KS", "P", "Struggling to qualify 8-Hi at NVDA"),
        ("Lasertec 6920.T", "S", "HBM inspection equipment"),
        ("Disco 6146.T", "S", "Wafer dicing for HBM"),
        ("TEL 8035.T", "S", "Hybrid bonding deposition"),
        ("Han Mi Semi", "K", "Korean TC bonders"),
    ],
    "CoWoS / Advanced Packaging": [
        ("TSM", "P", "CoWoS-L 80→130k WPM end-26 (+62%)"),
        ("ASE 3711.TT", "P", "OSAT leader"),
        ("AMKR", "P", "Amkor — advanced packaging"),
        ("INTC IFS", "S", "Intel Foundry — late entrant"),
        ("BESI", "P", "Hybrid bonding tools — structural winner"),
        ("ONTO", "S", "Onto Innovation — packaging metrology"),
        ("Disco 6146.T", "S", "Dicing for advanced packaging"),
        ("TEL 8035.T", "S", "Tokyo Electron — packaging tools"),
    ],
    "Fab Equipment": [
        ("AMAT", "P", "Applied Materials — Etch/Dep beneficiary GAA"),
        ("LRCX", "P", "Lam Research — etch leader"),
        ("KLAC", "P", "KLA — process control"),
        ("ASML", "P", "EUV monopoly — separate dynamic"),
        ("ACLS", "P", "Axcelis — ion implant; pivotal at 35.3x in colleague's T2 (memory + power-device tailwind)"),
        ("TEL 8035.T", "S", "Tokyo Electron — etch/dep"),
        ("TER", "S", "Teradyne — test"),
        ("ENTG", "P", "Entegris — materials engineering; 1% yield = $800M for 1.4nm"),
        ("MKSI", "S", "MKS Instruments"),
        ("AEHR", "K", "AEHR Test Systems — niche"),
        ("Lasertec 6920.T", "S", "EUV mask inspection — sole supplier"),
    ],
    "EDA Tools / IP": [
        ("SNPS", "P", "Synopsys — duopoly"),
        ("CDNS", "P", "Cadence — duopoly"),
        ("ARM", "P", "ARM — royalty stream from custom silicon"),
        ("Siemens EDA", "S", "Mentor — distant 3rd"),
        ("ALAB", "S", "Astera Labs — IP+silicon"),
        ("Rambus RMBS", "P", "HBM4 memory interface IP royalty stream — under-appreciated"),
        ("CEVA", "K", "DSP IP"),
    ],
    "CPU / Host Processors": [
        ("AMD (EPYC)", "P", "x86 server share +200bps/yr"),
        ("INTC", "P", "Losing share -500bps 2025-26"),
        ("ARM", "P", "+600bps server share to 7%"),
        ("AMZN (Graviton)", "S", "Internal ARM server CPU"),
        ("MSFT (Cobalt)", "S", "Internal ARM server CPU"),
        ("GOOG (Axion)", "S", "Internal ARM server CPU"),
        ("Ampere", "K", "Private — pure-play ARM server"),
        ("AAPL (M-series)", "K", "Internal Mac silicon"),
    ],
    "Server DRAM": [
        ("SK Hynix 000660.KS", "P", "Allocation gated; 2028 already booking"),
        ("MU", "P", "Customers asking for 2028 allocation"),
        ("Samsung 005930.KS", "P", "P4 fab flexibility — only player with conventional capacity adds"),
        ("Nanya 2408.TT", "S", "Specialty DRAM"),
        ("Winbond 2344.TT", "S", "Niche memory"),
    ],
    "Advanced Substrates / PCB": [
        ("IBIDEN 4062.T", "P", "35%+ AI substrate share"),
        ("Unimicron 3037.TT", "P", "Major Taiwanese substrate"),
        ("TTM", "P", "TTM Tech — North America"),
        ("AT&S", "S", "Austrian substrate"),
        ("Shinko 6967.T", "S", "JIC-acquired 2024"),
        ("SEMCO 009150.KS", "S", "Samsung Electro-Mechanics"),
    ],
    "ABF Dielectric Film": [
        ("Ajinomoto 2802.T", "P", "SOLE ABF dielectric film supplier — true monopoly. Trades as food/staples; specialty chem re-rate catalyst 2026-27 as Fukushima capacity hits HBM4/CoWoS-L peak. Most mispriced silicon-stack name"),
        ("Sekisui Chemical 4204.T", "S", "Adjacent specialty films — secondary ABF play"),
        ("Mitsui Chemicals 4183.T", "S", "Pellicles + adjacent specialty chemicals"),
    ],
    "HBM Hybrid Bonding": [
        ("BESI", "P", "Hybrid bonding tools monopoly into HBM4 transition. Sell-side underestimates HBM4 unit volume vs trailing logic-on-logic"),
        ("ASMPT 0522.HK", "P", "Advanced packaging equipment leader; HBM TC bonder + transitioning to hybrid bonding"),
        ("Han Mi Semi 042700.KS", "P", "TC bonder for HBM stacking — 90%+ share Korean memory ecosystem"),
        ("AMAT", "S", "Hybrid bonding deposition layer (CMP, copper bonding interfaces)"),
        ("TEL 8035.T", "S", "Hybrid bonding deposition tools"),
    ],
    "EUV Mask Inspection / Pellicles": [
        ("Lasertec 6920.T", "P", "Actinic EUV mask inspection monopoly. A16 has more EUV layers than N2; High-NA extends monopoly to ACTIS A300. -30% from 2024 highs on stale EUV-peaking narrative"),
        ("Mitsui Chemicals 4183.T", "P", "EUV pellicle leader — sole supplier for High-NA"),
        ("ASML", "S", "EUV scanner monopoly (separate dynamic — capacity gating not the bottleneck)"),
    ],
    "Scale-Out Networking Silicon": [
        ("AVGO", "P", "Tomahawk 6 (102.4T) volume; Tomahawk 7 in dev; ~50% merchant switch silicon share"),
        ("MRVL", "P", "Marvell — Innovium acquisition + Teralynx + custom networking ASICs for Trainium"),
        ("NVDA (Mellanox)", "P", "Mellanox InfiniBand + Spectrum Ethernet ~$15B/yr — bigger than ANET. Cross-tier exposure not surfaced in NVDA narrative (gets credited to compute)"),
        ("ANET", "P", "Arista — silicon attach +50% in 2025; AI back-end Ethernet leader"),
        ("CSCO (Silicon One)", "S", "Cisco custom silicon — G200 8x800G, gaining hyperscaler design wins"),
        ("HPE (Juniper)", "P", "HPE+Juniper closed Jan 2025 ($14B). Juniper Mist AI, Apstra fabric automation. AI/cloud networking now ~40% of HPE revenue post-deal — quietly the #2 enterprise AI infra story"),
        ("ALAB", "S", "Astera Labs — PCIe/CXL retimers + Scorpio fabric switches for AI rack"),
        ("CRDO", "S", "Credo — AECs (+245% 2024); SerDes/PHY IP into networking ASICs"),
        ("MTSI", "S", "MACOM — analog driver/TIA into networking and optical"),
    ],
    "Co-Packaged Optics (CPO)": [
        ("AVGO", "P", "Tomahawk 6+CPO architectural leader; bonds optics directly onto switch ASIC. First volume hyperscaler CPO 2027-28. Captures $/port that today goes to transceiver vendors"),
        ("MRVL", "P", "Marvell CPO roadmap on next-gen switch silicon; partnership with TSM for advanced packaging"),
        ("NVDA", "P", "Quantum-X / Spectrum-X CPO disclosed at GTC 2025 — co-packaged silicon photonics for InfiniBand/Ethernet"),
        ("TSM", "P", "TSMC SoIC + CoWoS packaging is the CPO bottleneck — silicon photonics integration on advanced packaging substrates. Same line as HBM/CoWoS — competing for capacity"),
        ("ASE 3711.TT", "P", "ASE 2.5D/3D packaging for CPO assembly; sub-supplier to AVGO/MRVL"),
        ("COHR", "S", "Coherent — laser engines for external light sources to CPO modules; preserves some content even after pluggable cannibalization"),
        ("LITE", "S", "Lumentum — DML/EML laser source for remote light delivery into CPO"),
        ("INTC IFS", "K", "Intel silicon photonics IP + IFS packaging — pre-CPO product but technology adjacency"),
        ("POET", "K", "Optical Interposer platform — pre-revenue CPO play"),
    ],
    "DPU / SmartNICs": [
        ("NVDA (BlueField)", "P", "BlueField-3 dominant in AI data centers; offloads networking + storage from x86. ~$3B run-rate hidden inside NVDA networking line"),
        ("AMD (Pensando)", "P", "Pensando ($2B acquisition) DPU shipping in Azure/Oracle clouds; Salina P4 next-gen 2026"),
        ("INTC (IPU)", "S", "Intel IPU E2000 deployed at Google — under-followed but volume customer"),
        ("MRVL (OCTEON)", "S", "OCTEON 10 ARM-based DPU; security/SDN attach"),
        ("AVGO", "S", "Stingray/Pensando-class SmartNIC silicon — incremental to switch business"),
        ("ALAB", "K", "Astera Labs PCIe fabric — adjacent to DPU role"),
    ],
    "Optical Transceivers": [
        ("COHR", "P", "Coherent — 800G/1.6T leader; transceiver + laser engine breadth"),
        ("LITE", "P", "Lumentum — major transceiver supplier + EML/DML lasers"),
        ("CIEN", "P", "Ciena — DCI Wolfe top pick; coherent optical for DC interconnect"),
        ("FN", "P", "Fabrinet — contract manufacturing for COHR/NVDA optical modules; quietly the fab-equivalent of optics"),
        ("MTSI", "S", "MACOM — driver/TIA into transceivers"),
        ("AAOI", "S", "Applied Optoelectronics — small-cap hyperscaler wins (AMZN, MSFT)"),
        ("MXL", "P", "MaxLinear — PAM4 DSP/CDR for 800G/1.6T transceivers; broader connectivity portfolio still rebuilding post-Silicon Motion deal collapse — depressed multiple, optionality on optical re-rate"),
        ("POET", "K", "POET Technologies — Si photonics interposer dev; pre-revenue"),
        ("CRDO", "S", "AEC primary; transceiver SerDes secondary"),
        ("Innolight 300308.SZ", "P", "Innolight (Suzhou) ~25% global AI optics share — largest 800G volume supplier to NVDA. Shenzhen A-share NOT directly tradeable for US accounts; watch only as share-shift signal vs COHR/LITE"),
        ("Eoptolink 300502.SZ", "P", "Eoptolink ~15% global AI optics share; Chinese A-share watch only. Disclosures useful for transceiver pricing/volume read-throughs"),
        ("Accelink 002281.SZ", "S", "Accelink — transceiver + DWDM components; A-share watch only"),
        ("Hisense Broadband", "K", "Hisense — Chinese transceiver volume player; private/sub of Hisense Group"),
    ],
    "Fiber / Physical Cabling": [
        ("GLW", "P", "Corning — capacity-constrained 2024-26"),
        ("Prysmian", "P", "PRY IM — at ceiling"),
        ("CommScope", "P", "MTP/MPO chokepoint"),
        ("BDC", "S", "Belden"),
        ("Furukawa 5801.T", "S", "Japanese fiber"),
        ("Sumitomo 5802.T", "S", "Cable + fusion splicers"),
        ("Fujikura 5803.T", "S", "Japanese fiber"),
    ],
    "High-Speed Connectors": [
        ("APH", "P", "Amphenol — 40%+ PCIe 5/6 share; 2025 +28% organic"),
        ("TE Connectivity", "P", "TEL — major share"),
        ("Molex", "P", "Private/Koch — major share"),
        ("MOG.A", "S", "Moog — specialty"),
        ("Bel Fuse", "S", "BELFB"),
        ("Hirose 6806.T", "S", "Japanese connectors"),
        ("JAE 6807.T", "S", "Japan Aviation Electronics"),
    ],
    "Active Electrical Cables (AEC)": [
        ("CRDO", "P", "Credo Tech — ~80% AEC market share; 2025 revenue +245%. Replaces passive copper above 400G/lane and short-reach optics inside rack"),
        ("AVGO", "S", "Broadcom AEC SerDes IP into ASIC; secondary beneficiary"),
        ("MRVL", "S", "Marvell PAM4 DSP into AEC modules"),
        ("MTSI", "S", "MACOM — analog driver into AEC"),
        ("APH", "S", "Amphenol — AEC assembly + connectors"),
        ("Molex", "S", "Molex — AEC assembly"),
    ],
    "Data Center Construction": [
        ("PWR", "P", "Quanta — record $44B backlog YE25"),
        ("MYRG", "P", "MYR Group — labor arbitrage"),
        ("FIX", "P", "Comfort Systems — modular pre-fab thesis validated"),
        ("EME", "P", "EMCOR — labor scarcity rent"),
        ("APG", "S", "API Group"),
        ("MTZ", "S", "MasTec"),
        ("DY", "S", "Dycom"),
        ("PRIM", "S", "Primoris"),
        ("Turner", "K", "Private — major DC GC"),
    ],
    "DC REITs / Co-lo": [
        ("EQIX", "P", "Equinix — premium co-location"),
        ("DLR", "P", "Digital Realty — wholesale"),
        ("IRM", "S", "Iron Mountain — DC pivot"),
        ("AMT", "S", "American Tower — DC pivot"),
        ("IREN", "P", "Iris Energy — HPC hosting"),
        ("CORZ", "P", "Core Scientific — HPC"),
        ("APLD", "S", "Applied Digital — HPC hosting"),
        ("NEXTDC", "S", "NXT AU — Australian DC"),
        ("Keppel DC", "S", "KDC SP — Asian DC REIT"),
    ],
    "Line Hardware & HVDC Cable": [
        ("PLPC", "P", "Preformed Line Products — sole-source on certain pole-line specs; under-followed micro-cap"),
        ("HUBB", "P", "Hubbell Power Systems — utility hardware franchise"),
        ("TEL", "S", "TE Connectivity — utility cable accessories"),
        ("Prysmian", "P", "PRY IM — HVDC cable order book through 2030"),
        ("Nexans", "S", "Nexans NEX FP — HVDC cable"),
        ("NKT", "P", "NKT A/S DK — HVDC subsea cable; Vineyard Wind, Bornholm; effective duopoly with Prysmian"),
        ("Southwire", "K", "Private — North American conductor leader"),
    ],
    "Steel Poles & Towers": [
        ("VMI", "P", "Valmont — steel/concrete transmission poles + galvanizing; pivotal duopoly"),
        ("ACA", "P", "Arcosa — wind/transmission structures; cheapest pivotal at 12.4x"),
        ("TRN", "S", "Trinity Industries — railcar + structural"),
        ("NUE", "S", "Nucor — structural steel feedstock"),
        ("STLD", "S", "Steel Dynamics — structural steel feedstock"),
        ("Sabre", "K", "Private — steel pole specialist"),
    ],
    "Galvanizing": [
        ("AZZ", "P", "AZZ Inc. — largest pure-play hot-dip galvanizer in NA; quiet duopoly mispriced as cyclical"),
        ("VMI", "P", "Valmont vertically integrated — galvanizing + poles"),
    ],
    "Defense Adjacent": [
        ("GHM", "P", "Graham Corporation — vacuum + heat-transfer; naval nuclear + AI cooling"),
        ("ESE", "P", "ESCO Technologies — Doble (utility) + ETS-Lindgren (EW shielding) + Globe (defense filtration)"),
        ("ATMU", "P", "Atmus Filtration — turbine inlet air filtration; AI gas turbine adjacency"),
        ("IPGP", "S", "IPG Photonics — high-power lasers; defense + cutting"),
        ("BWXT", "S", "BWX Technologies — naval nuclear sole-source"),
        ("HII", "S", "Huntington Ingalls — naval shipbuilder"),
        ("GD", "S", "General Dynamics — diversified defense"),
        ("CW", "S", "Curtiss-Wright — defense electronics"),
        ("TDG", "S", "TransDigm — aero aftermarket pricing power"),
        ("HEI", "S", "HEICO — aero parts + defense electronics"),
    ],
}


def all_tickers_with_layers() -> dict:
    """Returns {ticker: [(layer, tier, rationale), ...]} — used by v2 dashboard."""
    out: dict = {}
    for layer, names in LAYER_NAMES_DETAIL.items():
        for ticker, tier, rationale in names:
            out.setdefault(ticker, []).append((layer, tier, rationale))
    return out


# ── Monopoly / sole-source tickers ────────────────────────────────────────────
# Used by the v2 dashboard's composite scoring formula. These names are
# structurally underpriced because the sum-of-tightness ranking favors breadth
# (multi-layer plays) over depth (single layer, single supplier, no substitute).
# Curated from the Stonehouse research desks' own mispricing flags.
MONOPOLY_TICKERS = {
    "CLF",                     # GOES — sole US producer
    "Ajinomoto 2802.T",        # ABF dielectric film — sole supplier
    "Lasertec 6920.T",         # Actinic EUV mask inspection — monopoly
    "BESI",                    # Hybrid bonding tools — monopoly into HBM4
    "ASML",                    # EUV scanner — monopoly
    "TSM",                     # Leading-edge foundry — effective monopoly
    "MU",                      # Only US HBM producer (national security premium)
    "GLW",                     # Corning — fiber capacity-constrained
    "Han Mi Semi 042700.KS",   # TC bonder for Korean HBM ecosystem
    "ASMPT 0522.HK",           # Advanced packaging equipment leader
    "Mitsui Chemicals 4183.T", # EUV pellicle sole supplier
    # Round 4: colleague's grid-buildout + galvanizing duopolies
    "AZZ",                     # Galvanizing — largest pure-play, ~40% NA share
    "VMI",                     # Steel poles + galvanizing duopolist
    "ACA",                     # Steel poles duopolist (with VMI)
    "NKT",                     # HVDC subsea cable duopolist (with Prysmian)
    "PLPC",                    # Pole-line hardware — sole-source on certain specs
    "BWXT",                    # Naval nuclear — sole-source
    "ATMU",                    # Turbine inlet air filtration — installed-base lock-in
}


# ── Pivotal (★) tickers ──────────────────────────────────────────────────────
# Colleague's flow-diagram-v3 designation: critical-path / sole-source /
# under-priced operator within their tier. 18 names across 14 tiers. Drives
# the ★ badge in the v2 dashboard's Easiest Bets table.
PIVOTAL_TICKERS = {
    "ACLS",   # T2 silicon — Axcelis ion implant
    "ESE",    # T2/T11/T15 silicon+power+defense — ESCO Technologies
    "MPWR",   # T3 silicon — Monolithic Power
    "ALAB",   # T5 silicon — Astera Labs (PCIe/CXL retimers)
    "FIX",    # T7 dc — Comfort Systems modular pre-fab
    "HUBB",   # T8/T11 dc+power — Hubbell connectors + grid hardware
    "SPXC",   # T11 power — SPX Technologies transformer cores
    "POWL",   # T11 power — Powell Industries switchgear
    "CLF",    # T11 power — GOES sole-source
    "PLPC",   # T12 power — Preformed Line Products
    "NKT",    # T12 power — HVDC subsea cable
    "VMI",    # T13 power — Valmont steel poles
    "ACA",    # T13 power — Arcosa steel poles (cheapest pivotal)
    "AZZ",    # T14 power — galvanizing leader
    "GHM",    # T15 defense — Graham vacuum/heat-transfer
    "ATMU",   # T15 defense — Atmus turbine air filtration
}


# ── Tier mapping ─────────────────────────────────────────────────────────────
# Maps each of the 29 model layers to colleague's canonical T1-T15 numbering
# and track (silicon / dc / power / defense). Used by dashboard for grouping
# and narrative. T6 (Hyperscalers) and T10 (DC Hub) are demand-side, not
# supply layers — they don't appear in our model.
LAYER_TIER = {
    # Power / Energy
    "Power Generation":               ("T9",  "power"),
    "Grid Interconnect Queue":        ("T9",  "power"),
    "GOES (Electrical Steel)":        ("T11", "power"),
    "Large Power Transformers (LPT)": ("T11", "power"),
    "Distribution Transformers":      ("T11", "power"),
    "UPS / Backup Power":             ("T9",  "power"),
    "Liquid Cooling":                 ("T8",  "dc"),
    "Skilled Electrical Labor":       ("T7",  "dc"),
    # Silicon / Compute
    "GPU / AI Accelerators":          ("T4",  "silicon"),
    "HBM Memory":                     ("T4",  "silicon"),
    "CoWoS / Advanced Packaging":     ("T4",  "silicon"),
    "Fab Equipment":                  ("T2",  "silicon"),
    "EDA Tools / IP":                 ("T3",  "silicon"),
    "CPU / Host Processors":          ("T4",  "silicon"),
    "Server DRAM":                    ("T4",  "silicon"),
    "Advanced Substrates / PCB":      ("T4",  "silicon"),
    "ABF Dielectric Film":            ("T1",  "silicon"),
    "HBM Hybrid Bonding":             ("T2",  "silicon"),
    "EUV Mask Inspection / Pellicles": ("T2",  "silicon"),
    # Networking
    "Scale-Out Networking Silicon":   ("T5",  "silicon"),
    "Co-Packaged Optics (CPO)":       ("T5",  "silicon"),
    "DPU / SmartNICs":                ("T5",  "silicon"),
    "Optical Transceivers":           ("T5",  "silicon"),
    "Fiber / Physical Cabling":       ("T5",  "silicon"),
    "High-Speed Connectors":          ("T5",  "silicon"),
    "Active Electrical Cables (AEC)": ("T5",  "silicon"),
    # Physical Infrastructure
    "Data Center Construction":       ("T7",  "dc"),
    "DC REITs / Co-lo":               ("T7",  "dc"),
    # Round 4 grid buildout pipeline
    "Line Hardware & HVDC Cable":     ("T12", "power"),
    "Steel Poles & Towers":           ("T13", "power"),
    "Galvanizing":                    ("T14", "power"),
    "Defense Adjacent":               ("T15", "defense"),
}

TRACK_COLOR = {
    "silicon": "#8e44ad",   # purple
    "dc":      "#16a085",   # teal
    "power":   "#c0392b",   # red
    "defense": "#1a5276",   # navy
}


# ── Theme exposure overlay ───────────────────────────────────────────────────
# Estimated % of company revenue tied to AI infrastructure / data-center demand.
# Used by the dashboard's Pure-Play Score: composite × exposure / 100.
#
# Why this matters: a ticker can be the sole-source supplier of a critical
# bottleneck input but only generate, say, 6% of total revenue from it (CLF / GOES).
# In that case the structural mispricing is real but the equity-level rerate is
# small — the market is pricing 94% of the business correctly.
#
# Numbers below are best estimates from segment disclosures, sell-side decks,
# and earnings call commentary. Treat as a calibration starting point — refine
# from primary sources or override per ticker. Defaults to 30% if missing.
#
# Source notes (representative):
#   CLF 6% — PM lookup; GOES is small slice of integrated steel revenue
#   Ajinomoto 4% — ABF film monopoly hidden inside ¥1.4T food/staples giant
#   Hitachi 6501.T 10% — Hitachi Energy is the AI-tied subset of conglomerate
#   AZZ 35% — galvanizing services 60% of revenue; transmission/utility ~half of that
#   NVDA 85% — DC dominant; gaming/auto are small share now
#   AVGO 50% — networking + custom XPU AI; still has wireless/broadband
#   ASML 85% — leading-edge wafer capex is overwhelmingly AI-driven
#   ALAB 95% — Astera Labs is a pure AI rack-interconnect pure-play
#   EQIX/DLR 100% — DC operators
#   VRT 75% — DC power/cooling pure-play
#   FIX 50% — modular DC pre-fab dominates the order book
#   GEV 35% — gas turbines AI-tied; nuclear/wind/grid services dilute
#   CEG/TLN 30% — most reactor capacity is grid baseload; behind-the-meter PPAs growing
THEME_EXPOSURE = {
    # ── Pure plays (>70%) ────────────────────────────────────────────────────
    "NVDA": 85, "ALAB": 95, "ASML": 85, "Lasertec 6920.T": 75, "BESI": 80,
    "ASMPT 0522.HK": 70, "Han Mi Semi 042700.KS": 80, "Han Mi Semi": 80,
    "Disco 6146.T": 70, "VRT": 75, "CRDO": 75, "IBIDEN 4062.T": 70, "Ampere": 80,
    "FN": 70, "Cerebras": 100,
    # DC operators are pure plays
    "EQIX": 100, "DLR": 100, "IREN": 100, "CORZ": 100, "APLD": 100,
    "NEXTDC": 100, "Keppel DC": 100,
    # ── Significant exposure (40-70%) ───────────────────────────────────────
    "AVGO": 50, "AMAT": 50, "LRCX": 50, "KLAC": 50, "TSM": 60, "MU": 50,
    "SK Hynix 000660.KS": 40, "TEL 8035.T": 40, "ANET": 65, "MRVL": 50,
    "COHR": 60, "LITE": 65, "AAOI": 65, "MOD": 40, "Asetek": 50, "POWL": 60,
    "PWR": 40, "MYRG": 40, "EME": 40, "FIX": 50, "ONTO": 60, "ENTG": 50,
    "ACLS": 40, "Shinko 6967.T": 60, "SEMCO 009150.KS": 40, "Unimicron 3037.TT": 55,
    "AT&S": 50, "MPWR": 50, "SNPS": 50, "CDNS": 50, "Rambus RMBS": 60,
    "ARM": 40, "Boyd (ETN)": 40,
    # ── Moderate exposure (25-40%) ──────────────────────────────────────────
    "AMD": 35, "AMD (EPYC)": 35, "GEV": 35, "GEV (Prolec)": 35, "CEG": 30,
    "VST": 25, "TLN": 30, "SE": 30, "Schneider": 30, "ETN": 35, "GNRC": 35,
    "HUBB": 30, "ABB": 25, "AMKR": 30, "ASE 3711.TT": 35, "TE Connectivity": 25,
    "TEL": 25, "Prysmian": 25, "CIEN": 35, "GLW": 35, "SPXC": 35, "NVT": 35,
    "Munters": 25, "MTSI": 30, "Bel Fuse": 30, "Delta 2308.TT": 30,
    "ESE": 35, "AZZ": 35, "VMI": 30, "PLPC": 65, "NKT": 70, "ACA": 35,
    "PRIM": 25, "IESC": 35, "TER": 30, "MKSI": 30, "Hirose 6806.T": 20,
    "TTM": 40, "Stalprodukt": 30, "CommScope": 30, "BDC": 25, "Nanya 2408.TT": 25,
    "GHM": 25, "ATMU": 25, "BWXT": 25, "CW": 20, "IPGP": 20, "IRM": 25,
    "Sabre": 50, "Southwire": 30, "Molex": 30,
    # ── Low exposure / diversified (10-25%) ─────────────────────────────────
    "INTC": 15, "INTC IFS": 15, "AAPL (M-series)": 5, "Samsung 005930.KS": 15,
    "Winbond 2344.TT": 15, "MHI 7011.T": 10, "Hitachi 6501.T": 10,
    "Nidec 6594.T": 8, "EMR": 12, "JCI": 8, "TT": 10, "CMI": 12, "CAT": 10,
    "DUK": 8, "SO": 8, "EXC": 10, "AEP": 12, "NRG": 10, "AES": 10,
    "MTZ": 15, "DY": 15, "APG": 20, "AMT": 15, "ATKR": 10, "Legrand": 15,
    "GD": 8, "TDG": 8, "HII": 15, "HEI": 10, "MOG.A": 15, "WEG": 5,
    "ThyssenKrupp": 5, "JAE 6807.T": 15, "Furukawa 5801.T": 15, "Fujikura 5803.T": 15,
    "Sumitomo 5802.T": 5, "Kohler": 25, "Nexans": 15, "TRN": 10, "APH": 50,
    # ── Very low / structurally tiny (≤10%) ─────────────────────────────────
    "CLF": 6,                     # GOES is sole-source but ~6% of integrated steel rev
    "Ajinomoto 2802.T": 4,        # ABF film inside food/staples giant
    "Mitsui Chemicals 4183.T": 5, # EUV pellicle inside diversified chems
    "Sekisui Chemical 4204.T": 3,
    "POSCO 005490.KS": 3, "JFE 5411.T": 3, "Nippon Steel 5401.T": 3,
    "Baoshan 600019.SS": 2, "NUE": 5, "STLD": 5,
    "AAOI": 65,  # already covered above; keeping for safety
    # ── Internal-customer "tickers" (no public equity) — use parent if any ──
    "GOOG (TPU)": 5,              # internal silicon — exposure on GOOG shares ~5%
    "AMZN (Trainium)": 5,         # internal — AWS AI inside AMZN ~10% but Trainium specifically smaller
    "AMZN (Graviton)": 4,
    "MSFT (Cobalt)": 5, "GOOG (Axion)": 4,
    # ── Pre-revenue / private (NA but tag for clarity) ──────────────────────
    "OKLO": 100, "POET": 100, "AEHR": 30, "Siemens EDA": 30, "CEVA": 25,
    "Turner": 35, "CSCO (Silicon One)": 15,
    # ── Networking / optics expansion (Wave 9) ───────────────────────────────
    # HPE post-Juniper close (Jan 2025) — combined networking + Aruba + Juniper
    # is now ~40% of HPE; rest of company (compute/storage/services) still drags
    "HPE (Juniper)": 40,
    "HPE": 40,
    # Cross-tier exposure — these inherit parent's exposure since they're the
    # same equity (NVDA Mellanox/Spectrum, AMD Pensando, etc.)
    "NVDA (Mellanox)": 85,         # part of NVDA — same 85%
    "NVDA (BlueField)": 85,        # BlueField DPU under NVDA networking line
    "AMD (Pensando)": 35,          # AMD parent exposure
    "INTC (IPU)": 15,              # Intel — diversified, IPU small slice
    "MRVL (OCTEON)": 50,           # Marvell parent exposure
    # MaxLinear — connectivity/PAM4 is meaningful slice of revenue post-SIMO collapse
    "MXL": 50,
    # Chinese A-share optics — heavy AI optics concentration; not tradeable for
    # US accounts but tagged for completeness so they appear in rankings as
    # watch-only references
    "Innolight 300308.SZ": 80,
    "Eoptolink 300502.SZ": 75,
    "Accelink 002281.SZ": 50,
    "Hisense Broadband": 30,
}


def theme_exposure_pct(ticker: str, default: int = 30) -> int:
    """Return estimated AI-infrastructure revenue exposure (0-100) for a ticker."""
    return THEME_EXPOSURE.get(ticker, default)


# ── Market cap reference (USD billions, ~April 2026) ─────────────────────────
# Best-effort snapshot for sizing bubbles in the dashboard's interactive
# explorer. Update from Bloomberg before any decision-grade work — these are
# illustrative and decay with every tape print.
MARKET_CAP_USD_B = {
    # Mega-cap silicon
    "NVDA": 3500, "AAPL (M-series)": 3200, "MSFT (Cobalt)": 3300,
    "GOOG (TPU)": 2300, "GOOG (Axion)": 2300, "AMZN (Trainium)": 2200,
    "AMZN (Graviton)": 2200, "AVGO": 1100, "TSM": 1300, "META": 1700,
    "ORCL": 600,
    # Large-cap silicon
    "AMD": 320, "AMD (EPYC)": 320, "AMD (Pensando)": 320, "INTC": 110,
    "INTC IFS": 110, "INTC (IPU)": 110, "ARM": 180, "ASML": 360,
    "QCOM": 200, "MU": 180, "AMAT": 180, "LRCX": 130, "KLAC": 130,
    "SNPS": 120, "CDNS": 95, "MRVL": 75, "MRVL (OCTEON)": 75,
    "ANET": 230, "ADI": 110, "TXN": 180,
    "NVDA (Mellanox)": 3500, "NVDA (BlueField)": 3500,
    # Mid-cap silicon / equipment
    "Lasertec 6920.T": 22, "BESI": 12, "ASMPT 0522.HK": 8,
    "Han Mi Semi": 10, "Han Mi Semi 042700.KS": 10,
    "Disco 6146.T": 30, "TEL 8035.T": 90, "ONTO": 11, "ENTG": 18,
    "TER": 15, "MKSI": 6, "AEHR": 0.4, "ACLS": 4, "CRDO": 12,
    "MTSI": 8, "MPWR": 35, "ALAB": 15, "MXL": 1.2, "Rambus RMBS": 7,
    # Memory
    "SK Hynix 000660.KS": 130, "Samsung 005930.KS": 380,
    "Nanya 2408.TT": 5, "Winbond 2344.TT": 2,
    # Foundry / OSAT / packaging
    "ASE 3711.TT": 30, "AMKR": 7, "IBIDEN 4062.T": 8,
    "Unimicron 3037.TT": 5, "TTM": 2.5, "AT&S": 0.8,
    "Shinko 6967.T": 4, "SEMCO 009150.KS": 9,
    # Specialty inputs / sole-source
    "Ajinomoto 2802.T": 30, "Sekisui Chemical 4204.T": 8,
    "Mitsui Chemicals 4183.T": 4, "POSCO 005490.KS": 22,
    "JFE 5411.T": 8, "Nippon Steel 5401.T": 24, "ThyssenKrupp": 6,
    "Stalprodukt": 0.4, "Baoshan 600019.SS": 25,
    # IP
    "Siemens EDA": 200, "CEVA": 0.4, "Cerebras": 5,
    "Ampere": 4, "Turner": 8,
    # Optical / networking specialty
    "COHR": 14, "LITE": 9, "CIEN": 11, "FN": 9, "AAOI": 1.5,
    "POET": 0.4, "CSCO (Silicon One)": 220,
    "Innolight 300308.SZ": 18, "Eoptolink 300502.SZ": 14,
    "Accelink 002281.SZ": 4, "Hisense Broadband": 1.5,
    "HPE": 25, "HPE (Juniper)": 25,
    # Connectors / fiber
    "APH": 110, "TE Connectivity": 60, "Molex": 30,
    "Hirose 6806.T": 6, "JAE 6807.T": 1.5, "Bel Fuse": 1.4,
    "MOG.A": 7,
    "GLW": 35, "Prysmian": 18, "CommScope": 0.8, "BDC": 5,
    "Furukawa 5801.T": 3, "Sumitomo 5802.T": 6, "Fujikura 5803.T": 5,
    "Nexans": 7, "Southwire": 8,
    # Power gen
    "GEV": 130, "GEV (Prolec)": 130, "CEG": 90, "VST": 60,
    "TLN": 30, "SE": 60, "Hitachi 6501.T": 130, "MHI 7011.T": 80,
    "NRG": 25, "AES": 12, "DUK": 100, "SO": 110, "AEP": 60,
    "EXC": 45, "OKLO": 4, "WEG": 30,
    # Power equipment / grid
    "ETN": 130, "VRT": 50, "ABB": 105, "HUBB": 25, "SPXC": 8,
    "POWL": 4, "NVT": 12, "Schneider": 130, "Legrand": 25,
    "ATKR": 2.5, "GNRC": 9, "CMI": 50, "CAT": 200, "Kohler": 6,
    "Delta 2308.TT": 35, "EMR": 75, "JCI": 65, "TT": 95,
    "Munters": 4, "Asetek": 0.05, "MOD": 5, "Boyd (ETN)": 130,
    "Nidec 6594.T": 30,
    # Contractors / specialty labor
    "PWR": 70, "MYRG": 4, "EME": 25, "FIX": 30, "IESC": 6,
    "APG": 12, "MTZ": 12, "DY": 6, "PRIM": 4,
    # DC REITs
    "EQIX": 90, "DLR": 60, "IRM": 35, "AMT": 100,
    "IREN": 4, "CORZ": 9, "APLD": 3, "NEXTDC": 6, "Keppel DC": 3,
    # Materials / steel / GOES
    "CLF": 8, "NUE": 35, "STLD": 22, "TRN": 3,
    # Grid buildout (T12-T14)
    "PLPC": 0.7, "NKT": 6, "VMI": 7, "ACA": 4, "AZZ": 3, "Sabre": 0.5,
    # Defense adjacent
    "GHM": 0.6, "ESE": 4, "ATMU": 4, "IPGP": 3, "BWXT": 12,
    "HII": 9, "GD": 90, "CW": 17, "TDG": 90, "HEI": 35,
}


def market_cap_b(ticker: str, default: float = 5.0) -> float:
    """Return estimated market cap in USD billions for a ticker (default 5B if unknown)."""
    return MARKET_CAP_USD_B.get(ticker, default)


# ── Company blurbs (one-liner about what each ticker does) ────────────────────
# Neutral, generic descriptions — what the business is, not investment opinion.
# Tickers not listed fall back to the per-layer rationale in LAYER_NAMES_DETAIL.
COMPANY_BLURBS = {
    # ── Semis: GPU / accelerators / CPU ────────────────────────────────────
    "NVDA": "GPU and AI accelerator leader. ~80% data-center AI silicon share. Owns the full stack: silicon (GB200/Rubin), networking (Mellanox InfiniBand + Spectrum Ethernet), DPUs (BlueField), and software (CUDA, NIM).",
    "NVDA (Mellanox)": "Cross-tier exposure: NVDA's networking line — Mellanox InfiniBand + Spectrum Ethernet — is ~$15B/yr and growing, hidden inside the parent's compute narrative.",
    "NVDA (BlueField)": "Cross-tier exposure: NVDA's BlueField DPU offloads networking + storage from x86 hosts. ~$3B run-rate inside NVDA networking.",
    "AMD": "x86 CPU vendor (EPYC server) and the #2 AI GPU vendor (MI355X). Owns Pensando DPU. Distant 2nd to NVDA in AI compute, gaining share slowly.",
    "AMD (EPYC)": "AMD's x86 server CPU line. ~+200bps server share/yr.",
    "AMD (Pensando)": "AMD's DPU, deployed in Azure and Oracle clouds. Salina P4 next-gen 2026.",
    "INTC": "x86 incumbent losing share to AMD and ARM. Foundry Services trying to win advanced-node leadership through 18A.",
    "INTC IFS": "Intel Foundry Services — late entrant to leading-edge foundry; Microsoft + DOD wins, behind on volume.",
    "INTC (IPU)": "Intel IPU E2000 — DPU deployed at Google. Volume customer despite limited public follow.",
    "AVGO": "Custom AI XPU partner (Anthropic, Google TPU) + merchant networking switch silicon (Tomahawk). Pivot to software (VMware acquisition). ~50% AI exposure.",
    "MRVL": "Networking silicon + custom AI ASICs (Trainium attach). PAM4 DSP for optical transceivers; OCTEON DPU.",
    "MRVL (OCTEON)": "Marvell's ARM-based DPU/SmartNIC line. Security + SDN attach.",
    "ARM": "CPU IP licensing (Apple M-series, server ARM, mobile). Royalty stream from custom-silicon wave (TPU, Graviton, Cobalt).",
    "QCOM": "Mobile + auto SoC leader. AI inference push but small AI infra exposure.",
    "ALAB": "Astera Labs — PCIe/CXL retimers + Scorpio fabric switches. AI rack interconnect pure play.",
    "CRDO": "Credo Tech — Active Electrical Cables (AECs) ~80% market share + SerDes/PHY IP into networking ASICs.",
    "MTSI": "MACOM — analog driver/TIA chips for transceivers and networking.",
    "MPWR": "Monolithic Power — on-board PMICs and 48V conversion for AI servers.",
    "ACLS": "Axcelis Technologies — ion implant equipment leader; pivotal for memory + power devices.",

    # ── Memory ────────────────────────────────────────────────────────────
    "MU": "Micron — only US memory producer. HBM share growing, gaining ~30% power efficiency advantage.",
    "SK Hynix 000660.KS": "Korean memory leader; primary HBM supplier to NVDA. Allocation gated through 2028.",
    "Samsung 005930.KS": "Diversified Korean conglomerate. Memory + foundry + consumer electronics. Struggling to qualify HBM at NVDA.",
    "Nanya 2408.TT": "Taiwanese specialty DRAM producer. Niche.",
    "Winbond 2344.TT": "Niche Taiwanese memory.",

    # ── Foundry / packaging / equipment ────────────────────────────────────
    "TSM": "Taiwan Semiconductor — leading-edge foundry effective monopoly. Runs CoWoS packaging that bonds GPU + HBM. Capacity gates the entire AI chip ramp.",
    "ASML": "EUV lithography monopoly. Only company on Earth that builds these scanners. High-NA generation extends the moat.",
    "ASE 3711.TT": "ASE Technology — top OSAT (outsourced packaging). Behind TSMC's CoWoS but levered to advanced packaging including CPO assembly.",
    "AMKR": "Amkor — US-listed advanced packaging vendor. CHIPS Act AZ fab adjacent to TSMC.",
    "Lasertec 6920.T": "Sole-source supplier of actinic EUV mask blank inspection. True monopoly extending to High-NA via ACTIS A300.",
    "BESI": "BE Semiconductor — hybrid bonding tool monopoly. Critical equipment for HBM4 transition (4x equipment intensity per die).",
    "ASMPT 0522.HK": "Advanced packaging equipment leader. HBM TC bonders + transitioning to hybrid bonding.",
    "Han Mi Semi 042700.KS": "Han Mi Semiconductor — 90%+ share of TC bonders for Korean HBM ecosystem.",
    "Disco 6146.T": "Disco Corp — wafer dicing and grinding equipment. Monopoly in precision cutting for HBM and advanced packaging.",
    "TEL 8035.T": "Tokyo Electron — broad semiconductor equipment portfolio. Etch, deposition, hybrid bonding.",
    "AMAT": "Applied Materials — broad fab equipment vendor; etch and deposition leader.",
    "LRCX": "Lam Research — etch leader; high-aspect-ratio etch critical for 3D NAND and DRAM.",
    "KLAC": "KLA Corp — process control / metrology / inspection. Critical for yield at advanced nodes.",
    "ONTO": "Onto Innovation — packaging metrology and inspection. Levered to CoWoS.",
    "ENTG": "Entegris — specialty materials and process consumables. 1% yield improvement = ~$800M at 1.4nm.",
    "TER": "Teradyne — semiconductor test equipment. Memory + SoC test.",
    "MKSI": "MKS Instruments — vacuum, photonics, and motion subsystems for semi equipment.",
    "AEHR": "AEHR Test Systems — niche burn-in test equipment for SiC and silicon photonics.",
    "Ajinomoto 2802.T": "Diversified Japanese food/staples maker. Hidden inside: ABF Build-up Film monopoly used in every advanced AI/CPU substrate. ~4% of revenue but 100% market share.",
    "Mitsui Chemicals 4183.T": "Diversified Japanese specialty chemicals. EUV pellicle sole supplier (small slice of revenue).",
    "Sekisui Chemical 4204.T": "Japanese specialty chemicals. Adjacent specialty films — secondary ABF play.",
    "IBIDEN 4062.T": "Japanese substrate maker. ~35%+ AI substrate share.",
    "Unimicron 3037.TT": "Major Taiwanese ABF substrate supplier.",
    "TTM": "TTM Technologies — North American PCB maker.",

    # ── EDA / IP ──────────────────────────────────────────────────────────
    "SNPS": "Synopsys — EDA software duopoly. Critical for every chip design start.",
    "CDNS": "Cadence — EDA software duopoly. Pricing power on custom-silicon wave.",
    "Rambus RMBS": "HBM4 memory interface IP royalty stream. Under-appreciated angle.",

    # ── Networking / optics ────────────────────────────────────────────────
    "ANET": "Arista Networks — cloud + AI back-end Ethernet switch leader. Levered to AVGO Tomahawk silicon.",
    "CSCO (Silicon One)": "Cisco's custom switch silicon (G200) + enterprise networking incumbent.",
    "HPE": "Hewlett Packard Enterprise — servers + storage. Just closed Juniper acquisition (Jan 2025) — networking now ~40% of HPE.",
    "HPE (Juniper)": "HPE's Juniper unit (post Jan 2025 close) — Mist AI + Apstra fabric automation.",
    "COHR": "Coherent — 800G/1.6T optical transceiver leader; laser engines + transceiver breadth.",
    "LITE": "Lumentum — major transceiver supplier + DML/EML laser source. Hyperscaler exposed.",
    "CIEN": "Ciena — coherent optical for data-center interconnect (DCI). Wolfe top pick.",
    "FN": "Fabrinet — contract manufacturer for COHR / NVDA optical modules. The 'fab' of optics.",
    "AAOI": "Applied Optoelectronics — small-cap transceiver maker with hyperscaler wins (AMZN, MSFT).",
    "MXL": "MaxLinear — PAM4 DSP/CDR chips for 800G/1.6T transceivers + broader connectivity portfolio.",
    "POET": "POET Technologies — silicon photonics interposer dev; pre-revenue.",
    "Innolight 300308.SZ": "Suzhou Innolight — ~25% global AI optics share; largest 800G volume supplier to NVDA. Chinese A-share, watch only.",
    "Eoptolink 300502.SZ": "Eoptolink — ~15% global AI optics share. Chinese A-share, watch only.",
    "GLW": "Corning — glass + fiber. Capacity-constrained 2024-26 on optical fiber for DC builds.",
    "Prysmian": "Italian cable maker — power + optical fiber. HVDC subsea cable order book to 2030.",
    "CommScope": "Cabling and connectivity for data centers — MTP/MPO chokepoint.",
    "APH": "Amphenol — high-speed connectors. ~40% PCIe 5/6 share. 2025 organic +28%.",
    "TE Connectivity": "TE Connectivity — major connector incumbent. Broad industrial.",
    "Molex": "Private (Koch) — major connector share.",

    # ── DC: build / cooling / REITs ────────────────────────────────────────
    "VRT": "Vertiv — DC power + cooling pure play. Liquid cooling leader; FY26 guide $13.5-14B; Americas +44% YoY.",
    "MOD": "Modine — coolant distribution units (CDU) + cold plates for liquid cooling.",
    "EQIX": "Equinix — premium co-location REIT. Highest-density DC operator.",
    "DLR": "Digital Realty — wholesale DC REIT. Hyperscaler-tied.",
    "IREN": "Iris Energy — HPC hosting (formerly miner pivot).",
    "CORZ": "Core Scientific — HPC hosting (formerly miner pivot).",
    "PWR": "Quanta Services — specialty contractor. Record $44B backlog YE25 — AI grid + DC build.",
    "MYRG": "MYR Group — specialty electrical contractor.",
    "EME": "EMCOR — mechanical/electrical contractor. Levered to labor scarcity rent.",
    "FIX": "Comfort Systems — modular DC pre-fab dominant. Record $12.5B backlog Q1 2026.",
    "IESC": "IES Holdings — electrical contractor; rethink prior cut given labor rent.",
    "ETN": "Eaton — diversified electrical equipment. Q4 2025 backlog $19.6B; Electrical Americas +31% YoY.",
    "NVT": "nVent — pure-play electrical enclosures + thermal management.",
    "HUBB": "Hubbell — utility transformers + electrical components.",
    "ABB": "ABB — Swiss electrification + automation. Grid + transformers.",
    "GNRC": "Generac — backup power + standby gensets.",
    "CMI": "Cummins — gensets + power systems.",

    # ── Power generation ───────────────────────────────────────────────────
    "GEV": "GE Vernova — gas turbine + grid spin-out from GE. 100→110 GW backlog; pricing +10-20%/kW Q1 2026.",
    "GEV (Prolec)": "GEV's Prolec GE — transformer-attach to gas turbines.",
    "CEG": "Constellation Energy — largest US nuclear fleet. Behind-the-meter PPA leader for AI (MSFT, AMZN).",
    "VST": "Vistra — Texas merchant generation + nuclear (Comanche Peak) restart optionality.",
    "TLN": "Talen Energy — set the AMZN behind-the-meter nuclear PPA precedent.",
    "SE": "Siemens Energy — German turbines + grid technologies. €146B backlog; Grid Tech +25-27% growth.",
    "Hitachi 6501.T": "Hitachi — Japanese conglomerate. Hitachi Energy embedded as the AI-tied subset (transformers, grid).",
    "MHI 7011.T": "Mitsubishi Heavy Industries — Japanese gas turbine doubling underway, under-followed in US.",
    "OKLO": "Oklo — small modular reactor (SMR) developer. Pre-revenue, not investable through 2028.",

    # ── Materials / steel / GOES ───────────────────────────────────────────
    "CLF": "Cleveland-Cliffs — integrated US steelmaker. Hidden inside: sole US producer of grain-oriented electrical steel (GOES) — ~6% of revenue but 100% market share, used in every transformer.",
    "POSCO 005490.KS": "Korean integrated steelmaker. Major GOES producer.",
    "JFE 5411.T": "Japanese integrated steelmaker. Major GOES producer.",
    "Nippon Steel 5401.T": "Japanese integrated steelmaker. Major GOES producer.",
    "NUE": "Nucor — largest US mini-mill / structural steel.",
    "STLD": "Steel Dynamics — US mini-mill / structural steel.",

    # ── Grid buildout (T12-T14) ────────────────────────────────────────────
    "PLPC": "Preformed Line Products — small-cap pole-line hardware. Sole-source on certain utility specs.",
    "NKT": "NKT A/S (Denmark) — HVDC subsea cable; effective duopoly with Prysmian. Vineyard Wind, Bornholm.",
    "VMI": "Valmont — steel/concrete transmission poles + galvanizing. Pivotal duopoly with ACA.",
    "ACA": "Arcosa — wind/transmission structures. Cheapest pivotal at ~12x; spun from TRN.",
    "AZZ": "AZZ Inc — largest North American pure-play hot-dip galvanizer (~40% share). Quiet duopoly with VMI.",
    "POWL": "Powell Industries — switchgear; pivotal in T11 switchgear story.",
    "SPXC": "SPX Technologies — transformer cores + medium-voltage switchgear.",

    # ── Defense adjacent (T15) ─────────────────────────────────────────────
    "GHM": "Graham Corporation — vacuum + heat-transfer systems. Naval nuclear + AI cooling adjacency.",
    "ESE": "ESCO Technologies — Doble (utility test) + ETS-Lindgren (EW shielding) + Globe (defense filtration).",
    "ATMU": "Atmus Filtration — turbine inlet air filtration. AI gas turbine adjacency, installed-base lock-in.",
    "BWXT": "BWX Technologies — naval nuclear sole-source. Reactor cores for US Navy.",
    "HII": "Huntington Ingalls — naval shipbuilder (carriers, submarines).",
    "GD": "General Dynamics — diversified defense + Gulfstream.",
    "TDG": "TransDigm — aerospace aftermarket pricing power compounder.",
    "HEI": "HEICO — aero parts + defense electronics.",
    "IPGP": "IPG Photonics — high-power fiber lasers; defense + cutting + optical.",
    "CW": "Curtiss-Wright — defense electronics + naval nuclear adjacency.",

    # ── External / model labs (used in Users & Agents stage) ──────────────
    "MSFT": "Microsoft — OpenAI partner; Azure cloud; Copilot embed. The most levered mega-cap to AI demand on the consumer + enterprise side.",
    "MSFT (Cobalt)": "Microsoft's internal ARM server CPU. Small slice of MSFT revenue.",
    "GOOGL": "Alphabet/Google — Gemini frontier model + DeepMind + Google Cloud. Internal TPU silicon and Axion ARM server CPU.",
    "GOOG (TPU)": "Google's internal TPU silicon — small contribution to GOOG share value, but huge to AVGO (the partner).",
    "GOOG (Axion)": "Google's internal ARM server CPU (Axion).",
    "META": "Meta — Llama open-weights frontier; Reality Labs; ad business. Largest hyperscaler AI capex spender pro-rated.",
    "AAPL": "Apple — consumer ecosystem + Apple Intelligence (mostly on-device). M-series silicon internal.",
    "AAPL (M-series)": "Apple's internal M-series silicon — small AI infra exposure overall.",
    "AMZN": "Amazon — AWS + Anthropic stake + Trainium silicon. The cloud is the demand center; Bedrock the surface.",
    "AMZN (Trainium)": "Amazon's internal Trainium AI chip — small contribution to AMZN share value.",
    "AMZN (Graviton)": "Amazon's internal ARM server CPU (Graviton).",
    "ORCL": "Oracle — Oracle Cloud Infrastructure (OCI) hosting major Anthropic capacity. Late but large AI cloud entrant.",
}


def company_blurb(ticker: str) -> str:
    """Return a one-liner about what this company does, or empty string if unknown."""
    return COMPANY_BLURBS.get(ticker, "")
