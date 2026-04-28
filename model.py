"""
AI Infrastructure Supply Chain Model — Stonehouse Capital Management

Translates token demand into supply chain bottleneck signals across every
layer of the AI infrastructure stack, from silicon design to grid power.

Calibration anchor: ~30 GW total hyperscaler AI infrastructure in 2025.
"""

import os
import numpy as np
import pandas as pd
import openpyxl
from pathlib import Path

# Resolve backend repo: STONEHOUSE_BACKEND env var, then sibling-folder fallback
_BACKEND_ROOT = Path(
    os.environ.get("STONEHOUSE_BACKEND", "")
    or Path(__file__).parent.parent / "stonelodge-backend"
)
EXCEL_PATH = (
    _BACKEND_ROOT
    / "data/research/Technology and AI Analyst"
    / "AI Edge and Robotics/Token and Data Build Out.xlsx"
)

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
        "names": ["GEV", "CEG (nuclear)", "AES", "NRG"],
        "lead_time_yrs": 8.0, "supply_growth_pct": 0.07,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "Utility-scale power for AI data centers",
    },
    "Transformers / Switchgear": {
        "unit": "GW-equiv", "color": "#c0392b",
        "names": ["NVT", "HUBB", "ETN", "ABB"],
        "lead_time_yrs": 2.5, "supply_growth_pct": 0.15,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "Grid-to-datacenter step-down transformers",
    },
    "UPS / Backup Power": {
        "unit": "GW-equiv", "color": "#e67e22",
        "names": ["ETN", "Schneider", "GNRC", "CMI"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.22,
        "demand_driver": "compute", "demand_scale": 0.9,
        "description": "Uninterruptible power + emergency backup generation",
    },
    "Liquid Cooling": {
        "unit": "GW-thermal", "color": "#d35400",
        "names": ["VRT", "Nidec", "Modine (MOD)"],
        "lead_time_yrs": 0.75, "supply_growth_pct": 0.45,
        "demand_driver": "compute", "demand_scale": 0.8,
        "description": "Mandatory above 35 kW/rack; GPU clusters require liquid cooling",
    },

    # ── Silicon / Compute ─────────────────────────────────────────────────────
    "GPU / AI Accelerators": {
        "unit": "EFLOP/s", "color": "#8e44ad",
        "names": ["NVDA", "AMD", "GOOG (TPU)", "AMZN (Trainium)"],
        "lead_time_yrs": 1.25, "supply_growth_pct": 0.55,
        "demand_driver": "inference", "demand_scale": 1.0,
        "description": "Primary AI compute; NVDA dominant; custom ASICs growing",
    },
    "HBM Memory": {
        "unit": "TB total", "color": "#9b59b6",
        "names": ["MU", "SK Hynix", "Samsung"],
        "lead_time_yrs": 1.75, "supply_growth_pct": 0.38,
        "demand_driver": "compute", "demand_scale": 1.0,
        "description": "High Bandwidth Memory stacked on GPU packages; next binding constraint after CoWoS",
    },
    "CoWoS / Advanced Packaging": {
        "unit": "kwspm", "color": "#1abc9c",
        "names": ["TSM", "ASE", "Amkor"],
        "lead_time_yrs": 1.5, "supply_growth_pct": 0.32,
        "demand_driver": "capex", "demand_scale": 1.2,
        "description": "TSMC CoWoS bonds GPU die + HBM stacks; easing 2H26 but HBM4 re-tightens",
    },
    "Fab Equipment": {
        "unit": "WFE $B", "color": "#2980b9",
        "names": ["AMAT", "LRCX", "KLAC", "ASML"],
        "lead_time_yrs": 1.5, "supply_growth_pct": 0.20,
        "demand_driver": "capex", "demand_scale": 1.5,
        "description": "Wafer fab equipment; driven by new semiconductor capacity additions, not running load",
    },
    "EDA Tools / IP": {
        "unit": "design starts", "color": "#16a085",
        "names": ["SNPS", "CDNS", "SIEMENS EDA"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.18,
        "demand_driver": "capex", "demand_scale": 0.6,
        "description": "Design software for every custom ASIC/GPU; EDA duopoly; grows with custom silicon wave",
    },
    "CPU / Host Processors": {
        "unit": "M units", "color": "#27ae60",
        "names": ["INTC", "AMD (EPYC)", "ARM licensees"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.28,
        "demand_driver": "server", "demand_scale": 1.0,
        "description": "Every GPU server needs host CPUs; Intel losing share but still dominant",
    },
    "Server DRAM": {
        "unit": "TB total", "color": "#2ecc71",
        "names": ["MU", "Samsung", "SK Hynix"],
        "lead_time_yrs": 1.25, "supply_growth_pct": 0.30,
        "demand_driver": "server", "demand_scale": 1.0,
        "description": "DDR5 for AI server hosts; 512 GB–2 TB per server; distinct from HBM",
    },
    "Advanced Substrates / PCB": {
        "unit": "M units", "color": "#f1c40f",
        "names": ["TTM", "IBIDEN", "Unimicron"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.25,
        "demand_driver": "capex", "demand_scale": 0.8,
        "description": "High-layer-count substrates for GPU and HBM packages",
    },

    # ── Networking ────────────────────────────────────────────────────────────
    "Scale-Out Networking Silicon": {
        "unit": "Tb/s ports", "color": "#3498db",
        "names": ["AVGO", "MRVL", "ANET"],
        "lead_time_yrs": 0.75, "supply_growth_pct": 0.50,
        "demand_driver": "networking", "demand_scale": 1.0,
        "description": "Ethernet ASICs and switches for cluster interconnect; AVGO Tomahawk dominant",
    },
    "Optical Transceivers": {
        "unit": "M ports", "color": "#e74c3c",
        "names": ["COHR", "Lumentum", "II-VI"],
        "lead_time_yrs": 1.0, "supply_growth_pct": 0.40,
        "demand_driver": "optics", "demand_scale": 1.0,
        "description": "800G → 1.6T transceivers; silicon photonics transition underway",
    },
    "Fiber / Physical Cabling": {
        "unit": "km M", "color": "#7f8c8d",
        "names": ["GLW", "Prysmian", "CommScope"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.35,
        "demand_driver": "optics", "demand_scale": 0.8,
        "description": "Single-mode fiber for intra-DC + long-haul; Corning capacity constrained 2024-2026",
    },
    "High-Speed Connectors": {
        "unit": "M units", "color": "#95a5a6",
        "names": ["APH", "TE Connectivity", "Molex"],
        "lead_time_yrs": 0.5, "supply_growth_pct": 0.38,
        "demand_driver": "server", "demand_scale": 1.2,
        "description": "PCIe 5.0/6.0 connectors, power delivery connectors; Amphenol has 40%+ share",
    },

    # ── Physical Infrastructure ────────────────────────────────────────────────
    "Data Center Construction": {
        "unit": "GW capacity adds", "color": "#bdc3c7",
        "names": ["MYRG", "Quanta Services (PWR)", "Turner"],
        "lead_time_yrs": 2.0, "supply_growth_pct": 0.20,
        "demand_driver": "capex", "demand_scale": 1.0,
        "description": "Hyperscaler build-out; MYRG is largest DC specialty contractor",
    },
    "DC REITs / Co-lo": {
        "unit": "MW leased", "color": "#ecf0f1",
        "names": ["EQIX", "DLR", "IREN"],
        "lead_time_yrs": 2.5, "supply_growth_pct": 0.18,
        "demand_driver": "compute", "demand_scale": 0.5,
        "description": "Co-location and wholesale DC capacity; hyperscalers increasingly build own",
    },
}


def load_excel_scenario(sheet_name: str) -> pd.DataFrame:
    """
    Load a scenario sheet. Keeps first occurrence of duplicate row labels
    (prevents mix-% rows from overwriting the token-count rows).
    """
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


def build_infrastructure_demand(
    token_df: pd.DataFrame,
    tokens_per_kwh_2025: float = 3_600_000,
    efficiency_doubling_years: float = 2.5,
    inference_utilization_2025: float = 0.067,
    inference_utilization_2035: float = 0.18,
    pue_2025: float = 1.40,
    pue_2040: float = 1.15,
    hbm_gb_per_tflop: float = 1.38,
    ports_per_mw: float = 11_000,
    server_kw: float = 25.0,          # kW per AI server (8× GPU rack average)
    dram_tb_per_server: float = 1.0,  # TB DDR5 per AI server
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
            rows_so_far = len(rows)
            prev_compute = rows[-1]["total_compute_gw"] * 1000 if rows else 0
            compute_delta_mw = max(0, total_compute_mw - prev_compute)

        # ── PUE ───────────────────────────────────────────────────────────────
        t_pue = min(1.0, yrs / (2040 - 2025))
        pue = pue_2025 + t_pue * (pue_2040 - pue_2025)
        cooling_mw = total_compute_mw * (pue - 1.0)
        power_total_gw = (total_compute_mw + cooling_mw) / 1000

        # ── Compute (EFLOP/s): H100 ≈ 5.65 TFLOP/W ────────────────────────────
        tflop_per_w = 5.65
        compute_eflops = total_compute_mw * 1e6 * tflop_per_w / 1e18

        # ── HBM ──────────────────────────────────────────────────────────────
        hbm_tb = total_compute_mw * 1e3 * tflop_per_w * hbm_gb_per_tflop / 1e6

        # ── CoWoS / Packaging — driven by new capacity additions ──────────────
        cowos_index = compute_delta_mw * 0.5 + total_compute_mw * 0.1

        # ── Fab Equipment — driven by capex (new semiconductor capacity) ──────
        fab_index = compute_delta_mw * 1.2 + hbm_tb * 0.02

        # ── EDA Tools ─────────────────────────────────────────────────────────
        eda_index = compute_delta_mw * 0.3

        # ── Server count (per-server basis) ──────────────────────────────────
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


# Map each layer name to its demand column in infra_df
LAYER_DEMAND_COL = {
    "Power Generation": "power_total_gw",
    "Transformers / Switchgear": "power_total_gw",
    "UPS / Backup Power": "power_total_gw",
    "Liquid Cooling": "cooling_gw",
    "GPU / AI Accelerators": "compute_eflops",
    "HBM Memory": "hbm_tb",
    "CoWoS / Advanced Packaging": "cowos_index",
    "Fab Equipment": "fab_index",
    "EDA Tools / IP": "eda_index",
    "CPU / Host Processors": "cpu_M",
    "Server DRAM": "server_dram_tb",
    "Advanced Substrates / PCB": "substrate_M",
    "Scale-Out Networking Silicon": "networking_tbps",
    "Optical Transceivers": "optics_ports_M",
    "Fiber / Physical Cabling": "optics_ports_M",
    "High-Speed Connectors": "connectors_M",
    "Data Center Construction": "construction_index",
    "DC REITs / Co-lo": "total_compute_gw",
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
    {"id": "tx",        "label": "Transformers\nNVT HUBB",         "x": 0.97, "y": 0.50, "layer": "Transformers / Switchgear"},
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
