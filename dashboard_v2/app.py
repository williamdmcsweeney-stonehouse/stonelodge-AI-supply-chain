"""
AI Infra Supply Chain — Dashboard v2 — Stonehouse Capital
Run:   python -m streamlit run dashboard_v2/app.py --server.port 8503
       (or use dashboard_v2/run.bat)

Layout
------
- Sidebar: scenario presets + key sliders + advanced expander
- Main area (top to bottom):
    1. Headline metrics
    2. Year scrubber
    3. Bottleneck Map — 29 layers (T1-T15) as cards across silicon/dc/power/defense tracks
    4. Tightness Heat Grid — all layers x years
    5. Easiest Bets — top-10 cards with sparklines + ranked long-tail table
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent dir to path so we can import model.py
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Diagnostic try/except around model import. If this fails on Streamlit Cloud,
# show the REAL traceback on-screen instead of letting Streamlit redact it to a
# generic "ImportError" — this turns a 30-min debugging cycle into a 30-second
# one because the actual root cause shows up immediately on the broken page.
try:
    from model import (
        LAYER_NAMES_DETAIL,
        LAYER_TIER,
        LAYERS,
        MACRO_SCENARIOS,
        MONOPOLY_TICKERS,
        PIVOTAL_TICKERS,
        TRACK_COLOR,
        YEARS,
        all_tickers_with_layers,
        build_infrastructure_demand,
        build_infrastructure_demand_vintaged,
        build_macro_gap,
        build_tightness_scores,
        build_token_demand,
        gap_summary,
        load_excel_scenario,
        market_cap_b,
        power_inflection_year,
        theme_exposure_pct,
    )
except Exception as _model_import_err:
    import traceback as _tb
    import streamlit as _st_err
    _st_err.error(
        "**Model import failed** — full traceback below "
        "(if you're on Streamlit Cloud, also check the deploy logs)."
    )
    _st_err.code(_tb.format_exc(), language="python")
    _st_err.stop()


# ─────────────────────────────────────────────────────────────────────────────
# COMPANY BLURBS — defined in app.py (not imported from model.py) so the
# dashboard stays decoupled from model module changes. Adding/editing blurbs
# never requires touching model.py, and Streamlit Cloud's stale-import class
# of failure cannot affect this data.
# ─────────────────────────────────────────────────────────────────────────────

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


# ═════════════════════════════════════════════════════════════════════════════
# PAGE SETUP
# ═════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="AI Infra Supply Chain v2 | Stonehouse",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
.block-container { padding-top: 1.0rem; padding-bottom: 1rem; max-width: 1400px; }
[data-testid="stSidebar"] { background: #0b0e16; }
[data-testid="stSidebar"] h1 { font-size: 1.05rem; color: #fff; }
[data-testid="stSidebar"] h3 { font-size: 0.78rem; color: #8893a8; text-transform: uppercase; letter-spacing: 0.06em; margin-top: 1rem; }
.stMetric { background: #161a26; border-radius: 8px; padding: 10px 14px; border: 1px solid #2a2f3d; }
[data-testid="stMetricValue"] { font-size: 1.4rem; }
[data-testid="stMetricLabel"] { font-size: 0.72rem; color: #8893a8; }
.bottleneck-card {
    border-radius: 8px; padding: 10px 12px; margin-bottom: 8px;
    border: 1px solid rgba(255,255,255,0.08);
    transition: transform 0.1s ease;
}
.bottleneck-card:hover { transform: translateY(-2px); border-color: rgba(255,255,255,0.25); }
.bottleneck-card .layer-name { font-size: 12px; font-weight: 600; color: white; margin-bottom: 2px; line-height: 1.15; }
.bottleneck-card .score-big  { font-size: 22px; font-weight: 800; color: white; line-height: 1; }
.bottleneck-card .score-unit { font-size: 10px; font-weight: 400; color: rgba(255,255,255,0.7); margin-left: 3px; }
.bottleneck-card .chips      { font-size: 10px; color: rgba(255,255,255,0.85); margin-top: 6px; line-height: 1.3; }
.bottleneck-card .new-tag    { font-size: 9px; color: #ffd700; font-weight: 700; letter-spacing: 0.05em; }
.stage-header {
    font-size: 11px; color: #8893a8; text-transform: uppercase;
    letter-spacing: 0.08em; font-weight: 600; margin: 0 0 8px 4px;
    padding-bottom: 6px; border-bottom: 1px solid #2a2f3d;
}
.bet-card {
    background: #161a26; border-radius: 10px; padding: 14px;
    border: 1px solid #2a2f3d; margin-bottom: 12px;
}
.bet-card .ticker { font-size: 20px; font-weight: 800; color: #fff; }
.bet-card .layer  { font-size: 11px; color: #8893a8; }
.bet-card .score  { float: right; font-size: 13px; font-weight: 700; color: #ffd700; }
.bet-card .why    { font-size: 11px; color: #d0d4dc; margin-top: 8px; line-height: 1.4; }
</style>
""",
    unsafe_allow_html=True,
)

# Layers added in the April 2026 reconciliation — flagged in the UI
NEW_LAYERS = {
    "GOES (Electrical Steel)",
    "Skilled Electrical Labor",
    "Grid Interconnect Queue",
    "Large Power Transformers (LPT)",
    "Distribution Transformers",
    "ABF Dielectric Film",
    "HBM Hybrid Bonding",
    "EUV Mask Inspection / Pellicles",
    # Round 4 — colleague's grid-buildout pipeline + defense
    "Line Hardware & HVDC Cable",
    "Steel Poles & Towers",
    "Galvanizing",
    "Defense Adjacent",
    # Round 5 (Wave 9) — optics / networking expansion
    "Co-Packaged Optics (CPO)",
    "DPU / SmartNICs",
    "Active Electrical Cables (AEC)",
}

# ═════════════════════════════════════════════════════════════════════════════
# TOP HEADER — primary scenario controls (used to live in the sidebar)
# These need to be defined BEFORE run_model() so they're set up here, but
# rendered as a horizontal pill bar above the tabs further down the file.
# ═════════════════════════════════════════════════════════════════════════════

PRESETS = {
    "Stonehouse Base": {
        # 2026-04-29 audit: ai_users 1100→1400 (H2-25 aggregate weekly AI users
        # — OpenAI 800M + Gemini + Meta AI + Claude + Copilot); doubling 2.0→1.85
        # (Epoch AI Jun 2025 update); util 6.7%→9.0% (H2-25 ramp from agentic +
        # ChatGPT 800M weekly). Triangulates: 2030 supply 229 GW vs JLL/McK 200.
        "scenario": "Base", "ai_users": 1400, "agent_mult": 1.0, "humanoid": 1.0,
        "enterprise": 1.0, "doubling": 1.85, "util_2025": 0.090,
    },
    "Robotics Bull": {
        "scenario": "Robo Bull", "ai_users": 1600, "agent_mult": 1.4, "humanoid": 2.5,
        "enterprise": 1.3, "doubling": 1.85, "util_2025": 0.105,
    },
    "Adoption Bear": {
        "scenario": "Bear", "ai_users": 1000, "agent_mult": 0.7, "humanoid": 0.5,
        "enterprise": 0.8, "doubling": 2.25, "util_2025": 0.075,
    },
    "Aggressive Efficiency (1.5yr doubling)": {
        "scenario": "Base", "ai_users": 1400, "agent_mult": 1.0, "humanoid": 1.0,
        "enterprise": 1.0, "doubling": 1.5, "util_2025": 0.090,
    },
}

