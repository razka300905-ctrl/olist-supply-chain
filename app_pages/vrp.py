"""Project 2 - Vehicle routing: daily last-mile delivery from the São Paulo FC."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import (LIGHT_BLUE, ROOT, SERIES, callout, hero, kpis, md_file, purpose, section, setup_page,
                        style_fig)

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


nm, bm, bf = row("normal__mixed"), row("black_friday__mixed"), row("black_friday__normal_fleet")

hero("Project 2 · Last-mile delivery",
     "How should the São Paulo FC deliver every day?",
     f"Daily routes from the FC chosen in project 1 to customers across Grande São Paulo. A normal day "
     f"({int(nm.orders)} orders) is compared with Black Friday 2017 ({int(bm.orders)} orders), using vans, motorbikes "
     "or a mix of both.",
     ["Vehicle routing (CVRP)", "Google OR-Tools", "7 scenarios", "Grande São Paulo, 11–23 cities"])

purpose(
    "How many vehicles, which type, at what cost per delivery, and what happens on a peak day?",
    "Deliver every order within one shift at the lowest cost, and size the extra capacity a peak needs.",
    "Optimised routes per vehicle, the fleet size and mix, the cost per order and the peak-day capacity gap.",
    "Last-mile operations and fleet managers, and capacity planners preparing for campaigns such as Black Friday.",
)

callout(f"<b>Recommendation: run a mixed fleet (vans + motorbikes) and contract extra riders for peaks.</b> "
        f"A normal day needs 2 vans + 2 motorbikes at <b>R$ {nm.cost_per_order:.2f}</b> per order. With only that fleet, "
        f"<b>{int(bf.orders_not_delivered)} of {int(bf.orders)}</b> Black Friday orders would be a day late.")
kpis([
    {"label": "Normal-day fleet", "value": f"{int(nm.vans)} vans + {int(nm.motorbikes)} motos", "note": f"{int(nm.orders)} orders, all delivered"},
    {"label": "Cost per order", "value": f"R$ {nm.cost_per_order:.2f}", "note": f"↓ {nm.cost_saving_vs_baseline_pct:.0f}% vs greedy plan", "tone": "good"},
    {"label": "Black Friday fleet", "value": f"{int(bm.vans + bm.motorbikes)} vehicles", "note": f"{int(bm.vans)} vans + {int(bm.motorbikes)} motos for {int(bm.orders)} orders"},
    {"label": "Peak gap (normal fleet)", "value": f"{bf.orders_not_delivered / bf.orders * 100:.0f}% late", "note": f"{int(bf.orders_not_delivered)} orders slip a day", "tone": "bad"},
])

tab_res, tab_an, tab_m = st.tabs(["📊  Results & routes", "🧭  Analysis: what we chose and why", "⚙️  Method & data"])

# ================================================================== results
with tab_res:
    section(1, "Pick a day and a fleet", "Every combination was solved separately with OR-Tools")
    c1, c2 = st.columns([1, 2])
    day = c1.segmented_control("Day", list(DAY_LABEL), default="normal", format_func=DAY_LABEL.get)
    fleet_opts = list(FLEET_LABEL) + (["normal_fleet"] if day == "black_friday" else [])
    fleet_fmt = {**FLEET_LABEL, "normal_fleet": "Normal-day fleet only"}
    fleet = c2.segmented_control("Fleet", fleet_opts, default="mixed", format_func=fleet_fmt.get)
    day, fleet = day or "normal", fleet or "mixed"
    sid = f"{day}__{fleet}"
    r = row(sid)
    rt = routes[routes.scenario == sid]

    if fleet == "normal_fleet":   # fleet is capped, so the solver maximises deliveries - a cost comparison is not meaningful
        cost_card = {"label": "Cost per delivered order", "value": f"R$ {r.cost_per_order:.2f}", "note": "fleet capped"}
    else:
        cost_card = {"label": "Cost per order", "value": f"R$ {r.cost_per_order:.2f}",
                     "note": f"↓ {r.cost_saving_vs_baseline_pct:.0f}% vs greedy plan", "tone": "good"}
    undelivered_note = ("too bulky for a motorbike" if r.orders_too_big_for_fleet else
                        ("fleet too small" if r.orders_not_delivered else "all delivered"))
    kpis([
        {"label": "Vehicles used", "value": int(r.vans + r.motorbikes), "note": f"{int(r.vans)} van · {int(r.motorbikes)} moto"},
        {"label": "Total distance", "value": f"{r.total_km:,.0f} km", "note": f"{r.km_per_order:.1f} km per order"},
        cost_card,
        {"label": "Longest route", "value": f"{r.max_route_hours:.1f} h", "note": "shift limit = 9 h"},
        {"label": "Not delivered", "value": int(r.orders_not_delivered), "note": undelivered_note,
         "tone": "bad" if r.orders_not_delivered else "good"},
    ])

    section(2, "The routes", "Each line is one vehicle's round trip from the FC. Hover a stop for its sequence and arrival time.")
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
                text=[f"Route {route_id} ({t}) · stop {s} · {c.title()} · {int(a // 60):02d}:{int(a % 60):02d} into shift"
                      for s, c, a in zip(g.seq, g.city, g.arrival_min)],
                hovertemplate="%{text}<extra></extra>"))
            shown.add(t)
        fig.add_trace(go.Scattermap(lat=[depot.lat], lon=[depot.lng], mode="markers+text", text=["FC São Paulo"],
                                    textposition="bottom right", marker=dict(size=18, color="#0b0b0b"),
                                    showlegend=False, hovertemplate="FC São Paulo<extra></extra>"))
        fig.update_layout(map=dict(style="carto-positron", center=dict(lat=float(rt.lat.mean()), lon=float(rt.lng.mean())), zoom=8.6),
                          legend=dict(orientation="h", x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.85)"))
        style_fig(fig, 520).update_layout(margin=dict(l=0, r=0, t=0, b=0))
        st.plotly_chart(fig, width="stretch")
    with right:
        per = (rt[rt.order_id != "FC"].groupby(["route", "vehicle_type"])
                 .agg(stops=("order_id", "nunique"), km=("route_km", "first"), hours=("route_min", "first"),
                      volume=("volume_util_pct", "first"))
                 .reset_index())
        per["hours"] = per.hours / 60
        st.dataframe(per, hide_index=True, width="stretch", height=400, column_config={
            "route": st.column_config.NumberColumn("Route", format="%d"), "vehicle_type": "Vehicle",
            "stops": st.column_config.NumberColumn("Stops", format="%d"),
            "km": st.column_config.NumberColumn("Km", format="%.0f"),
            "hours": st.column_config.ProgressColumn("Hours (of 9)", format="%.1f", min_value=0, max_value=9),
            "volume": st.column_config.NumberColumn("Load (vol. %)", format="%.0f%%")})
        callout("Vans are limited by <b>time</b> (load far below 100%), motorbikes by <b>box volume</b>.", "insight")

    section(3, "Which fleet is cheapest?", "Cost per delivered order for each fleet, on both days")
    main3 = sc[sc.fleet.isin(FLEET_LABEL)]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        subplot_titles=[f"{DAY_LABEL[d]} ({int(main3[main3.day == d].orders.iloc[0])} orders)" for d in DAY_LABEL])
    for i, d in enumerate(DAY_LABEL, start=1):
        x = main3[main3.day == d].set_index("fleet").loc[list(FLEET_LABEL)]
        best = x.cost_per_order.idxmin()
        fig.add_bar(x=[FLEET_LABEL[f] for f in x.index], y=x.cost_per_order, row=1, col=i, showlegend=False,
                    marker_color=[SERIES[0] if f == best else LIGHT_BLUE for f in x.index],
                    text=[f"R$ {v:.2f}" for v in x.cost_per_order], textposition="outside",
                    customdata=x[["vans", "motorbikes", "orders_not_delivered"]],
                    hovertemplate="%{x}: R$ %{y:.2f} per order<br>%{customdata[0]} vans, %{customdata[1]} motorbikes"
                                  "<br>%{customdata[2]} orders not delivered<extra></extra>")
    fig.update_yaxes(title_text="R$ per delivered order", range=[0, main3.cost_per_order.max() * 1.25], row=1, col=1)
    st.plotly_chart(style_fig(fig, 340).update_layout(bargap=0.35), width="stretch")
    callout(f"<b>Mixed wins on both days.</b> Motorbike-only looks cheap but leaves "
            f"{int(row('normal__motorbike_only').orders_too_big_for_fleet)} bulky orders undelivered. With 4× the orders, "
            f"cost per order <i>falls</i> (R$ {nm.cost_per_order:.2f} → R$ {bm.cost_per_order:.2f}), because the stops are denser.",
            "insight")

    section(4, "Where the orders go", "The service area is the whole metro region, not only São Paulo city")
    cities = load("orders_by_city")
    cities = cities[cities.day == day].assign(city=lambda d: d.city.str.title())
    st.dataframe(cities[["city", "orders", "share_pct"]], hide_index=True, width="stretch", height=280,
                 column_config={"city": "Municipality", "orders": st.column_config.NumberColumn("Orders", format="%d"),
                                "share_pct": st.column_config.ProgressColumn("Share", format="%.0f%%", min_value=0, max_value=100)})

# ================================================================== analysis
with tab_an:
    md_file(ROOT / "vrp" / "ANALYSIS.md")

# ================================================================== method & data
with tab_m:
    section("A", "Method")
    st.markdown(
        """
