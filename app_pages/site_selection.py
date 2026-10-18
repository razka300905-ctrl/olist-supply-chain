"""Project 1 - Site selection: how many fulfilment centres, and where?"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import (LIGHT_BLUE, MUTED, ROOT, SERIES, callout, fc_label, hero, hub_color, kpis, load_site,
                        md_file, purpose, section, setup_page, style_fig)

setup_page("Site Selection", "📍")

summary = load_site("scenario_summary")
sites = load_site("selected_sites", dtype={"zone": str})
assign = load_site("zone_assignment", dtype={"zone": str, "fc_zone": str})
variants = load_site("practical_variants_k3")
asis = summary.iloc[0]
k3 = summary[summary.k == 3].iloc[0]
scen = summary[summary.k >= 1]

hero("Project 1 · Network design",
     "Where should Olist open fulfilment centres?",
     "Today every seller ships directly, so the average parcel travels ~775 km and takes 12 days. This project finds "
     "how many FCs to open, and where, to bring orders closer to customers.",
     ["p-median optimisation", "PuLP + HiGHS", "849 demand regions", "1–6 FC scenarios"])

purpose(
    "How many FCs should Olist open, and in which cities?",
    "Minimise the distance between stock and customers, and show what each extra FC is worth.",
    "A recommended network, a 1–6 FC trade-off curve, KPIs per scenario and a coverage map.",
    "Network-strategy and real-estate teams, plus the operations leadership approving the FC investment.",
)

callout("<b>Recommendation: open 3 FCs</b> (São Paulo, Minas Gerais/Rio corridor, Northeast). In practice: "
        "<b>São Paulo + Rio + Salvador</b>, only 4% worse than the mathematical optimum and far easier to staff and supply.")
kpis([
    {"label": "Avg distance to customer", "value": f"{k3.avg_km:.0f} km", "note": f"↓ 47% vs {asis.avg_km:.0f} km today", "tone": "good"},
    {"label": "Next-day reach (≤300 km)", "value": f"{k3.pct_within_300km:.0f}%", "note": f"↑ from {asis.pct_within_300km:.0f}% today", "tone": "good"},
    {"label": "Est. delivery time", "value": f"{k3.est_delivery_days:.1f} days", "note": f"↓ from {asis.est_delivery_days:.1f} days", "tone": "good"},
    {"label": "Est. freight per item", "value": f"R$ {k3.est_freight_per_item:.2f}", "note": f"↓ from R$ {asis.est_freight_per_item:.2f}", "tone": "good"},
])

tab_res, tab_an, tab_m = st.tabs(["📊  Results & scenarios", "🧭  Analysis: what we chose and why", "⚙️  Method & data"])

# ================================================================== results
with tab_res:
    section(1, "Pick a scenario", "Move the slider to see how the network and KPIs change with 1–6 FCs")
    k = st.select_slider("Number of fulfilment centres", options=list(range(1, 7)), value=3, format_func=fc_label)
    row = summary[summary.k == k].iloc[0]

    def card(label, col, fmt, dfmt, lower_is_better):
        d = row[col] - asis[col]
        good = (d < 0) == lower_is_better
        return {"label": label, "value": fmt.format(row[col]), "note": f"{dfmt.format(d)} vs today", "tone": "good" if good else "bad"}

    kpis([
        card("Avg distance", "avg_km", "{:.0f} km", "{:+.0f} km", True),
        card("Within 300 km", "pct_within_300km", "{:.0f}%", "{:+.0f} pp", False),
        card("Within 800 km", "pct_within_800km", "{:.0f}%", "{:+.0f} pp", False),
        card("Delivery time", "est_delivery_days", "{:.1f} days", "{:+.1f} days", True),
        card("Freight per item", "est_freight_per_item", "R$ {:.2f}", "{:+.2f} R$", True),
    ])

    section(2, f"The network with {fc_label(k)}", "Each dot is a demand region (size = orders), coloured by the FC that serves it")
    left, right = st.columns([3, 2], gap="large")
    a, s = assign[assign.k == k], sites[sites.k == k]
    color_of = dict(zip(s.zone, s.state.map(hub_color)))
    with left:
        fig = go.Figure()
        fig.add_trace(go.Scattermap(
            lat=a.lat, lon=a.lng, mode="markers",
            marker=dict(size=(a.orders.clip(upper=2000) ** 0.5) / 2.2 + 3, color=a.fc_zone.map(color_of), opacity=0.7),
            text=[f"Zone {z} ({st_}) · {o:,} orders · {km:.0f} km to FC"
                  for z, st_, o, km in zip(a.zone, a.state, a.orders, a.road_km)],
            hovertemplate="%{text}<extra></extra>", showlegend=False))
        fig.add_trace(go.Scattermap(
            lat=s.lat, lon=s.lng, mode="markers+text", marker=dict(size=20, color="#0b0b0b"),
            text=s.city.str.title(), textposition="middle right", textfont=dict(size=13, color="#0b0b0b"),
            customdata=s[["state", "orders_served", "share_pct", "avg_km_served"]],
            hovertemplate="<b>FC %{text}-%{customdata[0]}</b><br>%{customdata[1]:,} orders (%{customdata[2]:.1f}%)"
                          "<br>avg %{customdata[3]:.0f} km to customer<extra></extra>", showlegend=False))
        fig.update_layout(map=dict(style="carto-positron", center=dict(lat=-15, lon=-52), zoom=3.0))
        style_fig(fig, 540).update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")
    with right:
        tbl = s.assign(Site=s.city.str.title() + "-" + s.state).sort_values("orders_served", ascending=False)
        st.dataframe(
            tbl[["Site", "orders_served", "share_pct", "avg_km_served"]], hide_index=True, width="stretch",
            column_config={
                "orders_served": st.column_config.NumberColumn("Orders served", format="%d"),
                "share_pct": st.column_config.ProgressColumn("Share", format="%.0f%%", min_value=0, max_value=100),
                "avg_km_served": st.column_config.NumberColumn("Avg km", format="%.0f"),
            })
        if k >= 2:
            callout(f"<b>Value of FC #{k}:</b> about <b>R$ {row.marginal_freight_saving_per_year / 1000:.0f}k/year</b> of "
                    "freight. On freight alone, it only pays off if it costs less than that to run.", "note")
        callout("<b>Why Lagarto / Juiz de Fora?</b> The model picks the point closest to all the demand around it. "
                "A business would choose the nearest big metro instead (see section 4).", "insight")

    section(3, "The trade-off: what each extra FC buys", "Dashed line = today; circle = selected scenario")
    panels = [("avg_km", "Avg distance (km)"), ("pct_within_300km", "Orders within 300 km (%)"),
              ("est_delivery_days", "Est. delivery days")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[p[1] for p in panels], horizontal_spacing=0.08)
    for i, (col, _) in enumerate(panels, start=1):
        fig.add_scatter(x=scen.k, y=scen[col], mode="lines+markers", line=dict(color=SERIES[0], width=2.5),
                        marker=dict(size=9, color=SERIES[0], line=dict(color="#fff", width=2)),
                        hovertemplate="%{x} FCs: %{y:.1f}<extra></extra>", showlegend=False, row=1, col=i)
        fig.add_hline(y=asis[col], line=dict(color=MUTED, dash="dash", width=1.5), row=1, col=i,
                      annotation_text="today", annotation_position="top right", annotation_font_color=MUTED)
        sel = scen[scen.k == k]
        fig.add_scatter(x=sel.k, y=sel[col], mode="markers", showlegend=False, hoverinfo="skip",
                        marker=dict(size=19, color="rgba(0,0,0,0)", line=dict(color="#0b0b0b", width=1.5)), row=1, col=i)
        fig.update_xaxes(title_text="Number of FCs", dtick=1, row=1, col=i)
    st.plotly_chart(style_fig(fig, 340), width="stretch")
    st.caption("The curve bends at 3 FCs: the 3rd FC lifts next-day reach from 39% to 58%. Beyond 5 FCs it is almost flat.")

    section(4, "Cost reality check", "Freight saved per extra FC, and the optimum vs. big-metro networks")
    c1, c2 = st.columns(2, gap="large")
    with c1:
        m2 = scen[scen.k >= 2]
        fig = go.Figure(go.Bar(
            x=m2.k.astype(str) + " FCs", y=m2.marginal_freight_saving_per_year / 1000,
            marker_color=[SERIES[0] if kk == k else LIGHT_BLUE for kk in m2.k],
            text=[f"R$ {v / 1000:.0f}k" for v in m2.marginal_freight_saving_per_year], textposition="outside",
            hovertemplate="Adding FC #%{x}: R$ %{y:.0f}k / year<extra></extra>"))
        fig.update_layout(title="Freight saved by adding each FC (R$ thousand / year)", title_font_size=13,
                          yaxis_range=[0, m2.marginal_freight_saving_per_year.max() / 1000 * 1.25])
        st.plotly_chart(style_fig(fig, 320), width="stretch")
    with c2:
        st.dataframe(
            variants[["variant", "sites", "avg_km", "pct_within_300km", "extra_km_vs_optimal_pct"]],
            hide_index=True, width="stretch",
            column_config={
                "variant": "Network (3 FCs)", "sites": "Sites",
                "avg_km": st.column_config.NumberColumn("Avg km", format="%.0f"),
                "pct_within_300km": st.column_config.NumberColumn("≤300 km", format="%.0f%%"),
                "extra_km_vs_optimal_pct": st.column_config.NumberColumn("vs optimum", format="+%.1f%%"),
            })
        callout("Big metros cost only ~4% more distance but bring workers, warehouses and carriers. "
                "<b>Freight savings are small: the case for FCs is speed.</b>", "insight")

# ================================================================== analysis
with tab_an:
    md_file(ROOT / "site_selection" / "ANALYSIS.md")

# ================================================================== method & data
with tab_m:
    section("A", "Method")
    st.markdown(
        """
