"""Project 2 - Vehicle routing: daily last-mile delivery from the São Paulo FC."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import ROOT, SERIES, setup_page

setup_page("Vehicle Routing", "🚚")

VRP_OUT = ROOT / "vrp" / "outputs"
TYPE_COLOR = {"van": SERIES[0], "motorbike": SERIES[1]}
FLEET_LABEL = {"van_only": "Van only", "motorbike_only": "Motorbike only", "mixed": "Mixed fleet"}
DAY_LABEL = {"normal": "Normal day", "black_friday": "Black Friday"}


@st.cache_data
def load(name):
    return pd.read_csv(VRP_OUT / f"{name}.csv")


sc = load("vrp_scenarios")
routes = load("vrp_routes")
depot = load("depot").iloc[0]
assumptions = load("vrp_assumptions")


def row(sid):
    return sc[sc.scenario == sid].iloc[0]


nm, bm, bv, bf = row("normal__mixed"), row("black_friday__mixed"), row("black_friday__van_only"), row("black_friday__normal_fleet")

st.title("2 · How should the São Paulo FC deliver every day?")
st.markdown(
    f"Project 1 placed a fulfilment centre in **São Paulo**. This project plans its **daily last-mile routes** "
    f"to customers in Grande São Paulo. It compares a normal day ({int(nm.orders)} orders, {nm.date}) with "
    f"**Black Friday 2017** ({int(bm.orders)} orders, the busiest day in the data), and vans, motorbikes or a mix of both."
)
st.success(
    f"**Recommendation: run a mixed fleet and plan extra capacity for peaks.** On a normal day, 2 vans + 2 motorbikes "
    f"deliver everything at **R$ {nm.cost_per_order:.2f} per order**. Black Friday needs about "
    f"**{int(bm.vans + bm.motorbikes)} vehicles**. With only the normal-day fleet, **{int(bf.orders_not_delivered)} of "
    f"{int(bf.orders)} orders ({bf.orders_not_delivered / bf.orders * 100:.0f}%)** would slip to the next day."
)

# ------------------------------------------------------------------ scenario pickers
c1, c2 = st.columns([1, 2])
day = c1.segmented_control("Day", list(DAY_LABEL), default="normal", format_func=DAY_LABEL.get)
fleet_opts = list(FLEET_LABEL) + (["normal_fleet"] if day == "black_friday" else [])
fleet_fmt = {**FLEET_LABEL, "normal_fleet": "Normal-day fleet only"}
fleet = c2.segmented_control("Fleet", fleet_opts, default="mixed", format_func=fleet_fmt.get)
day, fleet = day or "normal", fleet or "mixed"
sid = f"{day}__{fleet}"
r = row(sid)
rt = routes[routes.scenario == sid]

m = st.columns(5)
m[0].metric("Vehicles used", int(r.vans + r.motorbikes),
            help="Vans + motorbikes", delta=f"{int(r.vans)} van · {int(r.motorbikes)} moto", delta_color="off")
m[1].metric("Total distance", f"{r.total_km:,.0f} km", f"{r.km_per_order:.1f} km per order", delta_color="off")
if fleet == "normal_fleet":  # fleet is capped, so the solver maximises deliveries - a cost comparison is not meaningful
    m[2].metric("Cost per delivered order", f"R$ {r.cost_per_order:.2f}", "fleet capped", delta_color="off")
else:
    m[2].metric("Cost per order", f"R$ {r.cost_per_order:.2f}",
                f"{-r.cost_saving_vs_baseline_pct:+.0f}% vs greedy plan", delta_color="inverse")
m[3].metric("Longest route", f"{r.max_route_hours:.1f} h", "shift = 9 h", delta_color="off")
m[4].metric("Orders not delivered", int(r.orders_not_delivered),
            "too bulky for a motorbike" if r.orders_too_big_for_fleet else
            ("fleet too small" if r.orders_not_delivered else "all delivered"), delta_color="off")
st.caption("Greedy plan = always drive to the nearest next stop, the way a simple dispatcher would. "
           "The optimised plan is solved with Google OR-Tools.")

# ------------------------------------------------------------------ route map + route table
left, right = st.columns([3, 2], gap="large")
with left:
    fig = go.Figure()
    shown = set()
    for route_id, g in rt.groupby("route"):
        g = g.sort_values("seq")
        t = g.vehicle_type.iloc[0]
        fig.add_trace(go.Scattermap(
            lat=g.lat, lon=g.lng, mode="lines+markers",
            line=dict(width=2.5, color=TYPE_COLOR[t]), marker=dict(size=7, color=TYPE_COLOR[t]),
            name=t.title(), legendgroup=t, showlegend=t not in shown,
            text=[f"Route {route_id} ({t}) · stop {s} · {c.title()} · arrives {int(a // 60):02d}:{int(a % 60):02d} into shift"
                  for s, c, a in zip(g.seq, g.city, g.arrival_min)],
            hovertemplate="%{text}<extra></extra>",
        ))
        shown.add(t)
    fig.add_trace(go.Scattermap(lat=[depot.lat], lon=[depot.lng], mode="markers+text", text=["FC São Paulo"],
                                textposition="bottom right", marker=dict(size=18, color="#0b0b0b"),
                                name="FC", showlegend=False, hovertemplate="FC São Paulo<extra></extra>"))
    fig.update_layout(map=dict(style="carto-positron", center=dict(lat=float(rt.lat.mean()), lon=float(rt.lng.mean())), zoom=8.6),
                      height=540, margin=dict(l=0, r=0, t=0, b=0),
                      legend=dict(orientation="h", x=0, y=1.0, bgcolor="rgba(255,255,255,0.8)"))
    st.plotly_chart(fig, width="stretch")
    st.caption("Each line is one vehicle's route, starting and ending at the FC. Hover a stop for its order in the route.")

with right:
    st.subheader("Routes")
    per = (rt[rt.order_id != "FC"].groupby(["route", "vehicle_type"])
             .agg(stops=("order_id", "nunique"), km=("route_km", "first"), hours=("route_min", "first"),
                  volume=("volume_util_pct", "first"))
             .reset_index())
    per["hours"] = per.hours / 60
    st.dataframe(
        per, hide_index=True, width="stretch", height=430,
        column_config={
            "route": st.column_config.NumberColumn("Route", format="%d"),
            "vehicle_type": "Vehicle",
            "stops": st.column_config.NumberColumn("Stops", format="%d"),
            "km": st.column_config.NumberColumn("Km", format="%.0f"),
            "hours": st.column_config.ProgressColumn("Hours (of 9)", format="%.1f", min_value=0, max_value=9),
            "volume": st.column_config.NumberColumn("Load (vol. %)", format="%.0f%%"),
        },
    )
    st.caption("Van routes are limited by **time**, not space (load far below 100%). "
               "Motorbike routes are limited by **box volume**.")

st.divider()

# ------------------------------------------------------------------ comparison across scenarios
st.subheader("Which fleet is cheapest?")
main3 = sc[sc.fleet.isin(FLEET_LABEL)]
fig = make_subplots(rows=1, cols=2, subplot_titles=[f"{DAY_LABEL[d]} ({int(main3[main3.day == d].orders.iloc[0])} orders)"
                                                    for d in DAY_LABEL], shared_yaxes=True)
for i, d in enumerate(DAY_LABEL, start=1):
    x = main3[main3.day == d].set_index("fleet").loc[list(FLEET_LABEL)]
    best = x.cost_per_order.idxmin()
    fig.add_bar(x=[FLEET_LABEL[f] for f in x.index], y=x.cost_per_order, row=1, col=i, showlegend=False,
                marker_color=[SERIES[0] if f == best else "#b7d3f6" for f in x.index],
                text=[f"R$ {v:.2f}" for v in x.cost_per_order], textposition="outside",
                customdata=x[["vans", "motorbikes", "orders_not_delivered"]],
                hovertemplate="%{x}: R$ %{y:.2f} per order<br>%{customdata[0]} vans, %{customdata[1]} motorbikes"
                              "<br>%{customdata[2]} orders not delivered<extra></extra>")
fig.update_yaxes(title_text="R$ per delivered order", range=[0, main3.cost_per_order.max() * 1.25], row=1, col=1)
fig.update_layout(height=340, margin=dict(l=0, r=0, t=40, b=0), bargap=0.35)
st.plotly_chart(fig, width="stretch")
st.markdown(
    f"- **Mixed fleet wins on both days.** Vans carry the bulky parcels, and motorbikes take the many small ones "
    f"more cheaply.\n"
    f"- **Motorbike only looks cheap but fails service:** {int(row('normal__motorbike_only').orders_too_big_for_fleet)} "
    f"orders on a normal day are too bulky for a motorbike box.\n"
    f"- **Density lowers cost:** with 4× the orders, cost per order *falls* from R$ {nm.cost_per_order:.2f} to "
    f"R$ {bm.cost_per_order:.2f}, because stops are closer together. Growth makes last-mile cheaper per parcel."
)

with st.expander("All scenarios (data table)"):
    st.dataframe(sc.drop(columns=["fleet_bound_reached"], errors="ignore"), hide_index=True, width="stretch")

with st.expander("Assumptions (illustrative, not from the dataset)"):
    a = assumptions[assumptions.vehicle_type != "shift"].set_index("vehicle_type")
    st.dataframe(a.rename(columns={"weight_kg": "Max kg", "volume_l": "Max litres", "speed_kmh": "Avg km/h",
                                   "service_min": "Min per stop", "cost_per_km": "R$ per km",
                                   "cost_per_day": "R$ per vehicle-day"}), width="stretch")
    st.markdown("- One shift = **9 hours**, from the FC and back. Orders bought on day D are delivered on day D+1 from FC stock.\n"
                "- Distance = straight line × 1.3 (same as project 1); customer location = zip-code centroid.")

with st.expander("Method & limitations"):
    st.markdown(
        """
**Model.** This is a capacitated vehicle routing problem with a shift-length limit (CVRP with a time limit), on a heterogeneous fleet.
Every order is visited once, and every vehicle respects its weight, volume and 9-hour limit. The objective is to minimise
(fixed cost per vehicle) + (cost per km). It is solved with **Google OR-Tools** (guided local search). The mixed-fleet search
starts from the van-only plan, so it can only match or beat it.

**Data.** Valid delivered orders from the cleaned dataset, with weight and volume summed from the product data, for
customers in Grande São Paulo (zip codes 01000–09999).

**Limitations.** There is no real road network or traffic, and no delivery time windows. Locations are zip-level, so
several orders can share a point. Costs and capacities are assumptions, and the result is a planning estimate, not an
operational schedule.
"""
    )