**Model.** A capacitated vehicle routing problem with a 9-hour shift limit and a mixed fleet. Every order is visited once,
and every vehicle respects its weight, volume and time limits. The objective is to minimise (cost per vehicle-day) +
(cost per km). It is solved with **Google OR-Tools** (guided local search). The mixed-fleet search starts from the van-only
plan, so it can only match or beat it.

**Data.** Valid delivered orders for customers in Grande São Paulo (zip 01000–09999), with weight and volume from the
product data.
"""
    )
    section("B", "Assumptions (illustrative, not from the dataset)")
    a = assumptions[assumptions.vehicle_type != "shift"].set_index("vehicle_type")
    st.dataframe(a.rename(columns={"weight_kg": "Max kg", "volume_l": "Max litres", "speed_kmh": "Avg km/h",
                                   "service_min": "Min per stop", "cost_per_km": "R$ per km",
                                   "cost_per_day": "R$ per vehicle-day"}), width="stretch")
    st.markdown("- One shift = **9 hours**, FC to FC. Orders bought on day D are delivered on day D+1 from FC stock.\n"
                "- Distance = straight line × 1.3 (as in project 1); customer location = zip-code centroid.")
    section("C", "Limitations")
    st.markdown("No real road network or traffic · no customer time windows · zip-level locations · assumed costs. "
                "Results vary ±1–2% between runs because the solver stops at a time limit; the fleet ranking is stable.")
    section("D", "All scenarios")
    st.dataframe(sc.drop(columns=["fleet_bound_reached"], errors="ignore"), hide_index=True, width="stretch")
