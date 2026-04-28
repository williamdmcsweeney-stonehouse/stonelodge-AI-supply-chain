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
    power_inflection_year,
)

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
}

# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR — Scenario presets + key levers
# ═════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("# AI Infra Supply Chain")
st.sidebar.caption("v2 · Stonehouse Capital · 2026-04-28")

# ── MACRO SCENARIO (drives the GW gap framework) ─────────────────────────────
st.sidebar.markdown("### Macro Scenario")
st.sidebar.caption("Drives the Demand vs Supply gap (efficiency + supply phase rates).")
macro_name = st.sidebar.radio(
    "macro",
    list(MACRO_SCENARIOS.keys()),
    label_visibility="collapsed",
    help="Per colleague's v4_2 Efficiency Overlay. "
         "Bear = fast efficiency (gap closes ~2032). Bull = slow efficiency (gap never closes).",
)
macro_cfg = MACRO_SCENARIOS[macro_name]
st.sidebar.caption(f"_{macro_cfg['note']}_")

# ── DEMAND SCENARIO (drives token demand from Excel) ─────────────────────────
st.sidebar.markdown("### Demand Scenario")
PRESETS = {
    "Stonehouse Base": {
        "scenario": "Base", "ai_users": 1100, "agent_mult": 1.0, "humanoid": 1.0,
        "enterprise": 1.0, "doubling": 2.0, "util_2025": 0.067,
    },
    "Robotics Bull": {
        "scenario": "Robo Bull", "ai_users": 1300, "agent_mult": 1.4, "humanoid": 2.5,
        "enterprise": 1.3, "doubling": 2.0, "util_2025": 0.075,
    },
    "Adoption Bear": {
        "scenario": "Bear", "ai_users": 800, "agent_mult": 0.7, "humanoid": 0.5,
        "enterprise": 0.8, "doubling": 2.25, "util_2025": 0.06,
    },
    "Aggressive Efficiency (1.75yr doubling)": {
        "scenario": "Base", "ai_users": 1100, "agent_mult": 1.0, "humanoid": 1.0,
        "enterprise": 1.0, "doubling": 1.75, "util_2025": 0.067,
    },
}
preset_name = st.sidebar.radio(
    "scenario", list(PRESETS.keys()), label_visibility="collapsed",
)
preset = PRESETS[preset_name]

st.sidebar.markdown("### Fleet Calibration")
anchor_gw = st.sidebar.slider(
    "2025 DC power anchor (GW)", 30.0, 80.0, 66.0, 1.0,
    help="Total global DC operational capacity 2025. "
         "Cushman & Wakefield: US 40.6 + EMEA 10.3 + APAC 12.2 = 63 GW (~66 GW with growth to YE25). "
         "Drives the macro gap framework. Note: this is TOTAL DC capacity, broader than AI-only fleet.",
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
    "Efficiency doubling (years)", 1.0, 4.0, macro_cfg["doubling"], 0.25,
    help="Hardware efficiency doubling period (Epoch AI: ~2yr empirical). "
         "Lower = faster frontier gains. Default tracks selected Macro Scenario.",
)
util_2025 = st.sidebar.slider(
    "Inference utilization 2025 %",
    1.0, 20.0, round(preset["util_2025"] * 100, 1), 0.1,
    help="Pct of deployed AI fleet doing active inference. Used by layer-level model only. ~6.7% historical.",
) / 100

with st.sidebar.expander("Advanced — supply phase rates"):
    sr1 = st.slider("2026-27 supply growth %", 5, 50, int(macro_cfg["supply_rates"][0] * 100), 1) / 100
    sr2 = st.slider("2028-30 supply growth %", 5, 50, int(macro_cfg["supply_rates"][1] * 100), 1) / 100
    sr3 = st.slider("2031-35 supply growth %", 5, 50, int(macro_cfg["supply_rates"][2] * 100), 1) / 100
    sr4 = st.slider("2036-42 supply growth %", 2, 30, int(macro_cfg["supply_rates"][3] * 100), 1) / 100
    supply_rates = (sr1, sr2, sr3, sr4)

