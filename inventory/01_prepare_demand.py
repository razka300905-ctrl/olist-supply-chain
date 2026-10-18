"""Step 1 - Demand served by the São Paulo FC, as weekly units per product.

The FC's service area comes from project 1 (3-FC network, zones assigned to the SP site).
Time windows:
  calibration  2017-09-04 .. 2018-04-29  (34 weeks) - segment products, fit forecasts and policies
  test         2018-04-30 .. 2018-08-19  (16 weeks) - backtest forecasts and simulate the policy
"""
from pathlib import Path
import sqlite3

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DB = ROOT / "olist.db"
OUT = HERE / "outputs"

CAL_START, TEST_START, TEST_END = "2017-09-04", "2018-04-30", "2018-08-19"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)

    # Which FC serves each 3-digit zone (project 1, k = 3)
    assign = pd.read_csv(ROOT / "site_selection" / "outputs" / "zone_assignment.csv", dtype={"zone": str, "fc_zone": str})
    sites = pd.read_csv(ROOT / "site_selection" / "outputs" / "selected_sites.csv", dtype={"zone": str})
    k3 = assign[assign.k == 3].merge(sites[sites.k == 3][["zone", "state"]].rename(columns={"zone": "fc_zone", "state": "fc_state"}),
                                     on="fc_zone")
    k3[["zone", "fc_zone", "fc_state"]].to_sql("fc_zone_map", con, index=False, if_exists="replace")

    con.executescript((HERE / "sql" / "01_fc_demand.sql").read_text(encoding="utf-8"))
    d = pd.read_sql("SELECT * FROM inv_demand", con, parse_dates=["order_date"])
    d = d[(d.order_date >= CAL_START) & (d.order_date <= TEST_END)]

    # Daily and weekly unit demand per product (weeks start on Monday)
    daily = d.groupby(["product_id", "order_date"]).size().rename("units").reset_index()
    daily.to_csv(OUT / "daily_demand.csv", index=False)
    d["week"] = d.order_date - pd.to_timedelta(d.order_date.dt.weekday, unit="D")
    weekly = d.groupby(["product_id", "week"]).size().rename("units").reset_index()
    weekly.to_csv(OUT / "weekly_demand.csv", index=False)

    # Product master: category, average price, size, seller (most frequent) and its handling time
    handling = pd.read_sql("SELECT * FROM inv_seller_handling", con).set_index("seller_id").avg_handling_days
    prod = (d.groupby("product_id")
              .agg(category=("category", "first"), price=("price", "mean"), weight_kg=("weight_kg", "first"),
                   volume_l=("volume_l", "first"), seller_id=("seller_id", lambda s: s.mode().iloc[0]),
                   seller_state=("seller_state", lambda s: s.mode().iloc[0]))
              .reset_index())
    prod["seller_handling_days"] = prod.seller_id.map(handling).fillna(handling.median())
    prod.to_csv(OUT / "products.csv", index=False)

    cal = d[d.order_date < TEST_START]
    print(f"SP FC demand {CAL_START}..{TEST_END}: {len(d):,} items, {d.order_id.nunique():,} orders, "
          f"{d.product_id.nunique():,} products")
    print(f"calibration: {len(cal):,} items | test: {len(d) - len(cal):,} items")
    print(f"share of national valid items served by SP FC: "
          f"{len(pd.read_sql('SELECT 1 FROM inv_demand', con)) / con.execute('SELECT COUNT(*) FROM order_items oi JOIN orders o USING(order_id) WHERE o.is_valid_delivered=1').fetchone()[0] * 100:.0f}%")
    con.close()


if __name__ == "__main__":
    main()
