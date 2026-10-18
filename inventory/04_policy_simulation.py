"""Step 4 - Reorder-point policy with weekly re-planning, simulated day by day on real demand.

Why weekly re-planning: Olist's assortment turns over fast. 52% of units sold in the test weeks
come from products with no sales in the calibration weeks, so a product list fixed once goes stale.
Every Monday the plan is rebuilt from the latest data only (no peeking at the future):
  stock list          products sold in >= 6 of the last 12 weeks
  forecast_week       next-week forecast from FORECAST_METHOD (SES; all methods in forecasting.py
                      are compared in the "forecast" sweep, so the method is chosen on the stock outcome)
  sigma_week          standard deviation of weekly demand over the last 12 weeks
  lead time L (days)  seller handling days (data) + inbound transit + receiving (assumed)
  safety stock SS     = z(service level) x sigma_week x sqrt(L / 7)
  reorder point ROP   = forecast_week x L / 7 + SS
  order quantity Q    = min(EOQ, 8 weeks of forecast), at least 1
Each day: deliveries arrive, demand is served from stock, and stocked products whose stock on hand +
on order is at or below ROP are reordered. Demand the FC cannot serve is shipped by the seller directly
(today's model), so it is an FC miss, not a lost sale. Delisted products stop being reordered and their
remaining stock is returned to the seller at the next weekly re-plan (a "removal order").
The simulation starts 4 weeks early with an empty FC (warm-up); KPIs count only the 16 test weeks.
Trade-offs: assortment depth (stock rule), service level, order size cap, forecast method, fixed vs weekly list.
"""
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from forecasting import METHODS, next_week

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TEST_START, TEST_END = pd.Timestamp("2018-04-30"), pd.Timestamp("2018-08-19")
WARMUP_START = TEST_START - pd.Timedelta(weeks=4)

# Illustrative cost and process assumptions
INBOUND_TRANSIT_DAYS = 2      # seller -> FC truck
RECEIVING_DAYS = 1            # unload, check, put away
HOLDING_RATE = 0.25           # per year, share of unit value (capital, space, insurance, obsolescence)
ORDER_COST = 40.0             # R$ per replenishment order (admin, inbound handling)
MAX_COVER_WEEKS = 8           # never order more than 8 weeks of forecast demand at once
ORDER_CAPS = [4, 8, None]     # compared: tighter cap = less stock but more orders; None = pure EOQ
RECENT_WEEKS = 12
FORECAST_METHOD = "ses"       # chosen in the forecast sweep: same fill rate as MA4 with ~9% less stock
STOCK_RULES = [3, 6, 9]       # list a product if it sold in >= this many of the last 12 weeks
CHOSEN_RULE = 6
SERVICE_LEVELS = [0.50, 0.80, 0.90, 0.95, 0.98, 0.99]
CHOSEN_LEVEL = 0.95


def plan(weekly_grid, monday, prod, z, min_weeks):
    """Stock list and policy parameters using only the weeks before `monday`."""
    full = weekly_grid.loc[:monday - pd.Timedelta(days=1)]
    hist = full.iloc[-RECENT_WEEKS:]
    listed = hist.columns[(hist > 0).sum() >= min_weeks]
    h = hist[listed]
    p = prod.loc[listed].copy()
    p["forecast_week"] = [next_week(FORECAST_METHOD, full[c].to_numpy(float)) for c in listed]
    p["sigma_week"] = h.std(ddof=1)
    p["safety_stock"] = z * p.sigma_week * np.sqrt(p.lead_days / 7)
    p["reorder_point"] = np.ceil(p.forecast_week * p.lead_days / 7 + p.safety_stock).astype(int)
    eoq = np.sqrt(2 * (p.forecast_week * 52).clip(lower=1) * ORDER_COST / (HOLDING_RATE * p.price))
    cap = MAX_COVER_WEEKS * p.forecast_week if MAX_COVER_WEEKS else eoq
    p["order_qty"] = np.maximum(1, np.ceil(np.minimum(eoq, cap))).astype(int)
    return p


