"""
AI Infrastructure Supply Chain Dashboard — Stonehouse Capital Management
Repo:  W:/projects/stonelodge-supply-chain
Run:   run.bat  or  python -m streamlit run app.py --server.port 8502
Data:  reads Excel model from $STONEHOUSE_BACKEND/data/research/...
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from model import (
    build_token_demand, build_infrastructure_demand,
    build_tightness_scores, power_inflection_year,
    LAYERS, LAYER_DEMAND_COL, FLOW_NODES, FLOW_EDGES, YEARS,
)

st.set_page_config(
    page_title="AI Infra Supply Chain | Stonehouse",
    page_icon="⚡", layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown("""
<style>
.stSlider > div > div > div > div { background: #e74c3c; }
.block-container { padding-top: 0.5rem; padding-bottom: 0; }
div[data-testid="column"] { padding: 0 4px; }
.stMetric { background: #1a1a2e; border-radius: 8px; padding: 8px 12px; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# CONTROL PANEL — front and center
# ═══════════════════════════════════════════════════════════════════
st.markdown("## ⚡ AI Infrastructure Supply Chain — Stonehouse Capital")

with st.expander("▶  DEMAND LEVERS  (click to expand / collapse)", expanded=True):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        scenario = st.selectbox("Scenario", ["Base", "Robo Bull", "Bear"],
                                help="Excel model base scenario")
    with c2:
        ai_users_2025 = st.slider("AI Users 2025 (M)", 500, 2000, 1100, 50,
                                  help="Total AI users in 2025 baseline")
    with c3:
        agent_mult = st.slider("Agent Multiplier", 0.25, 3.0, 1.0, 0.05,
                               help="Scale enterprise agent tokens vs base (1.0 = Excel)")
    with c4:
        humanoid_scale = st.slider("Humanoid Units", 0.1, 5.0, 1.0, 0.1,
                                   help="Scale humanoid robot units vs base")
    with c5:
        edge_2040 = st.slider("Edge Fraction 2040 %", 20, 90, 65, 5,
                              help="% of robotics tokens served on-device by 2040") / 100
    with c6:
        enterprise_scale = st.slider("Enterprise Intensity", 0.5, 2.0, 1.0, 0.1,
                                     help="Scale enterprise token intensity vs base")

with st.expander("⚙️  EFFICIENCY & CALIBRATION  (advanced)", expanded=False):
    e1, e2, e3 = st.columns(3)
    with e1:
        tokens_per_kwh = st.slider("Tokens / kWh 2025 (M)", 0.5, 10.0, 3.6, 0.1,
                                   help="H100 frontier inference efficiency") * 1_000_000
        efficiency_dbl = st.slider("Efficiency doubling (years)", 1.5, 5.0, 2.5, 0.5,
                                   help="Slower = power demand stays high longer")
    with e2:
        inf_util = st.slider("Inference utilization 2025 %", 1, 20, 7, 1,
                             help="% of deployed AI infra doing active inference. "
                                  "Calibrates 2025 power to ~30 GW.") / 100
    with e3:
        st.markdown("**Supply Growth Rates (% / yr)**")
        st.caption("Drag to stress-test individual layer bottlenecks")

    # Supply growth sliders in a compact grid
    sg_cols = st.columns(6)
    custom_supply = {}
    layer_list = list(LAYERS.keys())
    for i, (layer, meta) in enumerate(LAYERS.items()):
        col = sg_cols[i % 6]
        with col:
            val = st.slider(
                layer.split(" ")[0][:12], 2, 80,
                int(meta["supply_growth_pct"] * 100), 2,
                key=f"sg_{layer}",
                help=f"{layer}: {meta['description']}"
            )
            custom_supply[layer] = val / 100

st.divider()

# ═══════════════════════════════════════════════════════════════════
# MODEL RUN
# ═══════════════════════════════════════════════════════════════════
@st.cache_data
def run_model(scenario, ai_users_2025, agent_mult, humanoid_scale,
              enterprise_scale, edge_2040, tokens_per_kwh, efficiency_dbl,
              inf_util, supply_tuple):
    tok = build_token_demand(
        scenario=scenario,
        ai_users_2025_M=ai_users_2025,
        agent_multiplier_scale=agent_mult,
        humanoid_units_scale=humanoid_scale,
        enterprise_intensity_scale=enterprise_scale,
        edge_fraction_2040=edge_2040,
    )
    inf = build_infrastructure_demand(
        tok,
        tokens_per_kwh_2025=tokens_per_kwh,
        efficiency_doubling_years=efficiency_dbl,
        inference_utilization_2025=inf_util,
    )
    tight = build_tightness_scores(inf, custom_supply_growth=dict(supply_tuple))
    return tok, inf, tight


tok_df, inf_df, tight_df = run_model(
    scenario, ai_users_2025, agent_mult, humanoid_scale,
    enterprise_scale, edge_2040, tokens_per_kwh, efficiency_dbl,
    inf_util, tuple(custom_supply.items()),
)
inflection = power_inflection_year(inf_df)


# ═══════════════════════════════════════════════════════════════════
# HEADLINE METRICS
# ═══════════════════════════════════════════════════════════════════
m1, m2, m3, m4, m5, m6 = st.columns(6)
with m1:
    st.metric("Tokens/day 2025", f"{tok_df.loc[2025,'total_T']:.0f}T")
with m2:
    v30 = tok_df.loc[2030, 'total_T']
    st.metric("Tokens/day 2030", f"{v30:.0f}T",
              delta=f"+{(v30/tok_df.loc[2025,'total_T']-1)*100:.0f}%")
with m3:
    st.metric("Power 2025", f"{inf_df.loc[2025,'power_total_gw']:.0f} GW")
with m4:
    pk_yr = inf_df['power_total_gw'].idxmax()
    st.metric("Peak Power", f"{inf_df['power_total_gw'].max():.0f} GW", delta=f"~{pk_yr}")
with m5:
    if inflection:
        st.metric("⚡ Power Inflection", str(inflection), delta="efficiency wins",
                  delta_color="off")
    else:
        st.metric("⚡ Power Inflection", "Post-2042")
with m6:
    tightest = tight_df.loc[2027:2030].mean().idxmax()
    score = tight_df.loc[2027:2030].mean().max()
    st.metric("Tightest Layer 2027-30", tightest.split(" ")[0], delta=f"{score:.0f}/100",
              delta_color="off")

st.divider()

# ═══════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Token Demand",
    "⚡ Power & Efficiency",
    "🔥 Bottleneck Heat Map",
    "💼 Investment Signals",
    "🗺️ Supply Chain Map",
])