# Top header bar — bull/base/bear pills directly on page (no sidebar dig)
hdr_left, hdr_right = st.columns([1.3, 1.7])
with hdr_left:
    st.markdown(
        "<div style='font-size:11px; color:#8893a8; text-transform:uppercase; "
        "letter-spacing:0.08em; margin-bottom:2px;'>Macro Scenario · Demand vs Supply gap</div>",
        unsafe_allow_html=True,
    )
    macro_name = st.radio(
        "macro_top",
        list(MACRO_SCENARIOS.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="macro_name_top",
        help="Per colleague's v4_2 Efficiency Overlay. "
             "Bear = fast efficiency (gap closes ~2032). Bull = slow efficiency (gap never closes).",
    )
with hdr_right:
    st.markdown(
        "<div style='font-size:11px; color:#8893a8; text-transform:uppercase; "
        "letter-spacing:0.08em; margin-bottom:2px;'>Demand Preset · token + utilization mix</div>",
        unsafe_allow_html=True,
    )
    preset_name = st.radio(
        "preset_top",
        list(PRESETS.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="preset_name_top",
    )

macro_cfg = MACRO_SCENARIOS[macro_name]
preset = PRESETS[preset_name]
st.caption(
    f"<span style='color:#8893a8'>"
    f"<b style='color:#fff'>{macro_name}</b> · {macro_cfg['note']} &nbsp;|&nbsp; "
    f"<b style='color:#fff'>{preset_name}</b>"
    f"</span>",
    unsafe_allow_html=True,
)

# Global year scrubber — drives Flow Map AND Bottleneck Map (visible across tabs)
st.markdown(
    "<div style='font-size:11px; color:#8893a8; text-transform:uppercase; "
    "letter-spacing:0.08em; margin: 6px 0 2px 0;'>Map Year · drives flow + bottleneck color</div>",
    unsafe_allow_html=True,
)
year = st.slider(
    "year_top",
    min_value=2025, max_value=2042, value=2028, step=1,
    label_visibility="collapsed",
    key="year_top",
)
st.markdown("<div style='border-bottom:1px solid #2a2f3d; margin:8px 0 14px 0'></div>", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — fine-tune levers (advanced)
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("# AI Infra Supply Chain")
st.sidebar.caption("v2 · Stonehouse Capital · 2026-04-28")
st.sidebar.caption("_Macro & demand pills are at the top of the main page._")

st.sidebar.markdown("### Fleet Calibration")
anchor_gw = st.sidebar.slider(
    "2025 DC power anchor (GW)", 30.0, 90.0, 70.0, 1.0,
    help="Total global DC operational capacity early 2026. "
         "Triangulation across public reports: C&W 2024 base 63 + 2024-25 growth ≈ 70-72; "
         "JLL 2026 Outlook ~72; GS Feb 2025 65 op (+90 under construction); McKinsey 2024 ~70; "
         "DCD Q1-2025 ~68. Default 70 = mid-consensus. "
         "This is TOTAL DC capacity, broader than AI-only fleet.",
)
fleet_life = st.sidebar.slider(
    "Fleet replacement lag (years)", 3, 10, macro_cfg["lag"], 1,
    help="Years before installed base fully refreshes. "
         "Hyperscaler GPU refresh 4-5yr; enterprise 7-8yr; 6yr is weighted midpoint. "
         "Default tracks selected Macro Scenario.",
)
use_vintaged = st.sidebar.checkbox(
    "Vintaged fleet (layer model)", value=True,
    help="ON = layer-level model tracks each year's GPU additions as a separate cohort. "
         "OFF = naive instantaneous-efficiency model. The macro gap above always uses vintaged math.",
)

st.sidebar.markdown("### Key Levers")
doubling = st.sidebar.slider(
    "Efficiency doubling (years)", 1.0, 4.0, macro_cfg["doubling"], 0.05,
    help="Hardware efficiency doubling period. Epoch AI Jun 2025 update: ~21 months "
         "(revised from 24mo in 2024). H100→B200→B300 cadence is running faster than the prior trend. "
         "Lower = faster frontier gains. Default tracks selected Macro Scenario.",
)
util_2025 = st.sidebar.slider(
    "Inference utilization 2025 %",
    1.0, 20.0, round(preset["util_2025"] * 100, 1), 0.1,
    help="Pct of deployed AI fleet doing active inference. ~9% Q1-2026 (was 6.7% in 2024 — "
         "H2-25 ramp from agentic workloads + ChatGPT 800M weekly active). Used by layer-level model only.",
) / 100

st.sidebar.markdown("### Theme Exposure Filter")
st.sidebar.caption("Hide names where AI infra is too small a share of revenue to move the equity.")
min_exposure = st.sidebar.slider(
    "Minimum AI-infra exposure %", 0, 100, 25, 5,
    help="Pure-Play Score = composite × exposure %. Names below this threshold are filtered out of the rankings. "
         "CLF (6%) / Ajinomoto (4%) / Hitachi (10%) get hidden at 25% — re-include them by lowering the slider.",
)

with st.sidebar.expander("Advanced — supply phase rates"):
    sr1 = st.slider("2026-27 supply growth %", 5, 50, int(macro_cfg["supply_rates"][0] * 100), 1) / 100
    sr2 = st.slider("2028-30 supply growth %", 5, 50, int(macro_cfg["supply_rates"][1] * 100), 1) / 100
    sr3 = st.slider("2031-35 supply growth %", 5, 50, int(macro_cfg["supply_rates"][2] * 100), 1) / 100
    sr4 = st.slider("2036-42 supply growth %", 2, 30, int(macro_cfg["supply_rates"][3] * 100), 1) / 100
    supply_rates = (sr1, sr2, sr3, sr4)

with st.sidebar.expander("Advanced — token demand"):
    ai_users = st.slider(
        "AI Users 2025 (M)", 500, 2500, preset["ai_users"], 50,
        help="Aggregate weekly active AI users worldwide. H2-2025: OpenAI ~800M + Gemini + "
             "Meta AI + Claude consumer + Copilot embeds ≈ 1.4B. Was 1.1B in 2024 baseline.",
    )
    agent_mult = st.slider(
        "Agent Multiplier scale", 0.25, 3.0, preset["agent_mult"], 0.05,
        help="Rescales the Excel's enterprise-token curve, which already bakes in an agent "
             "multiplier ramp (2.5x in 2025 → 14.7x in 2040). 1.0 = trust the Stonehouse "
             "forecast as-is. <1.0 = slower agent adoption. >1.0 = faster.",
    )
    humanoid = st.slider(
        "Humanoid Robotics — scale", 0.1, 5.0, preset["humanoid"], 0.1,
        help="Multiplier on the Excel robotics token row ('Usage per day (token) (T's)') — "
             "humanoid fleet + AV inference + teleop streaming, applied to ALL years 2025-2042. "
             "1.0 = trust the Stonehouse forecast as-is. Slider is dampened: 2.0 = +40% to "
             "robotics tokens (not +100%), 0.5 = -20%. Robotics is <2% of total tokens today, "
             "so this lever mainly matters in the 2035+ tail when humanoid fleets become "
             "material (Optimus, Figure, Unitree, BD).",
    )
    enterprise = st.slider(
        "Enterprise + Retail Adoption — scale", 0.5, 2.0, preset["enterprise"], 0.1,
        help="Multiplier on BOTH the retail AND enterprise rows of the Excel forecast, applied "
             "linearly to all years (1.5 = +50% to both consumer and enterprise tokens). "
             "Captures depth of AI workflow integration — copilots per knowledge worker, "
             "queries per consumer per day, agents per enterprise function. Stacks "
             "multiplicatively with the Agent Multiplier slider above.",
    )

with st.sidebar.expander("Advanced — supply growth overrides"):
    custom_supply = {}
    for layer, meta in LAYERS.items():
        is_new = "*" if layer in NEW_LAYERS else ""
        v = st.slider(
            f"{is_new}{layer}",
            2, 80, int(meta["supply_growth_pct"] * 100), 1,
            key=f"sg_{layer}",
            help=meta["description"],
        )
        custom_supply[layer] = v / 100

# ═════════════════════════════════════════════════════════════════════════════
# MODEL RUN (cached)
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_data
def run_model(
    scenario, ai_users, agent_mult, humanoid, enterprise,
    doubling, util_2025, supply_tuple,
    use_vintaged, anchor_gw, fleet_life,
    supply_rates,
):
    tok = build_token_demand(
        scenario=scenario, ai_users_2025_M=ai_users,
        agent_multiplier_scale=agent_mult,
        humanoid_units_scale=humanoid,
        enterprise_intensity_scale=enterprise,
    )
    # Macro gap (colleague's framework — aggregate GW level)
    macro = build_macro_gap(
        tok,
        anchor_gw_2025=anchor_gw,
        efficiency_doubling_years=doubling,
        fleet_lag_years=fleet_life,
        supply_phase_rates=supply_rates,
    )
    # Layer-level model (granular drilldown)
    if use_vintaged:
        inf = build_infrastructure_demand_vintaged(
            tok,
            initial_anchor_gw=anchor_gw,
            efficiency_doubling_years=doubling,
            fleet_life_years=fleet_life,
            inference_utilization_2025=util_2025,
        )
    else:
        inf = build_infrastructure_demand(
            tok,
            efficiency_doubling_years=doubling,
            inference_utilization_2025=util_2025,
        )
    tight = build_tightness_scores(inf, custom_supply_growth=dict(supply_tuple))
    return tok, macro, inf, tight


tok_df, macro_df, inf_df, tight_df = run_model(
    preset["scenario"], ai_users, agent_mult, humanoid, enterprise,
    doubling, util_2025, tuple(custom_supply.items()),
    use_vintaged, anchor_gw, fleet_life, supply_rates,
)
inflection = power_inflection_year(inf_df)
gap_stats = gap_summary(macro_df)

# ═════════════════════════════════════════════════════════════════════════════
# TABS — Macro / Flow Map / Bottleneck Map / Easiest Bets
# Each tab block uses manual __enter__/__exit__ so we don't have to reindent
# 800+ lines of legacy rendering code. Streamlit's DeltaGenerator stack is
# updated by these calls the same way `with tab_x:` would.
# ═════════════════════════════════════════════════════════════════════════════
tab_macro, tab_flow, tab_map, tab_bets = st.tabs([
    "📊 Macro",
    "🔗 Flow Map",
    "🗺️ Bottleneck Map",
    "💰 Easiest Bets",
])

# ── TAB 1: Macro (gap chart, capex flow, fleet eff lag) ──────────────────────
tab_macro.__enter__()

st.markdown(
    "## AI Infrastructure Supply Chain "
    f"&nbsp;<span style='font-size:14px;color:#8893a8'>· {macro_name} × {preset_name}</span>",
    unsafe_allow_html=True,
)

# ═════════════════════════════════════════════════════════════════════════════
# MODEL ASSUMPTIONS PANEL — what "1.0×" means in absolute terms
# Lets a non-Excel auditor verify the curve at a glance. Pulls directly from
# the underlying Stonehouse "Token and Data Build Out.xlsx" Base sheet.
# ═════════════════════════════════════════════════════════════════════════════

@st.cache_data
def _assumptions_tables(scenario: str, ai_users_override_M: float):
    """Return three small DataFrames + a calc dict summarizing the model curves.

    Used by the Model Assumptions expander on the Macro tab. Reads the Excel
    once (cached) so the panel stays cheap on slider re-runs.
    """
    raw = load_excel_scenario(scenario)
    yrs_show = [2025, 2030, 2035, 2040]

    def _row(label, fmt="{:,.0f}", scale=1.0):
        try:
            return [fmt.format(float(raw.loc[label, y]) * scale) for y in yrs_show]
        except Exception:
            return ["—"] * len(yrs_show)

    # 1. Token demand drivers (with user override on AI Users 2025)
    USERS_ROW = "AI Users (M's)"   # Excel label has an apostrophe — bind to a var
    ROBOT_USE_ROW = "Usage per day (token) (T's)"
    base_users_2025 = float(raw.loc[USERS_ROW, 2025]) if USERS_ROW in raw.index else 1100.0
    user_scale = ai_users_override_M / base_users_2025
    ai_users_row = [f"{float(raw.loc[USERS_ROW, y]) * user_scale:,.0f}" for y in yrs_show]
    agent_mult_row = [f"{float(raw.loc['Agent Multiplier', y]):.1f}×" for y in yrs_show]
    tok_drivers = pd.DataFrame({
        "AI Users (M)": ai_users_row,
        "Knowledge Workers (M)": _row("Knowledge Workers (M)"),
        "Tokens / worker / day": _row("Tokens/worker per/day"),
        "Agent Multiplier": agent_mult_row,
        "Retail tokens (T/day)": _row("Retail", fmt="{:,.0f}", scale=user_scale),
        "Enterprise tokens (T/day)": _row("Enterprise Used Per Day (T)"),
        "Robotics tokens (T/day)": _row(ROBOT_USE_ROW, fmt="{:,.1f}"),
    }, index=[str(y) for y in yrs_show]).T

    # 2. Robotics fleet breakdown (M units)
    robot_fleet = pd.DataFrame({
        "Humanoid (M units)": _row("Humanoid", fmt="{:.2f}"),
        "AVs (M units)": _row("AV", fmt="{:.2f}"),
        "Industrial Robots (M units)": _row("Industrial Robot", fmt="{:.2f}"),
        "Pro Service Robots (M units)": _row("Prof Service Robots", fmt="{:.2f}"),
        "Home Robots (M units)": _row("Home Robots", fmt="{:.1f}"),
        "Small Drones (M units)": _row("Small Drones", fmt="{:.1f}"),
        "Total Fleet (M units)": _row("Total", fmt="{:.1f}"),
    }, index=[str(y) for y in yrs_show]).T

    return tok_drivers, robot_fleet


with st.expander(
    "🔍 **Model Assumptions** — what '1.0×' means in absolute terms (click to audit)",
    expanded=False,
):
    st.caption(
        "All sliders default to **1.0× = trust the Stonehouse Excel forecast as-is**. "
        "2025 is the baseline year — every curve anchors there and the multipliers compound through 2040. "
        "If you're unfamiliar with the underlying Excel, this is the at-a-glance audit."
    )

    tok_drivers_df, robot_fleet_df = _assumptions_tables(preset["scenario"], ai_users)

    col_a, col_b = st.columns([1.0, 1.0])
    with col_a:
        st.markdown("**Token Demand Drivers** (Excel `Base` sheet)")
        st.dataframe(tok_drivers_df, width="stretch", height=295)
        st.caption(
            "📌 The **Enterprise tokens** row is the *post-agent-multiplier* number we load — it grows "
            "85→14,719 T/day, a 173× ramp that already bakes in agents going from 2.5× to 14.7×. "
            "This is what calibrates the GW math to consensus (without it, demand collapses ~7×)."
        )
    with col_b:
        st.markdown("**Robotics Fleet Breakdown** (units, not tokens)")
        st.dataframe(robot_fleet_df, width="stretch", height=295)
        st.caption(
            "📌 Humanoids are **20K units in 2025** (Optimus, Figure, Unitree pilots) → 47.4M by 2040. "
            "They're <1% of robotics tokens today; the slider mainly stresses the 2035-2040 tail."
        )

    # "Your sliders" — what the user has dialed in right now vs default
    st.markdown("**Your current slider settings (vs default 1.0×)**")
    slider_cols = st.columns(5)
    slider_cols[0].metric("AI Users 2025", f"{ai_users:,}M",
                          delta=f"{(ai_users/1400 - 1)*100:+.0f}% vs Base 1,400M" if ai_users != 1400 else "Base", delta_color="off")
    slider_cols[1].metric("Agent Multiplier scale", f"{agent_mult:.2f}×",
                          delta=f"{(agent_mult-1)*100:+.0f}% vs default" if agent_mult != 1.0 else "Default", delta_color="off")
    slider_cols[2].metric("Humanoid Robotics scale", f"{humanoid:.2f}×",
                          delta=f"{(humanoid-1)*40:+.0f}% to robotics tokens" if humanoid != 1.0 else "Default (dampened)", delta_color="off")
    slider_cols[3].metric("Enterprise+Retail scale", f"{enterprise:.2f}×",
                          delta=f"{(enterprise-1)*100:+.0f}% to consumer+enterprise" if enterprise != 1.0 else "Default", delta_color="off")
    slider_cols[4].metric("Efficiency doubling", f"{doubling:.2f} yr",
                          delta="faster GPU efficiency = lower demand" if doubling < 1.85 else "slower = higher demand" if doubling > 1.85 else "Base (Epoch AI Jun-25)",
                          delta_color="off")

    st.caption(
        "**How the curves combine:** Enterprise tokens × Agent slider × Enterprise+Retail slider. "
        "Retail tokens × AI Users slider × Enterprise+Retail slider. "
        "Robotics tokens × Humanoid slider (dampened: 2.0× → +40%, not +100%). "
        "Then total cloud tokens get divided by fleet-weighted GPU efficiency to derive GW demand."
    )

# ═════════════════════════════════════════════════════════════════════════════
# SECTION 0 (NEW TOP): MACRO GAP — colleague's Efficiency Overlay framework
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("### Macro Gap · Demand vs Supply")
st.caption(
    "**Demand** = compute capacity needed after fleet-weighted efficiency gains absorb token growth. "
    "**Supply** = what physically gets built (transformer/turbine/grid lead-times bound supply growth). "
    "**Gap** is the order-book proxy: positive = transformer/turbine pricing power; "
    "negative = oversupply / fiber-optic moment. Sourced to JLL 2026 + Cushman & Wakefield + Epoch AI (see Excel notes 1-10)."
)

# Headline gap metrics
g1, g2, g3, g4, g5 = st.columns(5)
with g1:
    st.metric(
        "Peak Gap",
        f"{gap_stats['peak_gap_gw']:.0f} GW",
        delta=f"{gap_stats['peak_gap_pct']*100:.0f}% undersupplied @ {gap_stats['peak_gap_year']}",
        delta_color="off",
    )
with g2:
    st.metric(
        "Balance Year",
        str(gap_stats['balance_year']) if gap_stats['balance_year'] else "post-2042",
        delta="orders soften" if gap_stats['balance_year'] else "gap never closes",
        delta_color="off",
    )
with g3:
    st.metric(
        "Overshoot Begins",
        str(gap_stats['overshoot_year']) if gap_stats['overshoot_year'] else "post-2042",
        delta="fiber-optic moment" if gap_stats['overshoot_year'] else "no oversupply",
        delta_color="off",
    )
with g4:
    cum_2030 = float(macro_df.loc[2030, "cumulative_power_grid_capex_b"])
    st.metric("Power+Grid Capex thru 2030", f"${cum_2030:.0f}B")
with g5:
    st.metric(
        "Power+Grid Capex thru 2042",
        f"${gap_stats['cumulative_capex_2042_b']/1000:.1f}T",
        delta="cumulative",
        delta_color="off",
    )

# Three-curve chart: Demand / Supply / Gap
gap_fig = go.Figure()
gap_fig.add_trace(go.Scatter(
    x=YEARS, y=macro_df["demand_gw"], name="Demand (efficiency-adjusted)",
    line=dict(color="#3498db", width=3),
    hovertemplate="<b>%{x}</b><br>Demand: %{y:.0f} GW<extra></extra>",
))
gap_fig.add_trace(go.Scatter(
    x=YEARS, y=macro_df["supply_gw"], name="Supply (physical build pace)",
    line=dict(color="#2ecc71", width=3),
    hovertemplate="<b>%{x}</b><br>Supply: %{y:.0f} GW<extra></extra>",
))
gap_fig.add_trace(go.Scatter(
    x=YEARS, y=macro_df["gap_gw"], name="Gap (Demand − Supply)",
    line=dict(color="#e74c3c", width=2.5, dash="dot"),
    fill="tozeroy", fillcolor="rgba(231,76,60,0.10)",
    hovertemplate="<b>%{x}</b><br>Gap: %{y:+.0f} GW<extra></extra>",
))
# Annotate the inflections
if gap_stats["peak_gap_year"]:
    gap_fig.add_vline(
        x=gap_stats["peak_gap_year"], line_dash="dash", line_color="#e74c3c", opacity=0.5,
        annotation_text=f"Peak gap {gap_stats['peak_gap_gw']:.0f} GW",
        annotation_position="top right",
        annotation_font_color="#e74c3c",
    )
if gap_stats["balance_year"]:
    gap_fig.add_vline(
        x=gap_stats["balance_year"], line_dash="dash", line_color="#f1c40f", opacity=0.6,
        annotation_text=f"Balance {gap_stats['balance_year']}",
        annotation_position="top right",
        annotation_font_color="#f1c40f",
    )
if gap_stats["overshoot_year"]:
    gap_fig.add_vline(
        x=gap_stats["overshoot_year"], line_dash="dash", line_color="#2ecc71", opacity=0.6,
        annotation_text=f"Overshoot {gap_stats['overshoot_year']}",
        annotation_position="bottom right",
        annotation_font_color="#2ecc71",
    )
gap_fig.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1)
gap_fig.update_layout(
    height=360,
    yaxis_title="GW (global DC capacity)",
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
    legend=dict(orientation="h", y=-0.2, x=0),
    margin=dict(t=20, b=60, l=60, r=20),
    hovermode="x unified",
)
st.plotly_chart(gap_fig, width='stretch')

# Capex flow expander
with st.expander("Capex flow — what gets built ($B/yr to power & grid infrastructure)", expanded=False):
    st.caption(
        f"Cost basis: $11.3M/MW shell+core + $15M/MW AI fit-out × 50% AI workload share. "
        f"Power & grid takes 25% of total DC capex (per JLL/McKinsey). "
        f"**Flows to T10-T15 in your colleague's tier map** — gas turbines (GEV), substation (ETN/ABB/Hitachi), "
        f"line hardware (HUBB/NVT), galvanizing (AZZ — flagged missing from layer model), and grid components."
    )
    cap_fig = go.Figure()
    cap_fig.add_trace(go.Bar(
        x=YEARS, y=macro_df["annual_power_grid_capex_b"],
        name="Annual ($B)", marker_color="#e74c3c", opacity=0.85,
        hovertemplate="<b>%{x}</b><br>Annual: $%{y:.0f}B<extra></extra>",
    ))
    cap_fig.add_trace(go.Scatter(
        x=YEARS, y=macro_df["cumulative_power_grid_capex_b"],
        name="Cumulative ($B)", yaxis="y2",
        line=dict(color="#f1c40f", width=2.5),
        hovertemplate="<b>%{x}</b><br>Cumulative: $%{y:,.0f}B<extra></extra>",
    ))
    cap_fig.update_layout(
        height=320,
        yaxis=dict(title="Annual $B"),
        yaxis2=dict(title="Cumulative $B", overlaying="y", side="right"),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=10, b=60, l=60, r=60),
    )
    st.plotly_chart(cap_fig, width='stretch')

st.markdown("---")
st.markdown("#### Layer-level drilldown · which components hit pricing power within the gap")

m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    st.metric("Power 2025", f"{inf_df.loc[2025,'power_total_gw']:.0f} GW",
              delta="anchor")
with m2:
    pk_yr = int(inf_df["power_total_gw"].idxmax())
    st.metric("Peak Power", f"{inf_df['power_total_gw'].max():.0f} GW", delta=f"~{pk_yr}")
with m3:
    st.metric("Power Inflection", str(inflection or "post-2042"),
              delta="efficiency wins" if inflection else None,
              delta_color="off" if inflection else "normal")
with m4:
    if use_vintaged and "fleet_age_avg_yrs" in inf_df.columns:
        # Show the structural lag — most differentiated signal of the vintaged model
        peak_year = int(inf_df["power_total_gw"].idxmax())
        fr_peak = inf_df.loc[peak_year, "frontier_eff_tokens_per_kwh"] / 1e6
        bl_peak = inf_df.loc[peak_year, "fleet_blended_eff_tokens_per_kwh"] / 1e6
        lag_pct = (1 - bl_peak / fr_peak) * 100 if fr_peak else 0
        st.metric(f"Fleet eff lag @ {peak_year}", f"{lag_pct:.0f}%",
                  delta=f"frontier {fr_peak:.0f}M vs fleet {bl_peak:.0f}M tok/kWh",
                  delta_color="off")
    else:
        st.metric("Fleet eff lag", "—", delta="enable vintaged", delta_color="off")
with m5:
    fwd_avg = tight_df.loc[2027:2030].mean()
    tightest = fwd_avg.idxmax()
    st.metric("Tightest 2027-30", tightest.split(" ")[0][:14],
              delta=f"{fwd_avg.max():.0f}/100", delta_color="off")
with m6:
    n_pegged = (tight_df.loc[2027:2030].max() >= 90).sum()
    st.metric("Layers pegged 2027-30", f"{n_pegged}", delta=f"of {len(LAYERS)}")


# ═════════════════════════════════════════════════════════════════════════════
# FLEET-EFFICIENCY LAG CHART (vintaged-only — exposes the key insight)
# ═════════════════════════════════════════════════════════════════════════════
if use_vintaged and "fleet_blended_eff_tokens_per_kwh" in inf_df.columns:
    with st.expander("Frontier vs fleet-blended efficiency — why the inflection takes longer than the press release", expanded=False):
        st.caption(
            f"Frontier doubling every **{doubling:.2f}yr**, fleet life **{fleet_life}yr**. "
            "Frontier = newest GPU. Fleet-blended = MW-weighted average across all active vintages. "
            "The gap is durable structural power demand: when a hyperscaler announces a 2x-efficient new chip, "
            "the *deployed* fleet only gets a small fraction of that benefit — old vintages keep running until retirement."
        )
        eff_fig = go.Figure()
        eff_fig.add_trace(go.Scatter(
            x=YEARS, y=inf_df["frontier_eff_tokens_per_kwh"] / 1e6,
            name="Frontier (newest GPU)",
            line=dict(color="#3498db", width=2, dash="dash"),
        ))
        eff_fig.add_trace(go.Scatter(
            x=YEARS, y=inf_df["fleet_blended_eff_tokens_per_kwh"] / 1e6,
            name="Fleet blended (deployed)",
            line=dict(color="#e74c3c", width=3),
            fill="tonexty", fillcolor="rgba(231,76,60,0.10)",
        ))
        eff_fig.update_layout(
            height=280,
            yaxis_title="M tokens / kWh", yaxis_type="log",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
            legend=dict(orientation="h", y=-0.2),
            margin=dict(t=20, b=40, l=40, r=20),
        )
        st.plotly_chart(eff_fig, width='stretch')


# Year scrubber lives in the global header above the tabs (line ~190); the
# value `year` is already set there and visible across all tabs.

# ═════════════════════════════════════════════════════════════════════════════
# Close TAB 1 (Macro) — open TAB 2 (Flow Map)
# ═════════════════════════════════════════════════════════════════════════════
tab_macro.__exit__(None, None, None)
tab_flow.__enter__()


# ═════════════════════════════════════════════════════════════════════════════
# FLOW VISUALIZATION — How AI demand becomes physical infrastructure
# Three layers of interactivity on top of the year scrubber:
#   1. Hover tooltips on each chevron stage (CSS, no Python round-trip)
#   2. Stage-picker radio that opens a drill-down panel with linked tiers + tickers
#   3. Plotly Sankey showing multi-source flow with native hover/zoom/drag
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"### How AI demand becomes physical infrastructure · {year}")
st.caption(
    "Read left to right. Each box is the next step the demand has to pass through to "
    "actually run. **Hover** any box for the explainer · **pick a stage below** to drill in · "
    "**scroll down** for the multi-source Sankey flow (drag/zoom/hover)."
)


