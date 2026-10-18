"""Project 3 - Inventory: what the São Paulo FC should stock, how much, and when to reorder."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import (LIGHT_BLUE, ROOT, SERIES, callout, hero, kpis, md_file, purpose, section, setup_page,
                        style_fig)

setup_page("Inventory", "📦")

INV_OUT = ROOT / "inventory" / "outputs"


@st.cache_data
def load(name, **kw):
    return pd.read_csv(INV_OUT / f"{name}.csv", **kw)


t = load("policy_tradeoff")
seg = load("segmentation_summary").iloc[0]
matrix = load("abc_pattern_matrix", index_col=0)
curve = load("sku_coverage_curve")
fc = load("forecast_backtest")
prods = load("policy_by_product")
chosen = t[(t.sweep == "stock_rule") & (t.stock_rule_min_weeks == 6)].iloc[0]
static = t[t.sweep == "planning"].iloc[0]

hero("Project 3 · Inventory policy",
     "What should the São Paulo FC stock, and how much?",
     "About 19,000 different products reached the FC's area in one year, and most sell only once or twice. This project "
     "decides which products to hold, how many, and when to reorder, then tests the policy day by day on 16 unseen weeks.",
     ["ABC × demand pattern", "Forecast backtest", "Reorder point + EOQ", "Day-by-day simulation"])

purpose(
    "Which products should the FC hold, how many of each, and when should it reorder?",
    "Ship as many units as possible from FC stock while keeping capital, space and cost under control.",
    "A stock list with reorder points per product, service-level and assortment trade-offs, and a tested policy.",
    "Inventory planners and category managers, plus the finance team that funds the stock.",
)

callout(f"<b>Recommendation: stock only the ~{int(chosen.products_listed_last_week)} most regular products</b> "
        "(sold in ≥6 of the last 12 weeks), <b>re-plan every Monday</b> and target a 95% service level. "
        "Sellers keep shipping everything else directly.")
kpis([
    {"label": "Products in the FC", "value": f"{int(chosen.products_listed_last_week)}", "note": "of ~19,000 sold in the area"},
    {"label": "Units shipped from FC", "value": f"{chosen.fc_share_of_all_units_pct:.1f}%", "note": "rest shipped by sellers"},
    {"label": "Fill rate", "value": f"{chosen.fill_rate_pct:.1f}%", "note": "on stocked products"},
    {"label": "Average stock", "value": f"R$ {chosen.avg_inventory_value / 1000:.0f}k",
     "note": f"{chosen.weeks_of_cover:.1f} weeks of cover · {chosen.avg_space_m3:.0f} m³"},
    {"label": "Cost per unit", "value": f"R$ {chosen.cost_per_unit_served:.2f}", "note": "holding + orders + returns"},
])
callout("<b>Key finding:</b> 52% of units sold in the test weeks came from products with <b>no sales at all</b> in the "
        "previous 34 weeks. Volume is stable but the products keep changing, so the plan is rebuilt every Monday.", "insight")

tab_res, tab_an, tab_m = st.tabs(["📊  Results & trade-offs", "🧭  Analysis: what we chose and why", "⚙️  Method & data"])

# ================================================================== results
with tab_res:
    section(1, "Explore the trade-offs", "Pick a decision; the dark bar is the recommended policy")
    SWEEPS = {
        "stock_rule": ("How many products?", "stock_rule_min_weeks", lambda v: f"≥{int(v)}/12"),
        "service_level": ("Which service level?", "service_level_pct", lambda v: f"{v:.0f}%"),
        "order_cap": ("How much to order at once?", "order_cap_weeks", lambda v: f"{v} wk" if str(v).isdigit() else "EOQ"),
    }
    sweep = st.segmented_control("Decision", list(SWEEPS), default="stock_rule", format_func=lambda k: SWEEPS[k][0])
    sweep = sweep or "stock_rule"
    _, col, fmt = SWEEPS[sweep]
    s = t[t.sweep == sweep].copy()
    s["_o"] = s[col].map(lambda v: float(v) if str(v).replace(".", "").isdigit() else 999)
    s = s.sort_values("_o")
    labels = [fmt(v) for v in s[col]]
    is_chosen = [(r.stock_rule_min_weeks == 6 and r.service_level_pct == 95 and str(r.order_cap_weeks) == "8")
                 for r in s.itertuples()]
    fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.06,
                        subplot_titles=["Units from FC (%)", "Fill rate (%)", "Cost per unit (R$)", "Weeks of cover"])
    for i, (c, f) in enumerate([("fc_share_of_all_units_pct", "{:.1f}%"), ("fill_rate_pct", "{:.1f}%"),
                                ("cost_per_unit_served", "R$ {:.2f}"), ("weeks_of_cover", "{:.1f}")], start=1):
        fig.add_bar(x=labels, y=s[c], row=1, col=i, showlegend=False,
                    marker_color=[SERIES[0] if ch else LIGHT_BLUE for ch in is_chosen],
                    text=[f.format(v) for v in s[c]], textposition="outside",
                    hovertemplate="%{x}: %{y:.2f}<extra></extra>")
        fig.update_yaxes(range=[0, s[c].max() * 1.28], row=1, col=i)
    fig.update_xaxes(tickangle=0)
    st.plotly_chart(style_fig(fig, 340).update_layout(bargap=0.3), width="stretch")
    captions = {
        "stock_rule": "Going deeper into the range doubles the FC share but almost doubles the cost of every unit. "
                      "≥6 of 12 weeks is the balance.",
        "service_level": "From 50% to 95% the fill rate rises ~3 points. Above 95% stock grows but fill rate does not: "
                         "the misses come mostly from newly listed products still waiting for their first delivery.",
        "order_cap": "Pure EOQ is ~2% cheaper on paper but holds 15 weeks of stock. A 4-week cap means many small orders; "
                     "8 weeks is the middle ground.",
    }
    callout(captions[sweep], "insight")
    callout(f"<b>Fixed list vs. weekly re-planning:</b> a list set once is cheaper per unit (R$ {static.cost_per_unit_served:.2f}), "
            f"but the FC ships only <b>{static.fc_share_of_all_units_pct:.1f}%</b> of units (vs {chosen.fc_share_of_all_units_pct:.1f}%) "
            f"and holds <b>{static.weeks_of_cover:.1f} weeks</b> of ageing stock (vs {chosen.weeks_of_cover:.1f}).", "note")

    section(2, "Which products qualify?", "A very long tail: few products sell regularly")
    left, right = st.columns([2, 3], gap="large")
    with left:
        fig = go.Figure(go.Scatter(x=curve.skus, y=curve.units_covered_pct, mode="lines", fill="tozeroy",
                                   fillcolor="rgba(42,120,214,0.10)", line=dict(color=SERIES[0], width=2.5),
                                   hovertemplate="Top %{x:,} products → %{y:.1f}% of units<extra></extra>"))
        fig.update_xaxes(type="log", title_text="Number of products (log scale)")
        fig.update_yaxes(title_text="% of units covered", range=[0, 100])
        fig.update_layout(title="Products needed to cover x% of units", title_font_size=13)
        st.plotly_chart(style_fig(fig, 320), width="stretch")
    with right:
        st.markdown(f"Of **{int(seg.products_total):,} products** sold in the calibration weeks, the top 100 cover only "
                    f"**{curve.loc[curve.skus == 100, 'units_covered_pct'].iloc[0]:.0f}%** of units.")
        st.dataframe(matrix, width="stretch")
        st.caption("Number of products by ABC class (revenue, A = top 80%) × Syntetos-Boylan demand pattern. "
                   "*Intermittent* = does not sell every week.")

    section(3, "The plan: reorder points per product", "The list as it stood on the last Monday of the test")
    cats = ["All"] + sorted(prods.category.dropna().unique())
    pick = st.selectbox("Category", cats)
    view = prods if pick == "All" else prods[prods.category == pick]
    st.dataframe(
        view[["category", "price", "forecast_week", "lead_days", "safety_stock", "reorder_point", "order_qty", "fill_rate_pct"]],
        hide_index=True, width="stretch", height=360,
        column_config={
            "category": "Category", "price": st.column_config.NumberColumn("Price (R$)", format="%.0f"),
            "forecast_week": st.column_config.NumberColumn("Forecast / wk", format="%.1f"),
            "lead_days": st.column_config.NumberColumn("Lead time (d)", format="%d"),
            "safety_stock": st.column_config.NumberColumn("Safety stock", format="%.1f"),
            "reorder_point": st.column_config.NumberColumn("Reorder at", format="%d"),
            "order_qty": st.column_config.NumberColumn("Order qty", format="%d"),
            "fill_rate_pct": st.column_config.ProgressColumn("Fill rate (test)", format="%.0f%%", min_value=0, max_value=100),
        })
    st.caption("How to read a row: when stock on hand + on order falls to *Reorder at*, order *Order qty* units from the seller.")

    section(4, "Which forecast method?", "Compared at two levels: per product (drives stock) and FC total per day (drives staffing)")
    lvl = st.segmented_control("Level", ["product", "daily"], default="product",
                               format_func={"product": "Per product, per week", "daily": "FC total, per day"}.get)
    if (lvl or "product") == "product":
        order = ["naive", "ma4", "ses", "holt", "holt_damped", "croston", "tsb"]
        names = {"naive": "Naive", "ma4": "MA 4 wk", "ses": "SES", "holt": "Holt", "holt_damped": "Holt damped",
                 "croston": "Croston", "tsb": "TSB"}
        f = fc.set_index("method").loc[order]
        stock = t[t.sweep == "forecast"].set_index("forecast_method").loc[order]
        fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.07,
                            subplot_titles=["Error: WAPE (%)", "Error: scaled RMSE (%)", "Stock needed in simulation (R$k)"])
        for i, (vals, fmt) in enumerate([(f.wape_pct, "{:.0f}%"), (f.scaled_rmse_pct, "{:.0f}%"),
                                         (stock.avg_inventory_value / 1000, "{:.0f}k")], start=1):
            fig.add_bar(x=[names[m] for m in order], y=vals, row=1, col=i, showlegend=False,
                        marker_color=[SERIES[0] if m == "ses" else LIGHT_BLUE for m in order],
                        text=[fmt.format(v) for v in vals], textposition="outside",
                        hovertemplate="%{x}: %{y:.1f}<extra></extra>")
            fig.update_yaxes(range=[0, vals.max() * 1.28], row=1, col=i)
        fig.update_xaxes(tickangle=0, tickfont=dict(size=10))
        st.plotly_chart(style_fig(fig, 330).update_layout(bargap=0.3), width="stretch")
        callout("<b>The two error metrics disagree</b> (WAPE favours forecasts near zero, which flatters naive), so the method "
                "is chosen on the <b>stock outcome</b>. <b>SES</b> keeps the fill rate of the moving average "
                f"({stock.loc['ses', 'fill_rate_pct']:.1f}% vs {stock.loc['ma4', 'fill_rate_pct']:.1f}%) with ~9% less stock. "
                "Holt adds nothing (no trend), and Croston/TSB hold little stock but miss more orders. "
                "<b>Holt-Winters is not usable here:</b> it needs 2 years of history, and weeks full of zeros have no seasonal shape.",
                "insight")
    else:
        daily = load("forecast_daily_backtest", index_col=0).sort_values("wape_pct")
        series = load("forecast_daily_series", index_col=0, parse_dates=True)
        wk = load("weekday_index", index_col=0)["index"]
        best = daily.index[0]
        c1, c2 = st.columns([1, 1.5], gap="large")
        with c1:
            fig = go.Figure(go.Bar(y=daily.label[::-1], x=daily.wape_pct[::-1], orientation="h",
                                   marker_color=[SERIES[0] if m == best else LIGHT_BLUE for m in daily.index[::-1]],
                                   text=[f"{v:.1f}%" for v in daily.wape_pct[::-1]], textposition="outside",
                                   hovertemplate="%{y}: %{x:.1f}% WAPE<extra></extra>"))
            fig.update_layout(title="7-day-ahead error (WAPE %)", title_font_size=13,
                              xaxis_range=[0, daily.wape_pct.max() * 1.2])
            st.plotly_chart(style_fig(fig, 360), width="stretch")
        with c2:
            fig = go.Figure()
            fig.add_scatter(x=series.index, y=series.actual, name="Actual", line=dict(color="#898781", width=1.5))
            fig.add_scatter(x=series.index, y=series[best], name=daily.loc[best, "label"], line=dict(color=SERIES[0], width=2.5))
            fig.update_layout(title="Actual vs. forecast, test period (units per day)", title_font_size=13,
                              legend=dict(orientation="h", y=1.12, x=0))
            st.plotly_chart(style_fig(fig, 360), width="stretch")
        callout(f"The FC's daily volume has a clear weekday pattern (Mon {wk['Mon']:.2f}× average, Sat {wk['Sat']:.2f}×). "
                f"<b>{daily.loc[best, 'label']}</b> wins with <b>{daily.loc[best, 'wape_pct']:.1f}%</b> error and almost no bias, "
                f"~28% better than a 7-day moving average ({daily.loc['ma7', 'wape_pct']:.1f}%). The weekday season does the work; "
                "the trend term adds almost nothing. Use it to plan pickers and next-day vehicles.", "insight")

# ================================================================== analysis
with tab_an:
    md_file(ROOT / "inventory" / "ANALYSIS.md")

# ================================================================== method & data
with tab_m:
    section("A", "Method")
    st.markdown(
        """
- **Demand:** valid delivered items from customers in the zones served by the São Paulo FC (project 1).
  Calibration Sep 2017–Apr 2018 (34 weeks), test May–Aug 2018 (16 weeks).
- **Weekly plan (Mondays, past data only):** stock list = sold in ≥6 of the last 12 weeks; forecast = exponential
  smoothing (SES); safety stock = z × σ(weekly demand) × √(lead time / 7); reorder point = lead-time demand + safety stock;
  order quantity = min(EOQ, 8 weeks of demand).
- **Simulation:** real daily orders with 4 warm-up weeks. Unserved demand is shipped by the seller (no lost sale), and
  stock of delisted products is returned to the seller.
"""
    )
    section("B", "Assumptions")
    st.markdown(
        """
| Assumption | Value |
|---|---|
| Lead time | seller handling (data, median ≈ 2 days) + 2 days transit + 1 day receiving ≈ 6 days |
| Holding cost | 25% of product value per year |
| Replenishment order / removal order | R$ 40 each |
| Unit value | customer price |
"""
    )
    section("C", "All simulated policies")
    st.dataframe(t, hide_index=True, width="stretch")
