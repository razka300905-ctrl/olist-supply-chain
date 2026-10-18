"""Project 1 - Site selection: how many fulfilment centres, and where?"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import MUTED, SERIES, fc_label, hub_color, load_site, setup_page

setup_page("Site Selection", "📍")

summary = load_site("scenario_summary")
sites = load_site("selected_sites", dtype={"zone": str})
assign = load_site("zone_assignment", dtype={"zone": str, "fc_zone": str})
variants = load_site("practical_variants_k3")
asis = summary.iloc[0]
scen = summary[summary.k >= 1]

st.title("1 · Where should Olist open fulfilment centres?")
st.markdown(
    "Today **every seller ships directly to the customer**. 76% of items leave São Paulo state, but only 42% of orders "
    "go there, so the average parcel travels **~775 km** and takes **12 days**. If Olist moved to fulfilment centres "
    "(FCs), how many should it open, and where?"
)

st.success(
    "**Recommendation: start with 3 FCs** (São Paulo, the Minas Gerais/Rio corridor, the Northeast). That nearly "
    "halves the distance to customers and doubles next-day reach. A metro network (**São Paulo + Rio + Salvador**) is "
    "only 4% worse than the mathematical optimum and is easier to staff and supply."
)

# ------------------------------------------------------------------ scenario picker + KPIs
k = st.select_slider("Number of fulfilment centres", options=list(range(1, 7)), value=3,
                     format_func=fc_label)
row = summary[summary.k == k].iloc[0]


def delta(col, fmt, inverse=False):
    d = row[col] - asis[col]
    return fmt.format(d), ("inverse" if inverse else "normal")


m = st.columns(5)
for col_, (label, col, fmt, dfmt, inv) in zip(m, [
    ("Avg. distance to customer", "avg_km", "{:.0f} km", "{:+.0f} km", True),
    ("Orders within 300 km", "pct_within_300km", "{:.0f}%", "{:+.0f} pp", False),
    ("Orders within 800 km", "pct_within_800km", "{:.0f}%", "{:+.0f} pp", False),
    ("Est. delivery time", "est_delivery_days", "{:.1f} days", "{:+.1f} days", True),
    ("Est. freight per item", "est_freight_per_item", "R$ {:.2f}", "{:+.2f} R$", True),
]):
    d, color = delta(col, dfmt, inv)
    col_.metric(label, fmt.format(row[col]), f"{d} vs today", delta_color=color)
st.caption("Deltas compare with today's model, where sellers ship direct. 300 km ≈ next-day and 800 km ≈ 2-day ground reach.")

# ------------------------------------------------------------------ map + site table
left, right = st.columns([3, 2], gap="large")
a, s = assign[assign.k == k], sites[sites.k == k]
color_of = dict(zip(s.zone, s.state.map(hub_color)))

with left:
    st.subheader(f"Network with {fc_label(k)}")
    fig = go.Figure()
    fig.add_trace(go.Scattermap(
        lat=a.lat, lon=a.lng, mode="markers",
        marker=dict(size=(a.orders.clip(upper=2000) ** 0.5) / 2.2 + 3, color=a.fc_zone.map(color_of), opacity=0.7),
        text=[f"Zone {z} ({st_}) · {o:,} orders · {km:.0f} km to FC"
              for z, st_, o, km in zip(a.zone, a.state, a.orders, a.road_km)],
        hovertemplate="%{text}<extra></extra>", name="Demand zones", showlegend=False,
    ))
    fig.add_trace(go.Scattermap(
        lat=s.lat, lon=s.lng, mode="markers+text",
        marker=dict(size=20, color="#0b0b0b"),
        text=s.city.str.title(), textposition="middle right", textfont=dict(size=13, color="#0b0b0b"),
        customdata=s[["state", "orders_served", "share_pct", "avg_km_served"]],
        hovertemplate="<b>FC %{text}-%{customdata[0]}</b><br>%{customdata[1]:,} orders (%{customdata[2]:.1f}%)"
                      "<br>avg %{customdata[3]:.0f} km to customer<extra></extra>",
        name="FC", showlegend=False,
    ))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=-15, lon=-52), zoom=3.0),
                      height=560, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, width="stretch")
    st.caption("Dot = demand zone (3-digit zip region, size = orders); colour = the FC that serves it; black = FC. "
               "Hover for details.")

with right:
    st.subheader("Chosen sites")
    tbl = s.assign(Site=s.city.str.title() + "-" + s.state).sort_values("orders_served", ascending=False)
    st.dataframe(
        tbl[["Site", "orders_served", "share_pct", "avg_km_served"]],
        hide_index=True, width="stretch",
        column_config={
            "orders_served": st.column_config.NumberColumn("Orders served", format="%d"),
            "share_pct": st.column_config.ProgressColumn("Share", format="%.0f%%", min_value=0, max_value=100),
            "avg_km_served": st.column_config.NumberColumn("Avg km", format="%.0f"),
        },
    )
    saving = row.marginal_freight_saving_per_year
    if k >= 2:
        st.markdown(f"**Value of the {k}th FC:** about **R$ {saving / 1000:.0f}k/year** in freight. "
                    "It only pays off on freight alone if it costs less than that to run.")
    st.markdown(
        "**Why Lagarto / Juiz de Fora?** The model picks the point that minimises distance to all demand around it. "
        "That is mathematically optimal, but a business would usually choose the nearest big metro (see the "
        "comparison below)."
    )

st.divider()

# ------------------------------------------------------------------ trade-off curves
st.subheader("The trade-off: what each extra FC buys")
panels = [("avg_km", "Avg. distance (km)"), ("pct_within_300km", "Orders within 300 km (%)"),
          ("est_delivery_days", "Est. delivery days")]
fig = make_subplots(rows=1, cols=3, subplot_titles=[p[1] for p in panels], horizontal_spacing=0.08)
for i, (col, title) in enumerate(panels, start=1):
    fig.add_scatter(x=scen.k, y=scen[col], mode="lines+markers", line=dict(color=SERIES[0], width=2),
                    marker=dict(size=9, color=SERIES[0], line=dict(color="#fcfcfb", width=2)),
                    hovertemplate="%{x} FCs: %{y:.1f}<extra></extra>", showlegend=False, row=1, col=i)
    fig.add_hline(y=asis[col], line=dict(color=MUTED, dash="dash", width=1.5), row=1, col=i,
                  annotation_text="today", annotation_position="top right", annotation_font_color=MUTED)
    sel = scen[scen.k == k]
    fig.add_scatter(x=sel.k, y=sel[col], mode="markers", showlegend=False, hoverinfo="skip",
                    marker=dict(size=18, color="rgba(0,0,0,0)", line=dict(color="#0b0b0b", width=1.5)), row=1, col=i)
    fig.update_xaxes(title_text="Number of FCs", dtick=1, row=1, col=i)
fig.update_layout(height=340, margin=dict(l=0, r=0, t=40, b=0))
st.plotly_chart(fig, width="stretch")
st.caption("The curve bends at 3 FCs: the 3rd FC lifts next-day reach from 39% to 58%, the biggest single jump. "
           "Beyond 5 FCs it is almost flat.")

c1, c2 = st.columns(2, gap="large")
with c1:
    st.subheader("Freight saved by each extra FC")
    m2 = scen[scen.k >= 2]
    fig = go.Figure(go.Bar(
        x=m2.k.astype(str) + " FCs", y=m2.marginal_freight_saving_per_year / 1000,
        marker_color=[SERIES[0] if kk == k else "#86b6ef" for kk in m2.k],
        text=[f"R$ {v / 1000:.0f}k" for v in m2.marginal_freight_saving_per_year], textposition="outside",
        hovertemplate="Adding FC #%{x}: R$ %{y:.0f}k / year<extra></extra>",
    ))
    fig.update_layout(height=320, margin=dict(l=0, r=0, t=10, b=0), yaxis_title="R$ thousand / year",
                      yaxis_range=[0, m2.marginal_freight_saving_per_year.max() / 1000 * 1.25])
    st.plotly_chart(fig, width="stretch")
    st.caption("At today's volume, freight savings are small. **The case for FCs is faster delivery**, not cheaper freight.")
with c2:
    st.subheader("Optimum vs. practical metro networks (3 FCs)")
    st.dataframe(
        variants[["variant", "sites", "avg_km", "pct_within_300km", "extra_km_vs_optimal_pct"]],
        hide_index=True, width="stretch",
        column_config={
            "variant": "Network", "sites": "Sites",
            "avg_km": st.column_config.NumberColumn("Avg km", format="%.0f"),
            "pct_within_300km": st.column_config.NumberColumn("≤300 km", format="%.0f%%"),
            "extra_km_vs_optimal_pct": st.column_config.NumberColumn("vs optimum", format="+%.1f%%"),
        },
    )
    st.caption("Choosing big metros costs only about 4% more distance but brings labour, real estate and carrier access.")

st.divider()

# ------------------------------------------------------------------ full table, method, limitations
with st.expander("All scenarios (data table)"):
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
        },
    )

with st.expander("Method"):
    st.markdown(
        """
