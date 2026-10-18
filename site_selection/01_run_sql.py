"""Step 1 - Run the SQL demand model and export the resulting tables as CSV."""
from pathlib import Path
import sqlite3

import pandas as pd

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "olist.db"
OUT = HERE / "outputs"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript((HERE / "sql" / "01_demand_model.sql").read_text(encoding="utf-8"))

    for table in ["demand_zone", "supply_zone", "candidate_site"]:
        df = pd.read_sql(f"SELECT * FROM {table}", con)
        df.to_csv(OUT / f"{table}.csv", index=False)
        print(f"{table:<16}{len(df):>6} rows")

    print("\nDemand coverage")
    print(pd.read_sql("""
        SELECT (SELECT COUNT(DISTINCT order_id) FROM fact_delivered_items) AS delivered_orders,
               (SELECT SUM(orders) FROM demand_zone)                      AS orders_in_zones,
               (SELECT COUNT(*) FROM asis_shipments)                      AS geocoded_items
    """, con).to_string(index=False))

    print("\nTop 10 states by orders")
    print(pd.read_sql("""
        SELECT state, SUM(orders) AS orders,
               ROUND(100.0 * SUM(orders) / (SELECT SUM(orders) FROM demand_zone), 1) AS pct
        FROM demand_zone GROUP BY state ORDER BY orders DESC LIMIT 10
    """, con).to_string(index=False))

    print("\nTop 5 seller states by items shipped")
    print(pd.read_sql("""
        SELECT state, SUM(items) AS items,
               ROUND(100.0 * SUM(items) / (SELECT SUM(items) FROM supply_zone), 1) AS pct
        FROM supply_zone GROUP BY state ORDER BY items DESC LIMIT 5
    """, con).to_string(index=False))
    con.close()


if __name__ == "__main__":
    main()