DARK = {"plot_bgcolor": "#0e1117", "paper_bgcolor": "#0e1117", "font_color": "white"}


# ─── Tab 1: Token Demand ──────────────────────────────────────────
with tab1:
    col_a, col_b = st.columns([3, 2])
    with col_a:
        fig = go.Figure()
        palette = {"retail_T": "#3498db", "enterprise_T": "#9b59b6",
                   "robotics_cloud_T": "#2ecc71", "robotics_edge_T": "#95a5a6"}
        labels = {"retail_T": "Retail", "enterprise_T": "Enterprise (incl. agents)",
                  "robotics_cloud_T": "Robotics (cloud)", "robotics_edge_T": "Robotics (edge)"}
        for col, color in palette.items():
            fig.add_trace(go.Bar(x=YEARS, y=tok_df[col], name=labels[col],
                                 marker_color=color, opacity=0.85))
        fig.update_layout(barmode="stack", title="Token Demand by Category (T/day)",
                          xaxis_title="Year", yaxis_title="Trillions/day",
                          legend=dict(orientation="h", y=-0.18), height=400,
                          margin=dict(t=40, b=80), **DARK)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        total = tok_df["total_T"]
        growth = total.pct_change() * 100
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=YEARS[1:], y=growth.iloc[1:],
                                  mode="lines+markers", line_color="#f39c12", line_width=2))
        fig2.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.4)
        fig2.update_layout(title="Token Demand YoY Growth %", height=400,
                           margin=dict(t=40, b=40), **DARK)
        st.plotly_chart(fig2, use_container_width=True)

    # Summary table
    mix_df = pd.DataFrame({
        "Retail %": (tok_df["retail_T"] / tok_df["total_T"] * 100).round(1),
        "Enterprise %": (tok_df["enterprise_T"] / tok_df["total_T"] * 100).round(1),
        "Robo Cloud %": (tok_df["robotics_cloud_T"] / tok_df["total_T"] * 100).round(1),
        "Robo Edge %": (tok_df["robotics_edge_T"] / tok_df["total_T"] * 100).round(1),
        "Total T/day": tok_df["total_T"].round(0).astype(int),
    })
    st.dataframe(mix_df.style.background_gradient(cmap="Blues", subset=["Total T/day"]),
                 use_container_width=True)