def _fmt_big(v: float) -> str:
    """Format a number with K/M/B/T suffix."""
    av = abs(v)
    if av >= 1e12: return f"{v/1e12:.1f}T"
    if av >= 1e9:  return f"{v/1e9:.1f}B"
    if av >= 1e6:  return f"{v/1e6:.1f}M"
    if av >= 1e3:  return f"{v/1e3:.1f}K"
    if av >= 10:   return f"{v:.0f}"
    return f"{v:.1f}"


def hex_to_rgba(hex_color: str, alpha: float = 0.18) -> str:
    """Convert #rrggbb hex to rgba(r,g,b,alpha) for Plotly fill."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(150,150,150,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# Pull live values for selected year + 2025 baseline (for delta)
def _vals(yr):
    return {
        "users":   ai_users * 1e6 * (1.30 ** (yr - 2025)),
        "tokens":  float(tok_df.loc[yr, "total_T"]),
        "compute": float(inf_df.loc[yr, "total_compute_gw"]),
        # HBM TB grows monotonically with compute (GPU memory wall thesis).
        # Server count is intentionally NOT used here because rack density
        # rises so fast that unit count can decline while capability grows —
        # confusing for a left-to-right narrative read.
        "memory":  float(inf_df.loc[yr, "hbm_tb"]),
        "power":   float(inf_df.loc[yr, "power_total_gw"]),
    }

vY = _vals(year)
v0 = _vals(2025)
y_twh_yr = vY["power"] * 8760 * 0.80 / 1000  # 80% load factor → TWh/yr

# Stage definitions with full tooltip + drill-down content.
# Each stage: (key, label, value, sub, color, track, tooltip_lines, linked_layers, top_tickers)
STAGE_DEFS = [
    {
        "key": "USERS", "label": "USERS",
        "value": _fmt_big(vY["users"]), "sub": "AI users worldwide",
        "color": "#27ae60", "track": "demand",
        "explain": "Humans + agents + robots generating AI requests. The user count compounds at ~30%/yr through 2030 in the base case. This is the demand-side root cause of every downstream bottleneck.",
        "v0": _fmt_big(v0["users"]), "delta_pct": (vY["users"]/v0["users"] - 1) * 100,
        "linked_tiers": ["T6 Hyperscalers (demand-side, not modeled as supply)"],
        "top_tickers": [("GOOG/MSFT/META", "frontier model labs"), ("AMZN/AAPL", "consumer + cloud distribution")],
    },
    {
        "key": "TOKENS", "label": "TOKENS",
        "value": f"{vY['tokens']:.0f}T/day", "sub": "tokens generated",
        "color": "#16a085", "track": "demand",
        "explain": f"Each user request breaks into ~1,000 tokens. {vY['tokens']:.0f}T/day = {vY['tokens']*1e12/86400/1e9:.1f}B tokens/sec globally. ~99.9% are cloud-served; edge tokens are tiny but growing with humanoid robotics.",
        "v0": f"{v0['tokens']:.0f}T/day", "delta_pct": (vY["tokens"]/v0["tokens"] - 1) * 100,
        "linked_tiers": ["T6 demand → drives all downstream"],
        "top_tickers": [("Retail", f"{tok_df.loc[year,'retail_T']:.0f}T"), ("Enterprise", f"{tok_df.loc[year,'enterprise_T']:.0f}T"), ("Robotics", f"{tok_df.loc[year,'robotics_cloud_T']+tok_df.loc[year,'robotics_edge_T']:.1f}T")],
    },
    {
        "key": "COMPUTE", "label": "COMPUTE",
        "value": f"{vY['compute']:.0f} GW", "sub": "active compute",
        "color": "#8e44ad", "track": "silicon",
        "explain": f"GW of running AI compute hardware. Translates tokens/day into chip throughput via fleet-blended efficiency ({inf_df.loc[year,'fleet_blended_eff_tokens_per_kwh']/1e6:.1f}M tokens/kWh in {year}). The frontier doubles every ~2yr; the deployed fleet trails by ~6yr.",
        "v0": f"{v0['compute']:.0f} GW", "delta_pct": (vY["compute"]/max(v0["compute"],0.01) - 1) * 100,
        "linked_tiers": ["T2 Semicon Equipment (Fab, EUV, Hybrid Bonding)", "T3 EDA + Design", "T4 Foundries / Memory / Packaging"],
        "top_tickers": [("NVDA", "GPU dominant"), ("AVGO", "custom XPU"), ("TSM", "leading-edge foundry"), ("BESI", "hybrid bonding"), ("ASML", "EUV monopoly")],
    },
    {
        "key": "HARDWARE", "label": "HARDWARE",
        "value": f"{vY['memory']/1000:.1f} PB", "sub": "HBM memory installed",
        "color": "#2980b9", "track": "silicon",
        "explain": f"Petabytes of high-bandwidth memory wired to the GPUs. Memory bandwidth — not raw compute — is the real bottleneck for inference throughput. HBM tightness drives the supply chain story (Ajinomoto ABF, BESI hybrid bonding, MU/Hynix/Samsung).",
        "v0": f"{v0['memory']/1000:.1f} PB", "delta_pct": (vY["memory"]/max(v0["memory"],0.01) - 1) * 100,
        "linked_tiers": ["T4 HBM / Substrates / ABF Film", "T5 Networking + Optics + Connectors + Fiber"],
        "top_tickers": [("MU", "HBM US monopoly"), ("Ajinomoto", "ABF film monopoly"), ("APH", "high-speed connectors"), ("COHR/LITE", "800G/1.6T optics"), ("GLW", "fiber")],
    },
    {
        "key": "FACILITY", "label": "FACILITY",
        "value": f"{vY['power']:.0f} GW", "sub": "data center capacity",
        "color": "#16a085", "track": "dc",
        "explain": f"Operational DC power capacity to host the hardware. Includes IT load + cooling + losses. {inf_df.loc[year,'cooling_gw']:.0f} GW of that is dedicated cooling. Build cycle 30-48 months — labor and grid interconnect are the binding constraints.",
        "v0": f"{v0['power']:.0f} GW", "delta_pct": (vY["power"]/v0["power"] - 1) * 100,
        "linked_tiers": ["T7 DC Real Estate & Build", "T8 Cooling & Power Distribution"],
        "top_tickers": [("EQIX/DLR", "co-lo REITs"), ("VRT", "liquid cooling leader"), ("FIX/PWR", "DC contractors"), ("ETN", "power distribution")],
    },
    {
        "key": "ENERGY", "label": "ENERGY",
        "value": f"{y_twh_yr:.0f} TWh/yr", "sub": f"grid power drawn",
        "color": "#c0392b", "track": "power",
        "explain": f"Electricity actually consumed. {vY['power']:.0f} GW × 8760h × 80% load factor = {y_twh_yr:.0f} TWh/yr — roughly {y_twh_yr/4000*100:.0f}% of US 2024 grid output. Generation, GOES (sole-source US), transformers, and grid interconnect are the slow-build chokepoints.",
        "v0": f"{v0['power']*8760*0.80/1000:.0f} TWh/yr", "delta_pct": (vY["power"]/v0["power"] - 1) * 100,
        "linked_tiers": ["T9 On-site Power & Backup", "T11 Transformers & GOES", "T12-T14 Line Hardware / Poles / Galvanizing", "T15 Defense Adjacent"],
        "top_tickers": [("GEV/SE/Hitachi", "turbines + grid"), ("CEG/TLN", "behind-the-meter nuclear"), ("CLF", "GOES sole-source US"), ("VMI/ACA/AZZ", "poles + galvanizing duopoly")],
    },
]

# CSS for chevron flow with hover tooltips
flow_css = """
<style>
.flow-row {
  display: flex; align-items: stretch; gap: 0; margin: 12px 0 8px 0;
  width: 100%; overflow-x: auto;
}
.flow-stage {
  flex: 1; min-width: 0; padding: 14px 16px 14px 22px;
  position: relative; color: #fff; cursor: help;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 50%, calc(100% - 14px) 100%, 0 100%, 14px 50%);
  transition: filter 0.15s ease;
}
.flow-stage:hover { filter: brightness(1.18); }
.flow-stage:first-child {
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 50%, calc(100% - 14px) 100%, 0 100%);
  padding-left: 16px;
}
.flow-stage:last-child {
  clip-path: polygon(0 0, 100% 0, 100% 100%, 0 100%, 14px 50%);
}
.flow-label { font-size: 10px; font-weight: 700; letter-spacing: 0.10em;
              text-transform: uppercase; color: rgba(255,255,255,0.85); margin-bottom: 4px; }