def simulate(weekly_grid, daily, prod, level, min_weeks, replan_weekly=True):
    z = NormalDist().inv_cdf(level)
    days = pd.date_range(WARMUP_START, TEST_END, freq="D")
    on_hand, pipeline = {}, {}                       # product -> units ; product -> [(arrival_day, qty)]
    stats = {k: 0.0 for k in ["listed_demand", "served", "missed", "unlisted_demand", "orders",
                              "on_hand_units", "on_hand_value", "on_hand_m3", "returned_value", "returns"]}
    per_product = {}
    pol = None
    for day in days:
        counting = day >= TEST_START
        if counting and day == TEST_START:            # warm-up over: reset counters, keep the stock
            stats = {k: 0.0 for k in stats}
            per_product = {}
        if day.weekday() == 0 and (replan_weekly or pol is None):
            pol = plan(weekly_grid, day, prod, z, min_weeks)
            for pid in [p for p, u in on_hand.items() if u > 0 and p not in pol.index]:
                stats["returned_value"] += on_hand[pid] * prod.price[pid]   # removal order back to seller
                stats["returns"] += 1
                on_hand[pid] = 0
        for pid in list(pipeline):                    # receive deliveries
            arrived = sum(q for t, q in pipeline[pid] if t == day)
            pipeline[pid] = [(t, q) for t, q in pipeline[pid] if t > day]
            on_hand[pid] = on_hand.get(pid, 0) + arrived
        for pid, want in daily.get(day, {}).items():  # serve today's demand
            give = min(on_hand.get(pid, 0), want)
            on_hand[pid] = on_hand.get(pid, 0) - give
            listed = pid in pol.index
            stats["served"] += give
            if listed:
                stats["listed_demand"] += want
                stats["missed"] += want - give
            else:
                stats["unlisted_demand"] += want
                stats["listed_demand"] += give        # leftover stock of a delisted product still serves
                stats["unlisted_demand"] -= give
            pp = per_product.setdefault(pid, {"demand": 0, "served": 0})
            pp["demand"] += want
            pp["served"] += give
        for r in pol.itertuples():                    # reorder listed products
            pos = on_hand.get(r.Index, 0) + sum(q for _, q in pipeline.get(r.Index, []))
            while pos <= r.reorder_point:
                pipeline.setdefault(r.Index, []).append((day + pd.Timedelta(days=int(r.lead_days)), int(r.order_qty)))
                pos += r.order_qty
                stats["orders"] += 1
        units = pd.Series(on_hand, dtype=float)
        units = units[units > 0]
        stats["on_hand_units"] += units.sum()
        stats["on_hand_value"] += (units * prod.price.reindex(units.index)).sum()
        stats["on_hand_m3"] += (units * prod.volume_l.reindex(units.index)).sum() / 1000

    n = int((days >= TEST_START).sum())
    years = n / 365
    holding = stats["on_hand_value"] / n * HOLDING_RATE
    ordering = stats["orders"] * ORDER_COST / years
    returning = stats["returns"] * ORDER_COST / years             # a removal order costs like a replenishment
    total_units = stats["listed_demand"] + stats["unlisted_demand"]
    kpi = {
        "service_level_pct": level * 100,
        "stock_rule_min_weeks": min_weeks,
        "order_cap_weeks": MAX_COVER_WEEKS or "EOQ only",
        "forecast_method": FORECAST_METHOD,
        "planning": "weekly re-planning" if replan_weekly else "list fixed at start",
        "fill_rate_pct": stats["served"] / stats["listed_demand"] * 100,
        "fc_share_of_all_units_pct": stats["served"] / total_units * 100,
        "products_listed_last_week": len(pol),
        "avg_units_on_hand": stats["on_hand_units"] / n,
        "avg_inventory_value": stats["on_hand_value"] / n,
        "avg_space_m3": stats["on_hand_m3"] / n,
        "weeks_of_cover": (stats["on_hand_units"] / n) / (stats["served"] / (n / 7)),
        "replenishment_orders": int(stats["orders"]),
        "holding_cost_per_year": holding, "ordering_cost_per_year": ordering,
        "return_cost_per_year": returning,
        "total_cost_per_year": holding + ordering + returning,
        "cost_per_unit_served": (holding + ordering + returning) / (stats["served"] / years),
        "returned_to_seller_value": stats["returned_value"],
    }
    return kpi, pol, per_product