# ─── Tab 2: Power & Efficiency ────────────────────────────────────
with tab2:
    col_a, col_b = st.columns(2)
    with col_a:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=YEARS, y=inf_df["power_total_gw"],
                                 name="Total AI Power (GW)",
                                 line=dict(color="#e74c3c", width=3),
                                 fill="tozeroy", fillcolor="rgba(231,76,60,0.12)"))
        fig.add_trace(go.Scatter(x=YEARS, y=inf_df["total_compute_gw"],
                                 name="GPU Compute (GW)",
                                 line=dict(color="#9b59b6", width=2, dash="dash")))
        fig.add_trace(go.Scatter(x=YEARS, y=inf_df["cooling_gw"],
                                 name="Cooling (GW)",
                                 line=dict(color="#3498db", width=1.5, dash="dot")))
        fig.add_hline(y=30, line_dash="dot", line_color="white", opacity=0.3,
                      annotation_text="2025 baseline 30 GW", annotation_position="bottom right")
        if inflection:
            fig.add_vline(x=inflection, line_dash="dash", line_color="#2ecc71", opacity=0.8,
                          annotation_text=f"Inflection ~{inflection}",
                          annotation_position="top right")
        fig.update_layout(title="AI Infrastructure Power Demand", height=380,
                          yaxis_title="GW", legend=dict(orientation="h", y=-0.2),
                          margin=dict(t=40, b=80), **DARK)
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        token_yoy = tok_df["total_cloud_T"].pct_change() * 100
        power_yoy = inf_df["power_total_gw"].pct_change() * 100
        eff_yoy = (inf_df["efficiency_tokens_per_kwh"].pct_change() * 100)
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=YEARS[1:], y=token_yoy.iloc[1:],
                                  name="Token demand growth %",
                                  line=dict(color="#3498db", width=2)))
        fig2.add_trace(go.Scatter(x=YEARS[1:], y=power_yoy.iloc[1:],
                                  name="Power demand growth %",
                                  line=dict(color="#e74c3c", width=2)))
        fig2.add_trace(go.Scatter(x=YEARS[1:], y=eff_yoy.iloc[1:],
                                  name="Efficiency improvement %",
                                  line=dict(color="#2ecc71", width=2, dash="dash")))
        fig2.add_hline(y=0, line_color="gray", line_dash="dash", opacity=0.4)
        fig2.update_layout(title="Token Growth vs Power Growth vs Efficiency",
                           height=380, legend=dict(orientation="h", y=-0.2),
                           margin=dict(t=40, b=80), **DARK)
        st.plotly_chart(fig2, use_container_width=True)

    # Efficiency curve
    eff_M = inf_df["efficiency_tokens_per_kwh"] / 1e6
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=YEARS, y=eff_M, mode="lines+markers",
                              line=dict(color="#f39c12", width=2)))
    fig3.update_layout(title="Inference Efficiency — M tokens / kWh",
                       height=260, margin=dict(t=40, b=40), **DARK)
    st.plotly_chart(fig3, use_container_width=True)