.flow-value { font-size: 22px; font-weight: 800; color: #fff; line-height: 1.05; }
.flow-sub   { font-size: 10px; color: rgba(255,255,255,0.85); margin-top: 4px; line-height: 1.25; }
.flow-delta {
  position: absolute; top: 6px; right: 18px;
  font-size: 9px; font-weight: 700; letter-spacing: 0.04em;
  background: rgba(0,0,0,0.30); padding: 1px 6px; border-radius: 8px;
  color: rgba(255,255,255,0.95);
}
</style>
"""

flow_html = flow_css + "<div class='flow-row'>"
for s in STAGE_DEFS:
    delta = s["delta_pct"]
    delta_str = f"+{delta:.0f}%" if delta >= 0 else f"{delta:.0f}%"
    # Native HTML title tooltip — keep on one line (no \n\n which Streamlit's markdown renderer converts to <p>)
    tooltip = (
        f"{s['label']} ({year}) — {s['explain']} "
        f"·· 2025: {s['v0']} → {year}: {s['value']} ({delta_str})"
    ).replace('"', "'")  # safety: escape any embedded double-quotes in the explanation
    flow_html += (
        f"<div class='flow-stage' style='background:{s['color']}' title=\"{tooltip}\">"
        f"<div class='flow-delta'>{delta_str}</div>"
        f"<div class='flow-label'>{s['label']}</div>"
        f"<div class='flow-value'>{s['value']}</div>"
        f"<div class='flow-sub'>{s['sub']}</div>"
        "</div>"
    )
flow_html += "</div>"
# Important: avoid blank lines inside flow_html — st.markdown's preprocessor turns
# them into <p> tags that escape angle brackets in attribute values.
st.markdown(flow_html.replace("\n\n", "\n"), unsafe_allow_html=True)

# ── Drill-down picker — pick a stage to expand details ─────────────────────────
drill = st.radio(
    "Drill into a stage",
    options=[s["key"] for s in STAGE_DEFS],
    horizontal=True, label_visibility="collapsed",
    key="flow_drill",
)
sel = next(s for s in STAGE_DEFS if s["key"] == drill)

dc1, dc2, dc3 = st.columns([1.0, 1.4, 1.6])
with dc1:
    st.markdown(
        f"<div style='background:{sel['color']}; padding:14px; border-radius:8px; color:#fff;'>"
        f"<div style='font-size:10px; letter-spacing:0.1em; opacity:0.85'>{sel['label']} · {year}</div>"
        f"<div style='font-size:28px; font-weight:800; margin-top:4px'>{sel['value']}</div>"
        f"<div style='font-size:11px; opacity:0.85; margin-top:2px'>{sel['sub']}</div>"
        f"<div style='font-size:11px; margin-top:10px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.20);'>"
        f"<b>2025:</b> {sel['v0']}<br/>"
        f"<b>Δ since 2025:</b> {'+' if sel['delta_pct']>=0 else ''}{sel['delta_pct']:.0f}%"
        f"</div></div>",
        unsafe_allow_html=True,
    )
with dc2:
    st.markdown(f"**What it is**\n\n{sel['explain']}")
    st.markdown(f"**Linked supply-chain tiers**")
    for t in sel["linked_tiers"]:
        st.markdown(f"- {t}")
with dc3:
    st.markdown("**Primary tickers in this stage**")
    for tk, why in sel["top_tickers"]:
        st.markdown(f"- **{tk}** — {why}")

# ── Plotly Sankey — multi-source flow with native interactivity ────────────────
st.markdown("#### Multi-source flow · Sankey · drag / hover / zoom")
st.caption(
    "Where the demand actually comes from and how it propagates. Hover any link to see "
    "real values. The widths are normalized to share-of-total at each stage."
)

# Build sankey with normalized share-of-total widths (so widths are comparable across stages)
retail_T   = float(tok_df.loc[year, "retail_T"])
ent_T      = float(tok_df.loc[year, "enterprise_T"])
robo_clT   = float(tok_df.loc[year, "robotics_cloud_T"])
robo_edT   = float(tok_df.loc[year, "robotics_edge_T"])
total_T    = max(retail_T + ent_T + robo_clT + robo_edT, 0.01)

# Each link scaled to 100 = full demand at that stage
sk_retail = (retail_T   / total_T) * 100
sk_ent    = (ent_T      / total_T) * 100
sk_robo_c = (robo_clT   / total_T) * 100
sk_robo_e = (robo_edT   / total_T) * 100
sk_cloud  = (retail_T + ent_T + robo_clT) / total_T * 100
sk_edge   = (robo_edT) / total_T * 100

# Compute through DC through power — these always carry ~100% of demand
sk_compute_in  = sk_cloud + sk_edge * 0.05  # edge mostly stays edge; tiny cloud spillover
sk_dc_in       = sk_compute_in
sk_power_in    = sk_dc_in

sk_node_labels = [
    f"Retail Users ({retail_T:.0f}T tok/day)",            # 0 green
    f"Enterprise + Agents ({ent_T:.0f}T tok/day)",        # 1 green
    f"Robotics ({robo_clT+robo_edT:.2f}T tok/day)",       # 2 green
    f"Cloud Tokens ({retail_T+ent_T+robo_clT:.0f}T)",     # 3 teal
    f"Edge Tokens ({robo_edT:.2f}T)",                     # 4 teal
    f"Active Compute ({vY['compute']:.0f} GW)",           # 5 purple
    f"DC Capacity ({vY['power']:.0f} GW)",                # 6 blue
    f"Power Drawn ({y_twh_yr:.0f} TWh/yr)",               # 7 red
]
sk_node_colors = ["#27ae60", "#27ae60", "#27ae60",
                  "#16a085", "#16a085",
                  "#8e44ad", "#2980b9", "#c0392b"]

sk_sources = [0, 1, 2, 2, 3, 4, 5, 6]
sk_targets = [3, 3, 3, 4, 5, 5, 6, 7]
sk_values  = [sk_retail, sk_ent, sk_robo_c, sk_robo_e, sk_cloud, sk_edge * 0.05, sk_dc_in, sk_power_in]
sk_link_colors = ["rgba(39,174,96,0.35)"] * 4 + ["rgba(22,160,133,0.35)"] * 2 + ["rgba(142,68,173,0.35)", "rgba(192,57,43,0.45)"]
sk_hover_link = [
    f"Retail users → Cloud tokens<br>{retail_T:.1f}T tokens/day ({sk_retail:.1f}% of demand)",
    f"Enterprise + agents → Cloud tokens<br>{ent_T:.1f}T tokens/day ({sk_ent:.1f}% of demand)",
    f"Robotics → Cloud tokens (humanoid teleop)<br>{robo_clT:.2f}T tokens/day",
    f"Robotics → Edge tokens (on-device)<br>{robo_edT:.2f}T tokens/day",
    f"Cloud tokens → Active compute<br>{retail_T+ent_T+robo_clT:.0f}T tokens routed to data centers",
    f"Edge → Cloud spillover<br>marginal cross-traffic from edge devices",
    f"Compute → DC capacity<br>{vY['compute']:.0f} GW IT load fits in {vY['power']:.0f} GW facility (cooling overhead)",
    f"DC → Grid power drawn<br>{y_twh_yr:.0f} TWh/yr at 80% load factor",
]

sankey_fig = go.Figure(go.Sankey(
    arrangement="snap",
    node=dict(
        pad=18, thickness=22,
        line=dict(color="#0e1117", width=0.5),
        label=sk_node_labels,
        color=sk_node_colors,
        hovertemplate="<b>%{label}</b><extra></extra>",
    ),
    link=dict(
        source=sk_sources, target=sk_targets, value=sk_values,
        color=sk_link_colors,
        customdata=sk_hover_link,
        hovertemplate="%{customdata}<extra></extra>",
    ),
))
sankey_fig.update_layout(
    height=360,
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
    font=dict(color="#e0e3eb", size=11),
    margin=dict(t=10, b=10, l=10, r=10),
)
st.plotly_chart(sankey_fig, width='stretch', key=f"sankey_{year}")

st.caption(
    "**The compounding ratio:** every doubling of users at the left forces a roughly proportional "
    "doubling of every stage to the right. The bottleneck cards below show which of those doublings "
    "are physically deliverable on time — and which become pricing-power moments for the suppliers."
)


# ═════════════════════════════════════════════════════════════════════════════
# BUBBLE EXPLORER — interactive stock map per drill-down stage
# Bubble size = market cap; X = AI exposure %; Y = composite tightness × tier
# weight; color = supply-chain track. Hover gives the rationale.
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"### Stocks in this stage · **{sel['label']}** · {year}")
st.caption(
    "Each bubble = one ticker exposed to this stage's layers. **Size = market cap** "
    "(USD billions, mid-2026 estimate — refresh from Bloomberg before sizing positions). "
    "**X = AI-infra revenue exposure**. **Y = layer tightness × role weight** (P=1.0, S=0.6, K=0.3) "
    "— picks the strongest single-layer exposure within this stage. **Color = supply-chain track**. "
    "Hover for rationale."
)

# Map drill-down stage key → list of supply-chain layers
STAGE_TO_LAYERS = {
    "USERS": [],
    "TOKENS": [],
    "COMPUTE": [
        "Fab Equipment", "EUV Mask Inspection / Pellicles", "EDA Tools / IP",
        "CoWoS / Advanced Packaging", "HBM Hybrid Bonding",
        "GPU / AI Accelerators", "HBM Memory", "CPU / Host Processors",
        "Server DRAM", "Advanced Substrates / PCB", "ABF Dielectric Film",
    ],
    "HARDWARE": [
        "Scale-Out Networking Silicon", "Co-Packaged Optics (CPO)",
        "DPU / SmartNICs", "Optical Transceivers",
        "Active Electrical Cables (AEC)", "Fiber / Physical Cabling",
        "High-Speed Connectors",
    ],
    "FACILITY": [
        "Liquid Cooling", "UPS / Backup Power", "Data Center Construction",
        "DC REITs / Co-lo", "Skilled Electrical Labor",
    ],
    "ENERGY": [
        "Power Generation", "Grid Interconnect Queue", "GOES (Electrical Steel)",
        "Large Power Transformers (LPT)", "Distribution Transformers",
        "Line Hardware & HVDC Cable", "Steel Poles & Towers", "Galvanizing",
        "Defense Adjacent",
    ],
}

stage_layers = [L for L in STAGE_TO_LAYERS.get(drill, []) if L in tight_df.columns]
if not stage_layers:
    st.info("This stage is demand-side (users/tokens) — no supply layers attach. Pick COMPUTE / HARDWARE / FACILITY / ENERGY.")
else:
    _tier_w = {"P": 1.0, "S": 0.6, "K": 0.3}
    _bubble_rows = []
    _seen = set()
    for layer in stage_layers:
        layer_score = float(tight_df.loc[year, layer])
        for ticker, tier, why in LAYER_NAMES_DETAIL.get(layer, []):
            if ticker in _seen:
                # If a ticker appears in multiple layers in this stage, keep the strongest
                existing = next(r for r in _bubble_rows if r["ticker"] == ticker)
                this_y = layer_score * _tier_w.get(tier, 0.3)
                if this_y > existing["y"]:
                    existing.update({
                        "y": this_y, "layer": layer, "tier": tier, "why": why,
                        "tightness": layer_score,
                    })
                continue
            _seen.add(ticker)
            track = LAYER_TIER.get(layer, ("—", "—"))[1]
            _bubble_rows.append({
                "ticker": ticker,
                "layer": layer,
                "tier": tier,
                "why": why,
                "tightness": layer_score,
                "y": layer_score * _tier_w.get(tier, 0.3),
                "exposure": theme_exposure_pct(ticker),
                "mcap": market_cap_b(ticker),
                "track": track,
                "monopoly": ticker in MONOPOLY_TICKERS,
                "pivotal": ticker in PIVOTAL_TICKERS,
            })

    bubble_df = pd.DataFrame(_bubble_rows)

    # Build hover text — full rationale + market cap + flags
    def _fmt_mcap(b):
        if b >= 1000: return f"${b/1000:.2f}T"
        if b >= 10:   return f"${b:.0f}B"
        return f"${b:.1f}B"

    bubble_df["hover"] = bubble_df.apply(
        lambda r: (
            f"<b>{'★ ' if r['pivotal'] else ''}{r['ticker']}</b>"
            f"{' · SOLE-SOURCE' if r['monopoly'] else ''}<br>"
            f"<b>Layer:</b> {r['layer']} ({r['tier']}-tier)<br>"
            f"<b>Market cap:</b> {_fmt_mcap(r['mcap'])}<br>"
            f"<b>AI exposure:</b> {r['exposure']}%<br>"
            f"<b>Layer tightness {year}:</b> {r['tightness']:.0f}/100<br>"
            f"<b>Score (tightness × role):</b> {r['y']:.0f}<br><br>"
            f"<i>{r['why']}</i>"
        ),
        axis=1,
    )

    bubble_fig = go.Figure()
    for track, color in TRACK_COLOR.items():
        sub = bubble_df[bubble_df["track"] == track]
        if sub.empty:
            continue
        bubble_fig.add_trace(go.Scatter(
            x=sub["exposure"],
            y=sub["y"],
            mode="markers+text",
            marker=dict(
                size=np.sqrt(sub["mcap"]) * 4 + 10,
                sizemode="diameter",
                color=color,
                opacity=0.75,
                line=dict(width=1.2, color="rgba(255,255,255,0.55)"),
            ),
            text=sub["ticker"],
            textposition="middle center",
            textfont=dict(size=9, color="#fff"),
            name=track,
            customdata=sub["hover"],
            hovertemplate="%{customdata}<extra></extra>",
        ))
    bubble_fig.add_vline(x=50, line_color="rgba(255,255,255,0.15)", line_dash="dot",
                         annotation_text="50% exposure", annotation_position="top")
    bubble_fig.add_hline(y=70, line_color="rgba(231,76,60,0.30)", line_dash="dot",
                         annotation_text="tight", annotation_position="right")
    bubble_fig.update_layout(
        height=520,
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font_color="white",
        xaxis=dict(
            title="AI-infra revenue exposure (%)",
            range=[-3, 105], gridcolor="rgba(255,255,255,0.08)",
        ),
        yaxis=dict(
            title=f"Tightness × role weight ({year})",
            range=[-3, 105], gridcolor="rgba(255,255,255,0.08)",
        ),
        legend=dict(orientation="h", y=-0.12),
        margin=dict(t=10, b=60, l=60, r=20),
        hoverlabel=dict(bgcolor="#161a26", font_size=11, font_color="white", bordercolor="#2a2f3d"),
    )
    st.plotly_chart(bubble_fig, width='stretch', key=f"bubble_{drill}_{year}")
    st.caption(
        f"_{len(bubble_df)} tickers across {len(stage_layers)} layer(s) in this stage. "
        f"Top-right quadrant (high exposure × high tightness) is where mispricing concentrates. "
        f"Bubble area scales with √(market cap) so micro-caps stay visible against mega-caps._"
    )


# ═════════════════════════════════════════════════════════════════════════════
# SUPPLY-CHAIN NARRATIVE — vertical waterfall walking the full chain.
# At every stage: layers + tickers (with $market cap) + tightness pill.
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown(f"### Supply-Chain Narrative · who plays at every stage · {year}")
st.caption(
    "Top-to-bottom walk through the entire AI infrastructure chain. **Each stage** = one layer of "
    "the build-out (compute → memory → packaging → networking → DC → power → grid). **Ticker chips** "
    "are sized/sorted by market cap (mega caps first); **★** = pivotal in our research; **§** = sole-source. "
    "**Color of the chip** = AI-infra revenue exposure (green = pure-play). **Tightness pill** = "
    "supply tension in the selected year."
)


# ─── 🔍 Ticker Inspector — pick any ticker, see what it does + every layer it touches ───
def _fmt_cap(b: float) -> str:
    if b >= 1000: return f"${b/1000:.1f}T"
    if b >= 10:   return f"${b:.0f}B"
    if b >= 1:    return f"${b:.1f}B"
    return f"${b*1000:.0f}M"


_all_tickers_map = all_tickers_with_layers()
_inspector_options = sorted(
    _all_tickers_map.keys(),
    key=lambda t: (-market_cap_b(t), -theme_exposure_pct(t), t),
)
_inspector_labels = ["— pick a ticker —"] + [
    f"{t} · {_fmt_cap(market_cap_b(t))} · {theme_exposure_pct(t)}% AI"
    for t in _inspector_options
]
_label_to_tk = dict(zip(_inspector_labels[1:], _inspector_options))

st.markdown(
    "<div style='background: rgba(255, 215, 0, 0.04); border: 1px solid rgba(255, 215, 0, 0.20); "
    "border-radius:10px; padding: 12px 16px; margin: 12px 0;'>"
    "<div style='font-size:13px; font-weight:700; color:#ffd700; margin-bottom:6px;'>"
    "🔍 Ticker Inspector"
    "</div>"
    "<div style='font-size:11px; color:#8893a8; margin-bottom:8px;'>"
    "Pick any ticker (179 names, sorted by market cap × AI exposure) to see what the company does and every supply-chain layer it touches."
    "</div>"
    "</div>",
    unsafe_allow_html=True,
)

inspector_pick = st.selectbox(
    "ticker_inspector",
    _inspector_labels,
    index=0,
    label_visibility="collapsed",
    key="ticker_inspector",
)

if inspector_pick and inspector_pick != "— pick a ticker —":
    ins_tk = _label_to_tk[inspector_pick]
    ins_mcap = market_cap_b(ins_tk)
    ins_exp  = theme_exposure_pct(ins_tk)
    ins_blurb = company_blurb(ins_tk)
    ins_layers = _all_tickers_map.get(ins_tk, [])
    ins_pivotal = ins_tk in PIVOTAL_TICKERS
    ins_sole    = ins_tk in MONOPOLY_TICKERS

    # Compute aggregate signal across all layers the ticker touches
    fwd = tight_df.loc[2027:2030].mean()
    layer_summaries = []
    for layer, role, why in ins_layers:
        if layer not in tight_df.columns:
            continue
        score_now = float(tight_df.loc[year, layer])
        score_fwd = float(fwd[layer])
        sc_tier, sc_track = LAYER_TIER.get(layer, ("—", "—"))
        layer_summaries.append({
            "layer": layer, "role": role, "why": why,
            "tier": sc_tier, "track": sc_track,
            "score_now": score_now, "score_fwd": score_fwd,
            "color": LAYERS.get(layer, {}).get("color", "#888"),
        })
    layer_summaries.sort(key=lambda r: (-r["score_fwd"]))

    # Top header card
    flag_html = ""
    if ins_pivotal:
        flag_html += "<span style='color:#ffd700; font-weight:700; font-size:13px; margin-right:6px;'>★ PIVOTAL</span>"
    if ins_sole:
        flag_html += "<span style='color:#ffd700; font-weight:700; font-size:13px; margin-right:6px;'>§ SOLE-SOURCE</span>"

    blurb_html = (
        f"<div style='font-size:13px; color:#d0d4dc; line-height:1.55; margin: 8px 0 0 0;'>{ins_blurb}</div>"
        if ins_blurb
        else "<div style='font-size:11px; color:#8893a8; font-style:italic; margin: 8px 0 0 0;'>"
             "_No company blurb on file — see per-layer rationale below for what this ticker does in this chain._"
             "</div>"
    )
    st.markdown(
        f"""
        <div style='background:#161a26; border-radius:10px; padding:18px 22px; margin: 8px 0 4px 0;
                    border:1px solid #2a2f3d;'>
          <div style='display:flex; justify-content:space-between; align-items:flex-start; gap:18px;'>
            <div style='flex:1.2;'>
              <div style='font-size:24px; font-weight:800; color:#fff;'>
                {ins_tk}
              </div>
              <div style='margin-top:4px;'>{flag_html}</div>
              {blurb_html}
            </div>
            <div style='text-align:right;'>
              <div style='font-size:10px; color:#8893a8; letter-spacing:0.06em; text-transform:uppercase; font-weight:700;'>Market Cap</div>
              <div style='font-size:22px; font-weight:800; color:#fff; margin-bottom:8px;'>{_fmt_cap(ins_mcap)}</div>
              <div style='font-size:10px; color:#8893a8; letter-spacing:0.06em; text-transform:uppercase; font-weight:700;'>AI-Infra Exposure</div>
              <div style='font-size:22px; font-weight:800;
                          color:{"#27ae60" if ins_exp >= 70 else ("#d4ac0d" if ins_exp >= 35 else "#e67e22")};'>
                {ins_exp}%
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Layer plays
    st.markdown(
        f"<div style='font-size:13px; font-weight:700; color:#fff; margin: 14px 0 6px 4px;'>"
        f"Plays in {len(layer_summaries)} supply-chain layer{'s' if len(layer_summaries) != 1 else ''}"
        f"</div>",
        unsafe_allow_html=True,
    )

    if not layer_summaries:
        st.info("No mapped supply-chain layers for this ticker.")
    else:
        for ls in layer_summaries:
            track_pill_color = TRACK_COLOR.get(ls["track"], "#666")
            role_label = {"P": "PRIMARY", "S": "SECONDARY", "K": "KICKER"}.get(ls["role"], ls["role"])
            score_color = (
                "#7a1d1d" if ls["score_fwd"] >= 85 else
                "#9c2a2a" if ls["score_fwd"] >= 70 else
                "#b85c1f" if ls["score_fwd"] >= 55 else
                "#9a7a1a" if ls["score_fwd"] >= 40 else
                "#3d6f30" if ls["score_fwd"] >= 25 else
                "#1f4530"
            )
            st.markdown(
                f"""
                <div style='background:#0e1117; border-left:3px solid {ls['color']};
                            border-radius:6px; padding:10px 14px; margin: 6px 0;'>
                  <div style='display:flex; justify-content:space-between; align-items:center;
                              margin-bottom:6px; gap:8px; flex-wrap:wrap;'>
                    <div style='flex:1; min-width:200px;'>
                      <span style='font-size:9px; color:#8893a8; font-weight:700; letter-spacing:0.05em;
                                   margin-right:6px;'>{ls['tier']}</span>
                      <span style='font-size:13px; font-weight:600; color:#fff;'>{ls['layer']}</span>
                      <span style='background:{track_pill_color}; color:#fff; font-size:9px;
                                   padding:1px 6px; border-radius:6px; font-weight:700;
                                   letter-spacing:0.04em; margin-left:8px;'>{ls['track']}</span>
                      <span style='background:rgba(255,215,0,0.12); color:#ffd700; font-size:9px;
                                   padding:1px 6px; border-radius:6px; font-weight:700;
                                   letter-spacing:0.04em; margin-left:4px;'>{role_label}</span>
                    </div>
                    <div style='text-align:right;'>
                      <span style='background:{score_color}; color:#fff; padding:2px 8px;
                                   border-radius:10px; font-size:10px; font-weight:700; margin-right:4px;'>
                        2027-30 · {int(ls['score_fwd'])}/100
                      </span>
                      <span style='font-size:10px; color:#8893a8;'>· {year}: {int(ls['score_now'])}/100</span>
                    </div>
                  </div>
                  <div style='font-size:11px; color:#d0d4dc; line-height:1.45;'>
                    <i>Why this ticker on this layer:</i> {ls['why']}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# Stage definitions — order is the actual narrative the user reads top-to-bottom
NARRATIVE_STAGES = [
    {
        "key": "users",
        "label": "1 · Users & Agents",
        "icon": "👥",
        "color": "#27ae60",
        "description": "Humans + agents + robots. The demand-side root cause. Frontier-model labs sit here.",
        "layers": [],
        "external_tickers": [
            ("MSFT", "OpenAI partner / Copilot embed"),
            ("GOOGL", "Gemini consumer + DeepMind"),
            ("META", "Llama frontier / Meta AI"),
            ("AAPL", "Apple Intelligence / on-device"),
            ("AMZN", "Anthropic stake + Bedrock"),
            ("ORCL", "OCI hosting Anthropic"),
        ],
    },
    {
        "key": "compute",
        "label": "2 · GPU & AI Compute",
        "icon": "💻",
        "color": "#8e44ad",
        "description": "Primary AI silicon. NVDA dominant; AVGO/AMZN/GOOG XPU share rising.",
        "layers": ["GPU / AI Accelerators"],
    },
    {
        "key": "memory",
        "label": "3 · Memory · the bandwidth wall",
        "icon": "📦",
        "color": "#9b59b6",
        "description": "HBM stacks bound inference throughput more than raw FLOPs do. Server DRAM behind it.",
        "layers": ["HBM Memory", "Server DRAM"],
    },
    {
        "key": "packaging",
        "label": "4 · Packaging, Substrates & Fab",
        "icon": "🏭",
        "color": "#1abc9c",
        "description": "CoWoS bonds GPU + HBM. Hybrid bonding for HBM4. ABF film monopoly + EUV mask sole-supply underneath everything.",
        "layers": [
            "CoWoS / Advanced Packaging",
            "HBM Hybrid Bonding",
            "ABF Dielectric Film",
            "Advanced Substrates / PCB",
            "EUV Mask Inspection / Pellicles",
            "Fab Equipment",
            "EDA Tools / IP",
            "CPU / Host Processors",
        ],
    },
    {
        "key": "networking",
        "label": "5 · Networking, Optics & Connectors",
        "icon": "🔌",
        "color": "#3498db",
        "description": "Ties GPUs into clusters. CPO architectural step-change 2027-28. AEC replaces copper above 400G.",
        "layers": [
            "Scale-Out Networking Silicon",
            "Co-Packaged Optics (CPO)",
            "DPU / SmartNICs",
            "Optical Transceivers",
            "Active Electrical Cables (AEC)",
            "Fiber / Physical Cabling",
            "High-Speed Connectors",
        ],
    },
    {
        "key": "facility",
        "label": "6 · Data Center Build & Operate",
        "icon": "🏢",
        "color": "#16a085",
        "description": "Specialty contractors + REITs + cooling + UPS. Labor + grid interconnect bind 2026-30.",
        "layers": [
            "Data Center Construction",
            "DC REITs / Co-lo",
            "Liquid Cooling",
            "UPS / Backup Power",
            "Skilled Electrical Labor",
        ],
    },
    {
        "key": "power",
        "label": "7 · Power Generation",
        "icon": "⚡",
        "color": "#e74c3c",
        "description": "Gas turbines (GEV slots through 2030), behind-the-meter nuclear (CEG/TLN). PJM queue gates supply.",
        "layers": [
            "Power Generation",
            "Grid Interconnect Queue",
        ],
    },
    {
        "key": "grid",
        "label": "8 · Transmission & Grid Hardware",
        "icon": "🔋",
        "color": "#c0392b",
        "description": "GOES sole-source (CLF), LPT lead times 100-210 weeks, line hardware + poles + galvanizing.",
        "layers": [
            "GOES (Electrical Steel)",
            "Large Power Transformers (LPT)",
            "Distribution Transformers",
            "Line Hardware & HVDC Cable",
            "Steel Poles & Towers",
            "Galvanizing",
        ],
    },
    {
        "key": "defense",
        "label": "9 · Defense Adjacent",
        "icon": "🛡️",
        "color": "#1a5276",
        "description": "Naval nuclear, turbine air filtration, EW shielding — quiet AI-adjacent compounders.",
        "layers": ["Defense Adjacent"],
    },
]


def _ticker_chip_html(ticker: str, mcap: float, exposure: int, pivotal: bool, monopoly: bool) -> str:
    """Render one ticker as a colored pill with $market_cap suffix."""
    if mcap >= 1000: cap_str = f"${mcap/1000:.1f}T"
    elif mcap >= 10: cap_str = f"${mcap:.0f}B"
    elif mcap >= 1:  cap_str = f"${mcap:.1f}B"
    else:            cap_str = f"${mcap*1000:.0f}M"
    # Background by exposure
    if exposure >= 70:   bg = "#1f4530"   # dark green — pure play
    elif exposure >= 40: bg = "#5d4037"   # warm brown — mixed
    elif exposure >= 20: bg = "#3d3520"   # dim yellow — diversified
    else:                bg = "#2a2f3d"   # gray — minor exposure
    star = "<span style='color:#ffd700; margin-right:2px;'>★</span>" if pivotal else ""
    sole = "<span style='color:#ffd700; margin-right:2px;'>§</span>" if monopoly else ""
    return (
        f"<span style='background:{bg}; color:#fff; padding:3px 8px; border-radius:5px; "
        f"margin: 2px 4px 2px 0; font-size:11px; font-weight:600; "
        f"display:inline-block; border:1px solid rgba(255,255,255,0.10);'>"
        f"{star}{sole}{ticker} "
        f"<span style='color:#8893a8; font-weight:400; font-size:10px;'>· {cap_str}</span>"
        f"</span>"
    )


def _tightness_pill_html(score: float) -> str:
    if score >= 85:   bg, txt = "#7a1d1d", "binding"
    elif score >= 70: bg, txt = "#9c2a2a", "tight"
    elif score >= 55: bg, txt = "#b85c1f", "elevated"
    elif score >= 40: bg, txt = "#9a7a1a", "watch"
    elif score >= 25: bg, txt = "#3d6f30", "balanced"
    else:             bg, txt = "#1f4530", "loose"
    return (
        f"<span style='background:{bg}; color:#fff; padding:2px 8px; border-radius:10px; "
        f"font-size:10px; font-weight:700; letter-spacing:0.04em;'>"
        f"{int(score)}/100 · {txt}</span>"
    )


def _render_layer_row(layer: str, year_idx: int):
    """One layer row inside a stage card: layer name + tightness pill + ticker chips."""
    score = float(tight_df.loc[year_idx, layer]) if layer in tight_df.columns else 0.0
    sc_tier, _ = LAYER_TIER.get(layer, ("—", "—"))

    # Pull tickers for the layer; sort by market cap descending
    tickers = LAYER_NAMES_DETAIL.get(layer, [])
    enriched = [
        (t, role, why, market_cap_b(t), theme_exposure_pct(t),
         t in PIVOTAL_TICKERS, t in MONOPOLY_TICKERS)
        for (t, role, why) in tickers
    ]
    enriched.sort(key=lambda r: (-r[3], 0 if r[1] == "P" else (1 if r[1] == "S" else 2)))

    chips_html = "".join(
        _ticker_chip_html(t, mc, exp, piv, mon)
        for (t, role, why, mc, exp, piv, mon) in enriched
    )

    st.markdown(
        f"""
        <div style='background:#161a26; border-radius:8px; padding:10px 14px; margin: 6px 0;
                    border:1px solid #2a2f3d;'>
          <div style='display:flex; justify-content:space-between; align-items:center;
                      margin-bottom:6px;'>
            <span style='font-size:13px; font-weight:600; color:#fff;'>
              <span style='color:#8893a8; font-size:10px; margin-right:6px; font-weight:700;
                           letter-spacing:0.04em;'>{sc_tier}</span>{layer}
            </span>
            {_tightness_pill_html(score)}
          </div>
          <div>{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_external_row(ext_tickers):
    """For demand-side stages (USERS): show tickers without tightness."""
    enriched = [
        (t, why, market_cap_b(t), theme_exposure_pct(t))
        for (t, why) in ext_tickers
    ]
    enriched.sort(key=lambda r: -r[2])
    chips_html = "".join(
        _ticker_chip_html(t, mc, exp, False, False)
        for (t, why, mc, exp) in enriched
    )
    st.markdown(
        f"""
        <div style='background:#161a26; border-radius:8px; padding:10px 14px; margin: 6px 0;
                    border:1px solid #2a2f3d;'>
          <div style='font-size:11px; color:#8893a8; margin-bottom:6px;
                      letter-spacing:0.04em; text-transform:uppercase; font-weight:600;'>
            Frontier model labs &amp; consumer surfaces
          </div>
          <div>{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Render each stage card top-to-bottom
for i, stage in enumerate(NARRATIVE_STAGES):
    # Stage header — colored circle on the left timeline + title
    st.markdown(
        f"""
        <div style='margin: 18px 0 4px 0;'>
          <div style='display:flex; align-items:center; gap:12px;'>
            <div style='width:32px; height:32px; border-radius:50%;
                        background:{stage['color']}; display:flex;
                        align-items:center; justify-content:center;
                        font-size:18px; box-shadow: 0 0 0 3px rgba(255,255,255,0.06);'>
              {stage['icon']}
            </div>
            <div style='flex:1;'>
              <div style='font-size:16px; font-weight:800; color:#fff;'>{stage['label']}</div>
              <div style='font-size:12px; color:#8893a8; margin-top:1px;'>{stage['description']}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if stage.get("layers"):
        for layer in stage["layers"]:
            _render_layer_row(layer, year)
    elif stage.get("external_tickers"):
        _render_external_row(stage["external_tickers"])

    # Vertical connector to next stage (skip after last)
    if i < len(NARRATIVE_STAGES) - 1:
        st.markdown(
            "<div style='margin: 0 0 0 14px; padding: 6px 0; border-left: 2px dashed #2a2f3d; "
            "height: 16px;'></div>",
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════════
# Close TAB 2 (Flow Map) — open TAB 3 (Bottleneck Map)
# ═════════════════════════════════════════════════════════════════════════════
tab_flow.__exit__(None, None, None)
tab_map.__enter__()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1: BOTTLENECK MAP — 29 layers (T1-T15) as cards arranged into 5 stage columns
# ═════════════════════════════════════════════════════════════════════════════
def score_to_color(s: float) -> str:
    """Tightness score → background color (gradient)."""
    if s >= 85: return "#7a1d1d"   # deep red — pegged
    if s >= 70: return "#9c2a2a"   # red — tight
    if s >= 55: return "#b85c1f"   # orange — elevated
    if s >= 40: return "#9a7a1a"   # amber — watch
    if s >= 25: return "#3d6f30"   # green — balanced
    return "#1f4530"               # deep green — loose


def render_card(layer: str, score: float):
    color = score_to_color(score)
    primary = [n for n, t, _ in LAYER_NAMES_DETAIL.get(layer, []) if t == "P"][:3]
    chips = " · ".join(
        f"<code style='background:rgba(0,0,0,0.25);padding:1px 4px;border-radius:3px'>"
        f"{'★ ' if n in PIVOTAL_TICKERS else ''}{n}</code>"
        for n in primary
    )
    new_tag = "<span class='new-tag'>NEW · </span>" if layer in NEW_LAYERS else ""
    sc_tier, sc_track = LAYER_TIER.get(layer, ("—", "—"))
    tier_tag = (
        f"<span style='background:rgba(0,0,0,0.35); color:#fff; font-size:9px; "
        f"padding:1px 5px; border-radius:6px; font-weight:700; letter-spacing:0.04em; "
        f"margin-right:5px;'>{sc_tier}</span>"
    )
    st.markdown(
        f"""
        <div class='bottleneck-card' style='background:{color}'>
          <div class='layer-name'>{tier_tag}{new_tag}{layer}</div>
          <div><span class='score-big'>{score:.0f}</span><span class='score-unit'>/100</span></div>
          <div class='chips'>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Stage columns — left to right, mirrors physical-to-logical supply chain
STAGES = [
    ("Materials", [
        "GOES (Electrical Steel)",
        "Galvanizing",
    ]),
    ("Power & Grid", [
        "Power Generation",
        "Grid Interconnect Queue",
        "Large Power Transformers (LPT)",
        "Distribution Transformers",
        "Line Hardware & HVDC Cable",
        "Steel Poles & Towers",
        "UPS / Backup Power",
        "Liquid Cooling",
    ]),
    ("Silicon", [
        "EDA Tools / IP",
        "EUV Mask Inspection / Pellicles",
        "Fab Equipment",
        "CoWoS / Advanced Packaging",
        "HBM Hybrid Bonding",
        "HBM Memory",
        "GPU / AI Accelerators",
        "CPU / Host Processors",
        "Server DRAM",
    ]),
    ("Platform & Net", [
        "Advanced Substrates / PCB",
        "ABF Dielectric Film",
        "High-Speed Connectors",
        "Active Electrical Cables (AEC)",
        "Scale-Out Networking Silicon",
        "DPU / SmartNICs",
        "Co-Packaged Optics (CPO)",
        "Optical Transceivers",
        "Fiber / Physical Cabling",
    ]),
    ("Facility & Defense", [
        "Skilled Electrical Labor",
        "Data Center Construction",
        "DC REITs / Co-lo",
        "Defense Adjacent",
    ]),
]

st.markdown(f"### Bottleneck Map · {year}")
st.caption(
    "Each card = a supply-chain layer. **Color = tightness** for the selected year "
    "(red = binding, green = balanced). Tickers shown are primary plays per Stonehouse research desk. "
    "Cards tagged **NEW** were added in the April 2026 reconciliations: Round 3 (GOES, Labor, Grid Interconnect, LPT/Distribution split, ABF film, Hybrid Bonding, EUV Mask Inspection); Round 4 (Line Hardware & HVDC, Steel Poles & Towers, Galvanizing, Defense Adjacent); Round 5 — optics/networking expansion (Co-Packaged Optics, DPU/SmartNICs, Active Electrical Cables — plus HPE, MaxLinear, Innolight/Eoptolink reference adds, and NVDA networking cross-tier exposure)."
)

cols = st.columns([1, 2.2, 2.5, 1.8, 1.2])
for col, (stage_name, layers) in zip(cols, STAGES):
    with col:
        st.markdown(f"<div class='stage-header'>{stage_name}</div>", unsafe_allow_html=True)
        for layer in layers:
            if layer not in tight_df.columns:
                continue
            score = float(tight_df.loc[year, layer])
            render_card(layer, score)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2: TIGHTNESS HEAT GRID — all layers × years
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Tightness Over Time")
st.caption(
    "Full layer × year matrix. Shows how each bottleneck evolves through the cycle. "
    "The pattern matters: long-lead layers (power gen 8yr) hold tightness longer post-peak; short-lead layers (GPU 1.25yr) clear faster."
)

# Order by forward-tightness so the eye lands on the hot rows first
fwd_sort = tight_df.loc[2027:2030].mean().sort_values(ascending=False)
heat_layers = list(fwd_sort.index)

display_years = [y for y in YEARS if y % 2 == 1 or y in (2025, 2030, 2035, 2040, 2042)]
hm = tight_df.loc[display_years, heat_layers].T

heat_fig = go.Figure(go.Heatmap(
    z=hm.values,
    x=[str(y) for y in display_years],
    y=list(hm.index),
    colorscale=[
        [0.0, "#0a1628"], [0.25, "#1f4530"], [0.45, "#9a7a1a"],
        [0.65, "#b85c1f"], [0.82, "#9c2a2a"], [1.0, "#7a1d1d"],
    ],
    zmin=0, zmax=100,
    text=hm.values.round(0).astype(int),
    texttemplate="%{text}", textfont={"size": 9, "color": "white"},
    colorbar=dict(title="Score", tickfont=dict(color="white"), thickness=14, len=0.7),
    hovertemplate="<b>%{y}</b><br>Year: %{x}<br>Tightness: %{z:.0f}/100<extra></extra>",
))
heat_fig.update_layout(
    height=620,
    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117", font_color="white",
    xaxis=dict(tickfont=dict(color="white", size=10), side="top"),
    yaxis=dict(tickfont=dict(color="white", size=10), automargin=True),
    margin=dict(t=30, l=10, r=10, b=10),
)
st.plotly_chart(heat_fig, width='stretch')


# ═════════════════════════════════════════════════════════════════════════════
# Close TAB 2 (Bottleneck Map) — open TAB 3 (Easiest Bets)
# ═════════════════════════════════════════════════════════════════════════════
tab_map.__exit__(None, None, None)
tab_bets.__enter__()


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: EASIEST BETS — mispricing surface
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("### Easiest Bets · Tightness × Tier × Layer Coverage × Theme Exposure")
# Caption rendered after bets_df is built (needs len() of filtered + full sets)
_caption_placeholder = st.empty()

TIER_WEIGHTS = {"P": 1.0, "S": 0.6, "K": 0.3}


@st.cache_data
def build_mispricing(_tight_df_hash, year_lo: int = 2027, year_hi: int = 2030):
    """
    Composite scoring formula (per tech-AI round 2 review):
      - Breadth (50%):  sum across layers of (tightness × tier_weight), normalized to 0-100 by /3
                        (a 3-layer name with 100/100 tightness × P-tier hits 100)
      - Depth (30%):    max across layers of (tightness × tier_weight), 0-100
                        (rewards a single deeply-tight P-tier exposure — surfaces memory monopolies)
      - Monopoly (20%): boolean 100/0 — explicit list of sole-source / oligopoly tickers
                        (CLF, Ajinomoto, Lasertec, BESI, ASML, TSM, MU, GLW, etc.)

    Why this works: power names with 3-4 broad-tightness layers still rank at the top,
    but memory pure-plays (MU, Hynix, Samsung) and silicon-stack monopolies (Ajinomoto,
    Lasertec, BESI) now surface alongside them, instead of being drowned by the sum-only formula.
    """
    fwd = tight_df.loc[year_lo:year_hi].mean()
    rows = []
    for ticker, exposures in all_tickers_with_layers().items():
        valid = [(layer, tier, why) for (layer, tier, why) in exposures if layer in fwd.index]
        if not valid:
            continue

        primary_layers = [(L, T, W) for (L, T, W) in valid if T == "P"]
        if primary_layers:
            best = max(primary_layers, key=lambda x: fwd[x[0]])
        else:
            best = max(valid, key=lambda x: fwd[x[0]] * TIER_WEIGHTS[x[1]])
        primary_layer, primary_tier, primary_why = best

        # Breadth: sum across layers, normalized so 3-layer P-tier 100s = 100
        breadth_raw = sum(fwd[L] * TIER_WEIGHTS[T] for (L, T, _) in valid)
        breadth = min(100.0, breadth_raw / 3.0)
        # Depth: max single exposure
        depth = max(fwd[L] * TIER_WEIGHTS[T] for (L, T, _) in valid)
        # Monopoly boost: hardcoded curated list
        monopoly = 100.0 if ticker in MONOPOLY_TICKERS else 0.0

        composite = 0.50 * breadth + 0.30 * depth + 0.20 * monopoly

        # Tier + track from the supply-chain map (colleague's T1-T15 scaffolding)
        sc_tier, sc_track = LAYER_TIER.get(primary_layer, ("—", "—"))
        is_pivotal = ticker in PIVOTAL_TICKERS

        # Theme exposure overlay — what % of company revenue is actually tied
        # to AI infra. Pure-Play Score haircuts the structural composite by
        # this share so equity-level mispricing isn't overstated for sole-source
        # franchises hidden inside diversified parents (CLF GOES at 6%, etc).
        exposure = theme_exposure_pct(ticker)
        pure_play = composite * exposure / 100.0

        rows.append({
            "★": "★" if is_pivotal else "",
            "Ticker": ticker,
            "Tier": sc_tier,
            "Track": sc_track,
            "Primary Layer": primary_layer,
            "Role": primary_tier,
            "Exposure %": exposure,
            "Tightness 2027-30": round(fwd[primary_layer], 1),
            "Pure-Play Score": round(pure_play, 1),
            "Composite Score": round(composite, 1),
            "Breadth": round(breadth, 1),
            "Depth": round(depth, 1),
            "Monopoly": "Y" if monopoly else "—",
            "# Layers": len(valid),
            "Why": primary_why,
        })
    return pd.DataFrame(rows).sort_values(
        ["Pure-Play Score", "Composite Score"], ascending=[False, False]
    ).reset_index(drop=True)


bets_df_full = build_mispricing(hash(tuple(tight_df.values.tobytes())))
# Apply the sidebar exposure filter — keep names with at least min_exposure% AI tie-in
bets_df = bets_df_full[bets_df_full["Exposure %"] >= min_exposure].reset_index(drop=True)

# Backfill the caption now that we know the filter counts
_caption_placeholder.caption(
    "**Pure-Play Score = Composite × Exposure % / 100.** Composite captures the structural tightness of "
    "a name's primary layers (50% breadth + 30% depth + 20% monopoly boost). "
    "Exposure haircuts that by the share of revenue actually tied to AI infra — so a sole-source supplier "
    "where the bottleneck is only 6% of revenue (CLF) doesn't get rerated as if it's a pure-play. "
    f"Filter currently set to **≥{min_exposure}% AI exposure** ({len(bets_df)} of {len(bets_df_full)} names shown). "
    "Top 10 shown as cards with sparklines; long tail in the table below."
)

# Top 10 — cards with sparklines (2 columns × 5 rows)
top10 = bets_df.head(10)

def render_bet_card(row, sparkline_layer: str, layer_color: str):
    """One bet card: ticker headline + tightness sparkline + rationale."""
    series = tight_df[sparkline_layer]
    fill_rgba = (
        layer_color.replace(")", ", 0.18)").replace("rgb", "rgba")
        if layer_color.startswith("rgb")
        else hex_to_rgba(layer_color, 0.18)
    )
    spark = go.Figure(go.Scatter(
        x=YEARS, y=series, mode="lines",
        line=dict(color=layer_color, width=2),
        fill="tozeroy", fillcolor=fill_rgba,
    ))
    spark.add_hline(y=65, line_dash="dot", line_color="#e74c3c", opacity=0.3)
    spark.add_vline(x=year, line_dash="dash", line_color="#ffd700", opacity=0.4)
    spark.update_layout(
        height=80, showlegend=False,
        paper_bgcolor="#161a26", plot_bgcolor="#161a26",
        margin=dict(t=2, b=2, l=2, r=2),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(range=[0, 105], showgrid=False, showticklabels=False, zeroline=False),
    )

    monopoly_badge = " · <span style='color:#ffd700; font-weight:700'>SOLE-SOURCE</span>" if row['Monopoly'] == "Y" else ""
    pivotal_badge = "<span style='color:#ffd700; font-size:16px; margin-right:6px;'>★</span>" if row['★'] == "★" else ""
    track_color = TRACK_COLOR.get(row['Track'], "#888")
    track_pill = (
        f"<span style='background:{track_color}; color:#fff; font-size:9px; "
        f"padding:1px 6px; border-radius:8px; font-weight:700; letter-spacing:0.05em; "
        f"text-transform:uppercase; margin-left:6px;'>{row['Tier']} · {row['Track']}</span>"
    )
    # Exposure pill — color shifts with how pure-play the name is
    exp = int(row['Exposure %'])
    exp_color = "#27ae60" if exp >= 70 else ("#d4ac0d" if exp >= 35 else "#922b21")
    exposure_pill = (
        f"<span style='background:{exp_color}; color:#fff; font-size:9px; "
        f"padding:1px 6px; border-radius:8px; font-weight:700; letter-spacing:0.05em; "
        f"margin-left:5px;'>{exp}% AI-tied</span>"
    )
    layer_line = (
        f"{row['Primary Layer']} · plays {row['# Layers']} "
        f"layer{'s' if row['# Layers'] > 1 else ''} · "
        f"tightness {row['Tightness 2027-30']:.0f}/100{monopoly_badge}"
    )
    score_line = (
        f"<span style='color:#ffd700'>{row['Pure-Play Score']:.0f}</span>"
        f"<span style='color:#8893a8; font-size:10px; margin-left:4px'>"
        f"({row['Composite Score']:.0f} × {exp}%)</span>"
    )
    st.markdown(
        f"""
        <div class='bet-card'>
          <span class='score'>{score_line}</span>
          <div class='ticker'>{pivotal_badge}{row['Ticker']}{track_pill}{exposure_pill}</div>
          <div class='layer'>{layer_line}</div>
          <div class='why'>{row['Why']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(spark, width='stretch', key=f"spark_{row['Ticker']}_{sparkline_layer}")


for i in range(0, len(top10), 2):
    cols = st.columns(2)
    for j, col in enumerate(cols):
        if i + j >= len(top10):
            break
        row = top10.iloc[i + j]
        layer_meta = LAYERS.get(row["Primary Layer"], {})
        layer_color = layer_meta.get("color", "#888")
        with col:
            render_bet_card(row, row["Primary Layer"], layer_color)


# ─── Top primary play per layer ──────────────────────────────────────────────
# The breadth-weighted score above favors multi-layer plays (power names that
# touch 3-4 layers). Memory/CPU/EDA pure-plays get drowned out even when their
# layer is genuinely tight. This section guarantees one primary-tier ticker per
# top-tightest layer is visible — covers the gap.
st.markdown("#### Top Primary Play · per Layer")
st.caption(
    "One primary-tier name per layer, ordered by forward tightness. "
    "Surfaces narrow-but-deep mispricings (memory pure-plays, monopolies) that the "
    "breadth-weighted ranking above can hide. **Read this section if the top-10 looks "
    "too power-heavy for your taste.**"
)

per_layer_picks = []
for layer in fwd_sort.index:
    score = fwd_sort[layer]
    if score < 35:  # skip clearly loose layers
        continue
    primaries = [(t, w) for t, tier, w in LAYER_NAMES_DETAIL.get(layer, []) if tier == "P"]
    if not primaries:
        continue
    ticker, why = primaries[0]  # first primary listed = highest exposure per agent ranking
    sc_tier, sc_track = LAYER_TIER.get(layer, ("—", "—"))
    per_layer_picks.append({
        "Layer": layer,
        "Tier": sc_tier,
        "Track": sc_track,
        "Tightness": round(score, 0),
        "Top Primary Play": ticker,
        "Pivotal": ticker in PIVOTAL_TICKERS,
        "Why": why,
    })

per_layer_df = pd.DataFrame(per_layer_picks)

# Render as a 3-wide row of cards (compact)
n_cols = 3
for i in range(0, len(per_layer_df), n_cols):
    pl_cols = st.columns(n_cols)
    for j, col in enumerate(pl_cols):
        if i + j >= len(per_layer_df):
            break
        row = per_layer_df.iloc[i + j]
        bg = score_to_color(float(row["Tightness"]))
        track_color = TRACK_COLOR.get(row["Track"], "#888")
        star = "<span style='color:#ffd700; margin-right:4px;'>★</span>" if row["Pivotal"] else ""
        track_pill = (
            f"<span style='background:{track_color}; color:#fff; font-size:9px; "
            f"padding:1px 5px; border-radius:6px; font-weight:700; letter-spacing:0.04em; "
            f"text-transform:uppercase; margin-left:5px;'>{row['Tier']}</span>"
        )
        with col:
            st.markdown(
                f"""
                <div class='bet-card' style='border-left: 3px solid {bg}; padding: 10px 12px;'>
                  <div style='display:flex; justify-content:space-between; align-items:baseline;'>
                    <span style='font-size:16px; font-weight:800; color:#fff;'>{star}{row['Top Primary Play']}{track_pill}</span>
                    <span style='font-size:11px; color:#ffd700; font-weight:700;'>{int(row['Tightness'])}/100</span>
                  </div>
                  <div style='font-size:10px; color:#8893a8; margin: 2px 0 6px 0;'>{row['Layer']}</div>
                  <div style='font-size:11px; color:#d0d4dc; line-height:1.35;'>{row['Why']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# Full ranked table (all tickers above the exposure threshold)
st.markdown(f"#### Full Ranking — names ≥{min_exposure}% AI-infra exposure")
st.caption(
    f"Sorted by **Pure-Play Score** = Composite × Exposure %. Showing {len(bets_df)} of {len(bets_df_full)} tickers "
    "(others fall below the exposure filter). Click any column header to re-sort."
)
st.dataframe(
    bets_df.style.background_gradient(
        cmap="Reds", subset=["Pure-Play Score", "Composite Score", "Tightness 2027-30", "Breadth", "Depth"]
    ).background_gradient(
        cmap="Greens", subset=["Exposure %"]
    ),
    width='stretch',
    height=440,
    column_config={
        "★": st.column_config.TextColumn(width="small", help="Colleague's pivotal flag — sole-source / critical-path operator within its tier"),
        "Tier": st.column_config.TextColumn(width="small", help="Supply-chain tier T1-T15 per colleague's flow diagram"),
        "Track": st.column_config.TextColumn(width="small", help="silicon / dc / power / defense"),
        "Role": st.column_config.TextColumn(width="small", help="Stonehouse exposure tier on the primary layer (P = primary, S = secondary, K = known)"),
        "Exposure %": st.column_config.NumberColumn(
            "Exp %", format="%d%%",
            help="Estimated % of company revenue tied to AI infra. Best-effort from segment disclosures + sell-side. Override per ticker in model.py::THEME_EXPOSURE.",
        ),
        "Pure-Play Score": st.column_config.NumberColumn(
            "Pure-Play", format="%.0f",
            help="Composite × Exposure / 100. The equity-level mispricing signal. Sole-source franchises hidden inside diversified parents (CLF GOES at 6%) score low here even if their composite is high.",
        ),
        "Why": st.column_config.TextColumn("Investment Rationale", width="large"),
        "Composite Score": st.column_config.NumberColumn(
            "Composite", format="%.0f",
            help="Structural tightness only: 50% Breadth + 30% Depth + 20% Monopoly Boost. Ignores how big the franchise is in revenue terms.",
        ),
        "Breadth": st.column_config.NumberColumn(format="%.0f", help="Sum tightness × role-weight across layers (normalized)"),
        "Depth": st.column_config.NumberColumn(format="%.0f", help="Max single-layer tightness × role-weight"),
        "Monopoly": st.column_config.TextColumn(width="small", help="Sole-source / oligopoly per Stonehouse research"),
        "Tightness 2027-30": st.column_config.NumberColumn(format="%.0f"),
    },
)


# ═════════════════════════════════════════════════════════════════════════════
# Close TAB 3 (Easiest Bets) — render footer at page level (outside tabs)
# ═════════════════════════════════════════════════════════════════════════════
tab_bets.__exit__(None, None, None)


# ═════════════════════════════════════════════════════════════════════════════
# FOOTER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.caption(
    f"Stonehouse Capital · AI Infra Supply Chain v2 · Scenario: **{preset_name}** · "
    f"Doubling: {doubling:.2f}yr · Util 2025: {util_2025*100:.1f}% · "
    f"Inflection: {inflection or 'post-2042'} · "
    f"{len(LAYERS)} layers · T1-T15 · {sum(len(v) for v in LAYER_NAMES_DETAIL.values())} ticker exposures · "
    "calibrated 2026-04-28 (see research/assumptions_validation.md)"
)
