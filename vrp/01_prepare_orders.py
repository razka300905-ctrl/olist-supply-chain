"""Step 1 - Build the delivery-order tables (SQL) and pick the scenario days.

- Normal day: the Tue-Thu in Mar-May 2018 whose Grande-SP order count is closest to the
  median of those days (a typical, non-promotional weekday).
- Peak day: Black Friday 2017 (24 Nov), the busiest day in the dataset.
Orders bought on day D are assumed to be delivered from the FC on day D+1.
"""
from pathlib import Path
import sqlite3

import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "olist.db"
OUT = HERE / "outputs"
PEAK_DAY = "2017-11-24"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript((HERE / "sql" / "01_delivery_orders.sql").read_text(encoding="utf-8"))

    daily = pd.read_sql("SELECT * FROM vrp_daily", con)
    window = daily[daily.purchase_date.between("2018-03-01", "2018-05-31") & daily.weekday.between(2, 4)]
    median = window.orders.median()
    normal_day = window.iloc[(window.orders - median).abs().argsort().iloc[0]].purchase_date

    days = {"normal": normal_day, "black_friday": PEAK_DAY}
    for label, day in days.items():
        orders = pd.read_sql("SELECT * FROM vrp_orders WHERE purchase_date = ?", con, params=[day])
        orders.to_csv(OUT / f"orders_{label}.csv", index=False)
        print(f"{label:<13} {day}: {len(orders):>4} orders, {orders.weight_kg.sum():7.1f} kg, "
              f"{orders.volume_l.sum():8.1f} L, heaviest {orders.weight_kg.max():.1f} kg, "
              f"{orders.zip5.nunique()} distinct zips")

    daily.to_csv(OUT / "daily_orders.csv", index=False)
    pd.Series(days).to_csv(OUT / "scenario_days.csv", header=["date"], index_label="day")
    print(f"\nMedian Tue-Thu (Mar-May 2018): {median:.0f} orders/day; all-time daily max: "
          f"{daily.orders.max()} on {daily.loc[daily.orders.idxmax(), 'purchase_date']}")
    con.close()


if __name__ == "__main__":
    main()