# ─── Tab 3: Heat Map ──────────────────────────────────────────────
with tab3:
    st.caption(
        "**Tightness 0–100:** demand growth rate vs supply expansion capacity, "
        "adjusted for lead times. 65+ = structurally constrained. "
        "Green = supply keeping pace. Red = binding bottleneck."
    )

    display_years = [y for y in YEARS if y % 2 == 1 or y in (2025, 2030, 2035, 2040, 2042)]
    hm = tight_df[display_years].T

    fig = go.Figure(go.Heatmap(
        z=hm.values,
        x=[str(y) for y in display_years],
        y=list(hm.index),
        colorscale=[
            [0.0, "#0a1628"], [0.30, "#1e6b3e"], [0.55, "#c47a00"],
            [0.72, "#c43e00"], [1.0, "#8b0000"],
        ],
        zmin=0, zmax=100,
        text=hm.values.round(0).astype(int),
        texttemplate="%{text}", textfont={"size": 9},
        colorbar=dict(title="Score", tickfont=dict(color="white")),
    ))
    fig.update_layout(
        title="Supply Chain Tightness — All Layers × Year",
        height=560,
        xaxis=dict(tickfont=dict(color="white", size=10)),
        yaxis=dict(tickfont=dict(color="white", size=9), automargin=True),
        margin=dict(t=50, l=280, b=50),
        **DARK,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Binding constraint per year
    bind = tight_df.idxmax(axis=1)
    bind_score = tight_df.max(axis=1)
    bind_df = pd.DataFrame({"Binding Constraint": bind, "Score": bind_score.round(1)})
    st.dataframe(bind_df, use_container_width=True)


# ─── Tab 4: Investment Signals ────────────────────────────────────
with tab4:
    # Sort layers by forward tightness (2026-2030 avg)
    fwd_scores = {layer: tight_df.loc[2026:2030, layer].mean()
                  for layer in tight_df.columns}
    sorted_layers = sorted(fwd_scores.items(), key=lambda x: -x[1])

    cols = st.columns(2)
    for idx, (layer, fwd_score) in enumerate(sorted_layers):
        if layer not in LAYERS:
            continue
        meta = LAYERS[layer]
        col = cols[idx % 2]
        with col:
            if fwd_score >= 65:
                badge = "🔴 TIGHT"
                badge_color = "#e74c3c"
            elif fwd_score >= 45:
                badge = "🟡 ELEVATED"
                badge_color = "#f39c12"
            else:
                badge = "🟢 BALANCED"
                badge_color = "#2ecc71"

            with st.expander(
                f"**{layer}**  ·  {', '.join(meta['names'][:3])}",
                expanded=(fwd_score >= 55),
            ):
                st.markdown(f"<span style='color:{badge_color};font-weight:bold'>{badge}</span>"
                            f"  |  2026–30 avg: **{fwd_score:.0f}/100**",
                            unsafe_allow_html=True)
                st.caption(meta["description"])
                st.caption(f"Lead time: {meta['lead_time_yrs']:.1f} yr  ·  "
                           f"Supply growth: {meta['supply_growth_pct']*100:.0f}%/yr")

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=YEARS, y=tight_df[layer],
                                         mode="lines+markers",
                                         line=dict(color=meta["color"], width=2),
                                         fill="tozeroy",
                                         fillcolor=meta["color"].replace(")", ",0.15)").replace("rgb", "rgba") if meta["color"].startswith("rgb") else meta["color"] + "26"))
                fig.add_hline(y=65, line_dash="dash", line_color="#e74c3c", opacity=0.4)
                fig.add_hline(y=40, line_dash="dot", line_color="#2ecc71", opacity=0.4)
                fig.update_layout(
                    height=180, showlegend=False, yaxis=dict(range=[0, 105]),
                    margin=dict(t=5, b=25, l=35, r=10),
                    xaxis=dict(tickfont=dict(size=8)),
                    **DARK,
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("  ".join(f"`{n}`" for n in meta["names"]))


# ─── Tab 5: Supply Chain Map ──────────────────────────────────────
with tab5:
    st.markdown("""
    **Interactive supply chain flow chart.**
    Each node shows which companies are exposed. Color = tightness score for selected year.
    Use the year slider to animate the bottleneck regime over time.
    """)

    map_year = st.slider("Year", min_value=2025, max_value=2042, value=2028, step=1,
                         key="map_year")

    # Build tightness lookup for this year
    def node_score(layer_key: str) -> float:
        if not layer_key or layer_key not in tight_df.columns:
            return 35.0
        return float(tight_df.loc[map_year, layer_key])

    def score_to_color(score: float) -> str:
        if score >= 70:
            return "#c0392b"
        elif score >= 55:
            return "#e67e22"
        elif score >= 40:
            return "#f39c12"
        else:
            return "#1e6b3e"

    # Build Plotly figure with custom shapes
    fig = go.Figure()

    node_lookup = {n["id"]: n for n in FLOW_NODES}

    # Draw edges first (behind nodes)
    for (src_id, tgt_id) in FLOW_EDGES:
        src = node_lookup[src_id]
        tgt = node_lookup[tgt_id]
        fig.add_annotation(
            x=tgt["x"] - 0.03, y=tgt["y"],
            ax=src["x"] + 0.03, ay=src["y"],
            xref="x", yref="y", axref="x", ayref="y",
            showarrow=True, arrowhead=2, arrowsize=0.8,
            arrowwidth=1.5, arrowcolor="rgba(180,180,180,0.35)",
        )

    # Draw nodes
    for node in FLOW_NODES:
        layer_key = node.get("layer", "")
        score = node_score(layer_key)
        color = score_to_color(score)
        label = node["label"]

        # Score badge suffix
        if layer_key:
            label += f"\n({score:.0f})"

        fig.add_trace(go.Scatter(
            x=[node["x"]], y=[node["y"]],
            mode="markers+text",
            marker=dict(
                size=52, color=color, opacity=0.9,
                line=dict(color="white", width=1.5),
                symbol="square",
            ),
            text=[label],
            textfont=dict(size=7.5, color="white"),
            textposition="middle center",
            hovertemplate=f"<b>{node['id'].replace('_',' ').title()}</b>"
                          + (f"<br>Tightness: {score:.0f}/100" if layer_key else "")
                          + "<extra></extra>",
        ))

    # Legend
    for label, color in [("≥70 TIGHT", "#c0392b"), ("55-70 ELEVATED", "#e67e22"),
                          ("40-55 WATCH", "#f39c12"), ("<40 BALANCED", "#1e6b3e")]:
        fig.add_trace(go.Scatter(
            x=[None], y=[None], mode="markers",
            marker=dict(size=12, color=color, symbol="square"),
            name=label, showlegend=True,
        ))

    fig.update_layout(
        title=f"AI Infrastructure Supply Chain — Tightness Map ({map_year})",
        xaxis=dict(range=[-0.03, 1.05], showgrid=False, zeroline=False,
                   showticklabels=False),
        yaxis=dict(range=[-0.05, 1.05], showgrid=False, zeroline=False,
                   showticklabels=False),
        height=580,
        legend=dict(orientation="h", y=-0.04, x=0.0,
                    font=dict(size=10, color="white")),
        margin=dict(t=50, b=60, l=10, r=10),
        showlegend=True,
        **DARK,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Tightness scores reflect demand growth rate vs supply expansion capacity, "
        "adjusted for lead time. Node color is absolute tightness; "
        "move the year slider to see how bottlenecks shift over the cycle."
    )

# ── Footer ────────────────────────────────────────────────────────
st.divider()
st.caption(
    f"Stonehouse Capital Management  ·  AI Infra Supply Chain  ·  "
    f"Scenario: {scenario}  ·  Agent mult: {agent_mult:.2f}×  ·  "
    f"Efficiency doubling: {efficiency_dbl:.1f} yr  ·  "
    f"Power inflection: {inflection or 'post-2042'}"
)
