"""Project 3 - Inventory: what the São Paulo FC should stock, how much, and when to reorder."""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from app_common import ROOT, SERIES, setup_page

setup_page("Inventory", "📦")

INV_OUT = ROOT / "inventory" / "outputs"
LIGHT = "#b7d3f6"


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

st.title("3 · What should the São Paulo FC stock, and how much?")
st.markdown(
    "The FC from project 1 serves ~62% of Olist's orders, but Olist is a marketplace: about **19,000 different "
    "products** reached this area in one year, and most sell only once or twice. This project decides **which "
    "products to hold, how much of each, and when to reorder**. It then tests the policy day by day on 16 weeks of "
    "real orders it never saw."
)
st.success(
    f"**Recommendation: stock only the ~{int(chosen.products_listed_last_week)} most regular products (sold in ≥6 of "
    f"the last 12 weeks), re-plan every Monday, and target 95%.** The FC ships **{chosen.fc_share_of_all_units_pct:.0f}% "
    f"of São Paulo units** with **R$ {chosen.avg_inventory_value / 1000:.0f}k** of stock at **R$ "
    f"{chosen.cost_per_unit_served:.2f}** inventory cost per unit. Everything else stays seller-shipped, as today."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Products in the FC", f"{int(chosen.products_listed_last_week)}", f"of ~19,000 sold in the area", delta_color="off")
c2.metric("Share of units from the FC", f"{chosen.fc_share_of_all_units_pct:.1f}%")
c3.metric("Fill rate (stocked products)", f"{chosen.fill_rate_pct:.1f}%",
          help="Units served from FC stock ÷ units demanded for listed products. Misses are shipped by the seller.")
c4.metric("Average stock", f"R$ {chosen.avg_inventory_value / 1000:.0f}k",
          f"{chosen.weeks_of_cover:.1f} weeks of cover · {chosen.avg_space_m3:.0f} m³", delta_color="off")

st.info("**Key finding:** 52% of units sold in the test weeks came from products with **no sales at all** in the "
        "previous 34 weeks. The volume is stable, but the products keep changing, so a list fixed once goes stale "
        "within weeks. That is why the plan is rebuilt every Monday.")

st.divider()

# ------------------------------------------------------------------ trade-off explorer
st.subheader("Explore the trade-offs")
SWEEPS = {
    "stock_rule": ("How many products?", "stock_rule_min_weeks", lambda v: f"≥{int(v)} of 12 weeks"),
    "service_level": ("Which service level?", "service_level_pct", lambda v: f"{v:.0f}%"),
    "order_cap": ("How much to order at once?", "order_cap_weeks", lambda v: f"cap {v} wk" if str(v).isdigit() else "pure EOQ"),
}
sweep = st.segmented_control("Decision", list(SWEEPS), default="stock_rule", format_func=lambda k: SWEEPS[k][0])
sweep = sweep or "stock_rule"
title, col, fmt = SWEEPS[sweep]
s = t[t.sweep == sweep].copy()
if sweep == "stock_rule":
    s = s.sort_values(col)
elif sweep == "service_level":
    s = s.sort_values(col)
else:
    s["_o"] = s[col].map(lambda v: int(v) if str(v).isdigit() else 999)
    s = s.sort_values("_o")
labels = [fmt(v) for v in s[col]]
is_chosen = [(r.stock_rule_min_weeks == 6 and r.service_level_pct == 95 and str(r.order_cap_weeks) == "8") for r in s.itertuples()]

fig = make_subplots(rows=1, cols=4, subplot_titles=["Share of units from FC (%)", "Fill rate (%)",
                                                    "Inventory cost per unit (R$)", "Weeks of cover"],
                    horizontal_spacing=0.06)
for i, (c, f) in enumerate([("fc_share_of_all_units_pct", "{:.1f}%"), ("fill_rate_pct", "{:.1f}%"),
                            ("cost_per_unit_served", "R$ {:.2f}"), ("weeks_of_cover", "{:.1f}")], start=1):
    fig.add_bar(x=labels, y=s[c], row=1, col=i, showlegend=False,
                marker_color=[SERIES[0] if ch else LIGHT for ch in is_chosen],
                text=[f.format(v) for v in s[c]], textposition="outside",
                hovertemplate="%{x}: " + f.replace("{:", "%{y:").replace("}", "}") + "<extra></extra>")
    fig.update_yaxes(range=[0, s[c].max() * 1.25], row=1, col=i)
fig.update_layout(height=330, margin=dict(l=0, r=0, t=40, b=0), bargap=0.3)
st.plotly_chart(fig, width="stretch")
captions = {
    "stock_rule": "Going deeper into the range doubles the FC's share but almost doubles the cost of every unit. "
                  "≥6 of 12 weeks is the balance.",
    "service_level": "Raising the target from 50% to 95% adds ~3 points of fill rate. Above 95% stock grows but fill "
                     "rate does not, because misses come mostly from newly listed products that are still waiting "
                     "for their first delivery.",
    "order_cap": "Pure EOQ is cheapest on paper but holds 16 weeks of stock. A 4-week cap means many small orders. "
                 "8 weeks is the middle ground.",
}
st.caption("Dark bar = recommended policy. " + captions[sweep])
static = t[t.sweep == "planning"].iloc[0]
st.markdown(
    f"**Fixed list vs. weekly re-planning:** a list set once is cheaper per unit (R$ {static.cost_per_unit_served:.2f}), "
    f"but the FC ships only **{static.fc_share_of_all_units_pct:.1f}%** of units (vs {chosen.fc_share_of_all_units_pct:.1f}%) "
    f"and holds **{static.weeks_of_cover:.1f} weeks** of ageing stock (vs {chosen.weeks_of_cover:.1f})."
)

st.divider()

# ------------------------------------------------------------------ which products + the plan
left, right = st.columns([2, 3], gap="large")
with left:
    st.subheader("Which products qualify?")
    st.caption("Products ranked by units sold: how many are needed to cover x% of the FC area's units "
               "(34 calibration weeks)")
    fig = go.Figure(go.Scatter(x=curve.skus, y=curve.units_covered_pct, mode="lines",
                               line=dict(color=SERIES[0], width=2.5),
                               hovertemplate="Top %{x:,} products → %{y:.1f}% of units<extra></extra>"))
    fig.update_xaxes(type="log", title_text="Number of products (log scale)")
    fig.update_yaxes(title_text="% of units covered", range=[0, 100])
    fig.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.markdown(
        f"Of **{int(seg.products_total):,} products** sold in the calibration weeks, the top 100 cover only about "
        f"**{curve.loc[curve.skus == 100, 'units_covered_pct'].iloc[0]:.0f}%** of units. This is a very long tail."
    )
    with st.expander("ABC × demand pattern (number of products)"):
        st.dataframe(matrix, width="stretch")
        st.caption("ABC by revenue (A = top 80%). The demand pattern follows Syntetos-Boylan: *intermittent* means "
                   "the product does not sell every week.")

with right:
    st.subheader("The plan: reorder points per product")
    cats = ["All"] + sorted(prods.category.dropna().unique())
    pick = st.selectbox("Category", cats)
    view = prods if pick == "All" else prods[prods.category == pick]
    st.dataframe(
        view[["category", "price", "forecast_week", "lead_days", "safety_stock", "reorder_point", "order_qty", "fill_rate_pct"]],
        hide_index=True, width="stretch", height=380,
        column_config={
            "category": "Category",
            "price": st.column_config.NumberColumn("Price (R$)", format="%.0f"),
            "forecast_week": st.column_config.NumberColumn("Forecast / wk", format="%.1f"),
            "lead_days": st.column_config.NumberColumn("Lead time (d)", format="%d"),
            "safety_stock": st.column_config.NumberColumn("Safety stock", format="%.1f"),
            "reorder_point": st.column_config.NumberColumn("Reorder at", format="%d"),
            "order_qty": st.column_config.NumberColumn("Order qty", format="%d"),
            "fill_rate_pct": st.column_config.ProgressColumn("Fill rate (test)", format="%.0f%%", min_value=0, max_value=100),
        },
    )
    st.caption("The list as it stood on the last Monday. Reading a row: when stock on hand plus stock on order falls to "
               "*Reorder at*, order *Order qty* units from the seller.")

st.divider()

# ------------------------------------------------------------------ forecast backtest
st.subheader("Which forecast method?")
f = fc.set_index("method").loc[["naive", "ma4", "ses", "croston"]]
names = {"naive": "Naive", "ma4": "Moving avg (4 wk)", "ses": "Exp. smoothing", "croston": "Croston (SBA)"}
fig = make_subplots(rows=1, cols=2, subplot_titles=["Error (WAPE %, lower is better)", "Bias (%, positive = too high)"])
for i, c in enumerate(["wape_pct", "bias_pct"], start=1):
    fig.add_bar(x=[names[m] for m in f.index], y=f[c], row=1, col=i, showlegend=False,
                marker_color=[SERIES[0] if m == "ma4" else LIGHT for m in f.index],
                text=[f"{v:.0f}%" for v in f[c]], textposition="outside",
                hovertemplate="%{x}: %{y:.1f}%<extra></extra>")
    fig.update_yaxes(range=[0, f[c].max() * 1.25], row=1, col=i)
fig.update_layout(height=300, margin=dict(l=0, r=0, t=40, b=0), bargap=0.35)
st.plotly_chart(fig, width="stretch")
st.caption("16 unseen weeks, stocked products. Weekly demand per product is very noisy (all errors are above 100%), "
           "which is exactly why safety stock is needed. The 4-week moving average (dark bar) is used: it is nearly as "
           "accurate as naive but steadier, while smoothing and Croston forecast too high because products fade after their peak.")

st.divider()
st.markdown((ROOT / "inventory" / "ANALYSIS.md").read_text(encoding="utf-8"))
st.divider()

with st.expander("All simulated policies (data table)"):
    st.dataframe(t, hide_index=True, width="stretch")

with st.expander("Method & assumptions"):
    st.markdown(
        """
- **Demand:** valid delivered order items from customers in the zones served by the São Paulo FC (project 1, 3-FC network).
  Calibration Sep 2017–Apr 2018 (34 weeks), test May–Aug 2018 (16 weeks).
- **Weekly plan (Mondays, past data only):** stock list = sold in ≥6 of the last 12 weeks; forecast = 4-week moving
  average; safety stock = z × σ(weekly demand, 12 weeks) × √(lead time / 7); reorder point = lead-time demand + safety
  stock; order quantity = min(EOQ, 8 weeks of demand).
- **Lead time:** each seller's handling time from the data (median ≈ 2 days) + 2 days transit + 1 day receiving (≈ 6 days).
- **Simulation:** real daily orders with 4 warm-up weeks. Unserved demand is shipped by the seller (no lost sale), and
  stock of delisted products is returned to the seller.
- **Costs (assumptions):** holding 25% of value per year; R$ 40 per replenishment order and per removal order.
  The customer price is used as unit value.
"""
    )