def main() -> None:
    weekly = pd.read_csv(OUT / "weekly_demand.csv", parse_dates=["week"])
    daily_df = pd.read_csv(OUT / "daily_demand.csv", parse_dates=["order_date"])
    prod = pd.read_csv(OUT / "products.csv").set_index("product_id")
    prod["lead_days"] = np.ceil(prod.seller_handling_days + INBOUND_TRANSIT_DAYS + RECEIVING_DAYS).astype(int)

    weeks = pd.date_range(weekly.week.min(), weekly.week.max(), freq="W-MON")
    grid = weekly.pivot_table(index="week", columns="product_id", values="units", aggfunc="sum").reindex(weeks).fillna(0)
    test = daily_df[(daily_df.order_date >= TEST_START) & (daily_df.order_date <= TEST_END)]
    daily = {d: dict(zip(g.product_id, g.units)) for d, g in test.groupby("order_date")}

    def show(tag, k):
        print(f"{tag:<16} fill {k['fill_rate_pct']:5.1f}%  FC share {k['fc_share_of_all_units_pct']:4.1f}%  "
              f"listed {k['products_listed_last_week']:4d}  stock R$ {k['avg_inventory_value']:8,.0f}  "
              f"cover {k['weeks_of_cover']:4.1f} wk  R$/unit {k['cost_per_unit_served']:5.2f}")

    rows, chosen = [], None
    for rule in STOCK_RULES:                                   # how deep into the assortment?
        kpi, pol, per_product = simulate(grid, daily, prod, CHOSEN_LEVEL, rule)
        rows.append({**kpi, "sweep": "stock_rule"})
        show(f"rule {rule}/12 @95%", kpi)
        if rule == CHOSEN_RULE:
            chosen = (pol, per_product)
    for level in SERVICE_LEVELS:                               # which service level?
        if level == CHOSEN_LEVEL:
            rows.append({**rows[STOCK_RULES.index(CHOSEN_RULE)], "sweep": "service_level"})
            continue
        kpi, _, _ = simulate(grid, daily, prod, level, CHOSEN_RULE)
        rows.append({**kpi, "sweep": "service_level"})
        show(f"CSL {level:.0%} @rule {CHOSEN_RULE}", kpi)
    global MAX_COVER_WEEKS, FORECAST_METHOD
    chosen_method = FORECAST_METHOD
    for method in METHODS:                                     # which forecast gives the best stock outcome?
        FORECAST_METHOD = method
        if method == chosen_method:
            rows.append({**rows[STOCK_RULES.index(CHOSEN_RULE)], "sweep": "forecast"})
            continue
        kpi, _, _ = simulate(grid, daily, prod, CHOSEN_LEVEL, CHOSEN_RULE)
        rows.append({**kpi, "sweep": "forecast"})
        show(f"fc {method}", kpi)
    FORECAST_METHOD = chosen_method
    chosen_cap = MAX_COVER_WEEKS
    for cap in ORDER_CAPS:                                     # how much to order at once?
        MAX_COVER_WEEKS = cap
        if cap == chosen_cap:
            rows.append({**rows[STOCK_RULES.index(CHOSEN_RULE)], "sweep": "order_cap"})
            continue
        kpi, _, _ = simulate(grid, daily, prod, CHOSEN_LEVEL, CHOSEN_RULE)
        rows.append({**kpi, "sweep": "order_cap"})
        show(f"cap {cap or 'EOQ'}", kpi)
    MAX_COVER_WEEKS = chosen_cap
    static, _, _ = simulate(grid, daily, prod, CHOSEN_LEVEL, CHOSEN_RULE, replan_weekly=False)
    rows.append({**static, "sweep": "planning"})
    show("static list", static)

    pd.DataFrame(rows).round(2).to_csv(OUT / "policy_tradeoff.csv", index=False)

    # The plan as it stands on the last Monday (what the FC would stock next week), with test performance
    pol, per_product = chosen
    perf = pd.DataFrame(per_product).T
    table = pol[["category", "price", "seller_state", "lead_days", "forecast_week", "sigma_week",
                 "safety_stock", "reorder_point", "order_qty"]].join(perf, how="left")
    table["fill_rate_pct"] = table.served / table.demand * 100
    table.rename_axis("product_id").reset_index().round(2).sort_values("forecast_week", ascending=False).to_csv(
        OUT / "policy_by_product.csv", index=False)
    pd.Series({"inbound_transit_days": INBOUND_TRANSIT_DAYS, "receiving_days": RECEIVING_DAYS,
               "holding_rate_per_year": HOLDING_RATE, "order_cost_rs": ORDER_COST, "max_cover_weeks": MAX_COVER_WEEKS,
               "stock_rule": f">= {CHOSEN_RULE} of last {RECENT_WEEKS} weeks with sales",
               "chosen_service_level": CHOSEN_LEVEL}).to_csv(OUT / "inventory_assumptions.csv", header=["value"])
    print(f"\nLead time days (median / p90): {pol.lead_days.median():.0f} / {pol.lead_days.quantile(.9):.0f}")


if __name__ == "__main__":
    main()