with st.sidebar.expander("Advanced — token demand"):
    ai_users = st.slider("AI Users 2025 (M)", 500, 2000, preset["ai_users"], 50)
    agent_mult = st.slider("Agent Multiplier", 0.25, 3.0, preset["agent_mult"], 0.05)
    humanoid = st.slider("Humanoid Units", 0.1, 5.0, preset["humanoid"], 0.1)
    enterprise = st.slider("Enterprise Intensity", 0.5, 2.0, preset["enterprise"], 0.1)

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
# HEADER + HEADLINE METRICS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    "## AI Infrastructure Supply Chain "
    f"&nbsp;<span style='font-size:14px;color:#8893a8'>· {macro_name} × {preset_name}</span>",
    unsafe_allow_html=True,
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
st.plotly_chart(gap_fig, use_container_width=True)

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
    st.plotly_chart(cap_fig, use_container_width=True)

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
        st.plotly_chart(eff_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# YEAR SCRUBBER (drives the flow visualization + bottleneck map)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
year = st.slider(
    "**Map Year** — drag to see how bottlenecks shift over the cycle",
    min_value=2025, max_value=2042, value=2028, step=1,
)


# ═════════════════════════════════════════════════════════════════════════════
# FLOW VISUALIZATION — How AI demand becomes physical infrastructure
# Reads the selected year from the scrubber above. Shows the cause-and-effect
# chain at a glance: users → tokens → compute → hardware → facility → power.
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(f"### How AI demand becomes physical infrastructure · {year}")
st.caption(
    "Read left to right. Each box is the next step the demand has to pass through to "
    "actually run. The supply chain bottlenecks below are which of these steps can't keep up."
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


# Pull live values for the selected year
y_users_M    = ai_users * (1 + 0.30) ** (year - 2025)  # ~30%/yr user growth assumption
y_tokens_T   = float(tok_df.loc[year, "total_T"])
y_compute_gw = float(inf_df.loc[year, "total_compute_gw"])
y_servers_M  = float(inf_df.loc[year, "server_count_M"])
y_power_gw   = float(inf_df.loc[year, "power_total_gw"])
y_twh_yr     = y_power_gw * 8760 * 0.80 / 1000  # 80% load factor → TWh/yr

flow_stages = [
    ("USERS", _fmt_big(y_users_M * 1e6), "AI users worldwide", "#27ae60", "silicon"),
    ("TOKENS", f"{y_tokens_T:.0f}T/day", "tokens generated", "#16a085", "silicon"),
    ("COMPUTE", f"{y_compute_gw:.0f} GW", "active compute", "#8e44ad", "silicon"),
    ("HARDWARE", f"{_fmt_big(y_servers_M * 1e6)} svrs", "GPU + memory + network", "#2980b9", "silicon"),
    ("FACILITY", f"{y_power_gw:.0f} GW", "data center capacity", "#16a085", "dc"),
    ("ENERGY", f"{y_twh_yr:.0f} TWh/yr", f"power drawn ({year})", "#c0392b", "power"),
]

# Build the flow as flexbox HTML — chevron-shaped boxes connected by arrows
flow_html = """
<style>
.flow-row {
  display: flex; align-items: stretch; gap: 0; margin: 12px 0 24px 0;
  width: 100%; overflow-x: auto;
}
.flow-stage {
  flex: 1; min-width: 0; padding: 14px 16px 14px 22px;
  position: relative; color: #fff;
  clip-path: polygon(0 0, calc(100% - 14px) 0, 100% 50%, calc(100% - 14px) 100%, 0 100%, 14px 50%);
}
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
</style>
<div class='flow-row'>
"""
for label, value, sub, color, _track in flow_stages:
    flow_html += (
        f"<div class='flow-stage' style='background:{color}'>"
        f"<div class='flow-label'>{label}</div>"
        f"<div class='flow-value'>{value}</div>"
        f"<div class='flow-sub'>{sub}</div>"
        "</div>"
    )
flow_html += "</div>"
st.markdown(flow_html, unsafe_allow_html=True)

st.caption(
    "**The compounding ratio:** every doubling of users at the left end forces ~roughly a doubling "
    "of every stage to the right. The bottleneck cards below show which of those doublings are "
    "physically deliverable on time, and which become pricing-power moments for the suppliers."
)


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
        "Scale-Out Networking Silicon",
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
    "Cards tagged **NEW** were added in the April 2026 reconciliations: Round 3 (GOES, Labor, Grid Interconnect, LPT/Distribution split, ABF film, Hybrid Bonding, EUV Mask Inspection); Round 4 (Line Hardware & HVDC, Steel Poles & Towers, Galvanizing, Defense Adjacent)."
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
st.plotly_chart(heat_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3: EASIEST BETS — mispricing surface
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("---")
st.markdown("### Easiest Bets · Tightness × Tier × Layer Coverage")
st.caption(
    "**Mispricing score** = sum across each ticker's layer exposures of "
    "(forward-tightness 2027-30) × (tier weight: P=1.0, S=0.6, K=0.3). "
    "Names that play multiple tight layers, or play a single tight layer as a primary, score highest. "
    "Top 10 shown as cards with sparklines; long tail in the table below."
)

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

        rows.append({
            "★": "★" if is_pivotal else "",
            "Ticker": ticker,
            "Tier": sc_tier,
            "Track": sc_track,
            "Primary Layer": primary_layer,
            "Role": primary_tier,
            "Tightness 2027-30": round(fwd[primary_layer], 1),
            "Composite Score": round(composite, 1),
            "Breadth": round(breadth, 1),
            "Depth": round(depth, 1),
            "Monopoly": "Y" if monopoly else "—",
            "# Layers": len(valid),
            "Why": primary_why,
        })
    return pd.DataFrame(rows).sort_values(
        ["Composite Score", "Tightness 2027-30"], ascending=[False, False]
    ).reset_index(drop=True)


bets_df = build_mispricing(hash(tuple(tight_df.values.tobytes())))

# Top 10 — cards with sparklines (2 columns × 5 rows)
top10 = bets_df.head(10)

def hex_to_rgba(hex_color: str, alpha: float = 0.18) -> str:
    """Convert #rrggbb hex to rgba(r,g,b,alpha) for Plotly fill."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(150,150,150,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


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
    layer_line = (
        f"{row['Primary Layer']} · plays {row['# Layers']} "
        f"layer{'s' if row['# Layers'] > 1 else ''} · "
        f"tightness {row['Tightness 2027-30']:.0f}/100{monopoly_badge}"
    )
    st.markdown(
        f"""
        <div class='bet-card'>
          <span class='score'>{row['Composite Score']:.0f}</span>
          <div class='ticker'>{pivotal_badge}{row['Ticker']}{track_pill}</div>
          <div class='layer'>{layer_line}</div>
          <div class='why'>{row['Why']}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.plotly_chart(spark, use_container_width=True, key=f"spark_{row['Ticker']}_{sparkline_layer}")


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


# Full ranked table (all tickers)
st.markdown("#### Full Ranking — all tickers")
st.caption("Sorted by mispricing score. Click a column header to re-sort.")
st.dataframe(
    bets_df.style.background_gradient(
        cmap="Reds", subset=["Composite Score", "Tightness 2027-30", "Breadth", "Depth"]
    ),
    use_container_width=True,
    height=400,
    column_config={
        "★": st.column_config.TextColumn(width="small", help="Colleague's pivotal flag — sole-source / critical-path operator within its tier"),
        "Tier": st.column_config.TextColumn(width="small", help="Supply-chain tier T1-T15 per colleague's flow diagram"),
        "Track": st.column_config.TextColumn(width="small", help="silicon / dc / power / defense"),
        "Role": st.column_config.TextColumn(width="small", help="Stonehouse exposure tier on the primary layer (P = primary, S = secondary, K = known)"),
        "Why": st.column_config.TextColumn("Investment Rationale", width="large"),
        "Composite Score": st.column_config.NumberColumn(
            "Composite", format="%.0f",
            help="50% Breadth + 30% Depth + 20% Monopoly Boost",
        ),
        "Breadth": st.column_config.NumberColumn(format="%.0f", help="Sum tightness × role-weight across layers (normalized)"),
        "Depth": st.column_config.NumberColumn(format="%.0f", help="Max single-layer tightness × role-weight"),
        "Monopoly": st.column_config.TextColumn(width="small", help="Sole-source / oligopoly per Stonehouse research"),
        "Tightness 2027-30": st.column_config.NumberColumn(format="%.0f"),
    },
)


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