1. **Clean data**: valid delivered orders only (`is_valid_delivered = 1`); one median coordinate per zip code.
2. **Demand zones (SQL)**: orders are added up into 849 three-digit zip regions. **Candidate sites**: the top 3 regions per state plus the top 60 nationally (119).
3. **p-median model**: open exactly *k* sites and assign every region to one, minimising order-weighted road distance (straight-line distance × 1.3). Solved to proven optimality with PuLP + HiGHS for k = 1…6.
4. **From km to business KPIs**: two regressions on about 110k real shipments. Delivery days ≈ 8.6 + 0.47 per 100 km (R² 0.18). Freight ≈ R$ 8.2 + 0.82 per 100 km + 2.58 per kg (R² 0.53).
"""
    )

with st.expander("Assumptions & limitations"):
    st.markdown(
        """
- **Outbound only.** Restocking FCs from sellers is not costed yet (76% of supply is already in São Paulo).
- **No FC fixed costs.** These are not in the data, so the break-even cost per FC is shown instead.
- **Estimated KPIs are directional** (R² 0.18 for days). Use them to compare scenarios, not to promise an SLA.
- **No capacity limits.** São Paulo would serve about 50–60% of volume.
- **Historical demand (2017–18).** Volume growth would strengthen the freight case.
"""
    )