1. **Clean data:** valid delivered orders only; one median coordinate per zip code (project 0).
2. **Demand regions (SQL):** orders grouped into 849 three-digit zip regions. **Candidates:** the top 3 regions per state + the top 60 nationally (119).
3. **p-median model:** open exactly *k* sites, assign every region to one, and minimise order-weighted road distance (straight line × 1.3). Solved to proven optimality with PuLP + HiGHS for k = 1…6.
4. **From km to KPIs:** regressions on ~110k real shipments. Delivery days ≈ 8.6 + 0.47 per 100 km (R² 0.18). Freight ≈ R$ 8.2 + 0.82 per 100 km + 2.58 per kg (R² 0.53).
"""
    )
    section("B", "Assumptions & limitations")
    st.markdown(
        """
- **Outbound only.** Restocking FCs from sellers is not costed (76% of supply is already in São Paulo).
- **No FC fixed costs.** They are not in the data, so the break-even cost per FC is shown instead.
- **Estimated KPIs are directional** (R² 0.18 for days). Use them to compare scenarios, not to promise an SLA.
- **No capacity limits.** São Paulo would serve ~50–60% of volume.
- **Historical demand (2017–18).** Volume growth would strengthen the freight case.
"""
    )
    section("C", "All scenarios")
    st.dataframe(
        summary.drop(columns=["est_freight_total"]), hide_index=True, width="stretch",
        column_config={
            "avg_km": st.column_config.NumberColumn("Avg km", format="%.0f"),
            "pct_within_300km": st.column_config.NumberColumn("≤300 km %", format="%.1f"),
            "pct_within_800km": st.column_config.NumberColumn("≤800 km %", format="%.1f"),
            "est_delivery_days": st.column_config.NumberColumn("Est. days", format="%.2f"),
            "est_freight_per_item": st.column_config.NumberColumn("Freight / item (R$)", format="%.2f"),
            "est_freight_per_year": st.column_config.NumberColumn("Freight / year (R$)", format="%.0f"),
            "marginal_freight_saving_per_year": st.column_config.NumberColumn("Saved by this FC (R$/yr)", format="%.0f"),
        })
