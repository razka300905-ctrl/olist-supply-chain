"""Pipeline step 1 - Load the raw Olist CSVs into SQLite, untouched.

Every column is stored as TEXT exactly as it appears in the CSV (tables prefixed raw_),
so the raw layer is a faithful copy and all typing/cleaning happens in 02_clean.py.
The CSVs in ../archive are the single source of truth; olist.db can be deleted at any time.
"""
from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "archive"
DB = ROOT / "olist.db"

TABLES = {
    "raw_customers": "olist_customers_dataset.csv",
    "raw_geolocation": "olist_geolocation_dataset.csv",
    "raw_order_items": "olist_order_items_dataset.csv",
    "raw_order_payments": "olist_order_payments_dataset.csv",
    "raw_order_reviews": "olist_order_reviews_dataset.csv",
    "raw_orders": "olist_orders_dataset.csv",
    "raw_products": "olist_products_dataset.csv",
    "raw_sellers": "olist_sellers_dataset.csv",
    "raw_category_translation": "product_category_name_translation.csv",
}


def main() -> None:
    DB.unlink(missing_ok=True)
    con = sqlite3.connect(DB)
    print(f"{'table':<26}{'rows':>10}{'cols':>6}  columns with nulls")
    for table, file in TABLES.items():
        df = pd.read_csv(RAW / file, dtype=str, keep_default_na=False, na_values=[""], encoding="utf-8-sig")
        df.to_sql(table, con, index=False)
        nulls = {c: int(n) for c, n in df.isna().sum().items() if n}
        print(f"{table:<26}{len(df):>10,}{df.shape[1]:>6}  {nulls or '-'}")
    con.commit()
    con.close()
    print(f"\nRaw layer written to {DB}")


if __name__ == "__main__":
    main()
