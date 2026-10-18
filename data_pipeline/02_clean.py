"""Pipeline step 2 - Clean and standardize the raw layer into analysis-ready tables.

raw_* (text, as delivered)  ->  clean tables (typed, standardized, flagged)

Principles
- Never silently delete: rows are only dropped when they are exact duplicates or
  physically impossible (e.g. coordinates outside Brazil). Everything questionable is
  kept and FLAGGED so each analysis can decide.
- Every rule writes a line to reports/cleaning_log.csv (table, rule, rows affected, action).
- Validation checks at the end fail loudly if a key or format rule is broken.
"""
from pathlib import Path
import re
import sqlite3
import unicodedata

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "olist.db"
HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
CLEAN_CSV = HERE / "clean_csv"

BRAZIL_STATES = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA",
                 "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
BRAZIL_BOX = {"lat": (-34.0, 5.5), "lng": (-74.0, -34.0)}
TS_FORMAT = "%Y-%m-%d %H:%M:%S"

# Two Portuguese categories have no English translation in the source file.
EXTRA_TRANSLATIONS = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos": "portable_kitchen_and_food_preparers",
}

LOG: list[dict] = []


def log(table, rule, rows, action):
    LOG.append({"table": table, "rule": rule, "rows_affected": int(rows), "action": action})
    print(f"  [{table}] {rule}: {int(rows):,} -> {action}")


# ---------------------------------------------------------------- text helpers
def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_city(s):
    """Lowercase, no accents, official hyphens kept, state/country tails removed.
    'São Paulo / SP' -> 'sao paulo', 'Lages - SC' -> 'lages', 'Embu-Guaçu' -> 'embu-guacu',
    'novo hamburgo, rio grande do sul, brasil' -> 'novo hamburgo', '04482255' / e-mail -> None."""
    if pd.isna(s) or "@" in str(s):
        return None
    s = strip_accents(str(s).replace("´", "'").replace("`", "'")).lower().strip()
    s = re.split(r"[,\\(/]", s)[0]                 # tails after ',', '\', '(', '/'
    s = re.sub(r"\s+-\s+.*$", "", s)               # 'lages - sc'
    m = re.fullmatch(r"(.+)-([a-z]{2})", s)        # 'andira-pr' (only if the suffix is a real UF)
    if m and m.group(2).upper() in BRAZIL_STATES:
        s = m.group(1)
    s = re.sub(r"[^a-z0-9' \-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" -")
    if not s or s.isdigit() or s.upper() in BRAZIL_STATES:   # 'sp' alone is a state, not a city
        return None
    return s


def norm_zip(s):
    return None if pd.isna(s) else str(s).strip().zfill(5)


def to_ts(series):
    return pd.to_datetime(series, errors="coerce", format="mixed")


def ts_text(series):
    """Store timestamps as ISO text - SQLite has no datetime type, ISO sorts and parses correctly."""
    return series.dt.strftime(TS_FORMAT).where(series.notna(), None)


def mode_or_none(s):
    m = s.mode()
    return m.iloc[0] if len(m) else None


# ---------------------------------------------------------------- table cleaners
def clean_geolocation(raw):
    t = "geolocation"
    df = raw.copy()
    df["geolocation_zip_code_prefix"] = df.geolocation_zip_code_prefix.map(norm_zip)
    df["geolocation_lat"] = pd.to_numeric(df.geolocation_lat, errors="coerce")
    df["geolocation_lng"] = pd.to_numeric(df.geolocation_lng, errors="coerce")
    df["geolocation_city"] = df.geolocation_city.map(norm_city)
    df["geolocation_state"] = df.geolocation_state.str.strip().str.upper()

    inside = (df.geolocation_lat.between(*BRAZIL_BOX["lat"]) & df.geolocation_lng.between(*BRAZIL_BOX["lng"]))
    log(t, "coordinates outside Brazil bounding box", (~inside).sum(), "dropped")
    df = df[inside]

    dup = df.duplicated()
    log(t, "exact duplicate rows (after standardizing city names)", dup.sum(), "dropped")
    return df[~dup].reset_index(drop=True)


def build_zip_centroids(geo, customers, sellers):
    """One coordinate per 5-digit zip (median = robust to stray points).
    Zips used by customers/sellers but missing from geolocation get the 3-digit-zone centroid."""
    t = "geo_zip_centroid"
    cent = (geo.groupby("geolocation_zip_code_prefix")
               .agg(lat=("geolocation_lat", "median"), lng=("geolocation_lng", "median"),
                    city=("geolocation_city", mode_or_none), state=("geolocation_state", mode_or_none),
                    n_points=("geolocation_lat", "size"))
               .reset_index().rename(columns={"geolocation_zip_code_prefix": "zip_code_prefix"}))
    cent["source"] = "geolocation"

    used = pd.concat([
        customers[["customer_zip_code_prefix", "customer_state"]].set_axis(["zip_code_prefix", "state"], axis=1),
        sellers[["seller_zip_code_prefix", "seller_state"]].set_axis(["zip_code_prefix", "state"], axis=1),
    ]).drop_duplicates("zip_code_prefix")
    missing = used[~used.zip_code_prefix.isin(cent.zip_code_prefix)].copy()

    zone = cent.assign(zip3=cent.zip_code_prefix.str[:3]).groupby("zip3")[["lat", "lng"]].median()
    missing["zip3"] = missing.zip_code_prefix.str[:3]
    missing = missing.join(zone, on="zip3")
    filled = missing.dropna(subset=["lat"])
    log(t, "customer/seller zips missing from geolocation", len(missing),
        f"{len(filled)} imputed from 3-digit zone centroid, {len(missing) - len(filled)} left without coordinates")
    filled = filled.assign(city=None, n_points=0, source="zip3_fallback")[cent.columns]
    return pd.concat([cent, filled], ignore_index=True)


def clean_customers(raw):
    t = "customers"
    df = raw.copy()
    df["customer_zip_code_prefix"] = df.customer_zip_code_prefix.map(norm_zip)
    before = df.customer_city.copy()
    df["customer_city"] = df.customer_city.map(norm_city)
    log(t, "city names standardized (accents, case, suffixes, symbols)", (before != df.customer_city).sum(), "rewritten")
    df["customer_state"] = df.customer_state.str.strip().str.upper()
    return df


def clean_sellers(raw, geo, known_cities):
    t = "sellers"
    df = raw.copy()
    df["seller_zip_code_prefix"] = df.seller_zip_code_prefix.map(norm_zip)
    before = df.seller_city.copy()
    df["seller_city"] = df.seller_city.map(norm_city)
    log(t, "city names standardized (accents, case, '/sp' and ', brasil' tails, symbols)",
        (before.str.lower() != df.seller_city).sum(), "rewritten")

    # Sellers type their city freely ('sbc', 'sp', a zip code, an e-mail). Anything that is not a
    # known Brazilian city name is replaced with the city of the seller's zip code.
    zip_city = geo.groupby("geolocation_zip_code_prefix").geolocation_city.agg(mode_or_none)
    bad = ~df.seller_city.isin(known_cities)
    examples = ", ".join(sorted(set(before[bad].astype(str)))[:6])
    df.loc[bad, "seller_city"] = df.loc[bad, "seller_zip_code_prefix"].map(zip_city)
    log(t, f"city not a known city name (e.g. {examples})", bad.sum(), "replaced with city of the zip code")
    df["seller_state"] = df.seller_state.str.strip().str.upper()
    return df


def clean_orders(raw, items):
    t = "orders"
    df = raw.copy()
    ts_cols = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"]
    ts = {c: to_ts(df[c]) for c in ts_cols}
    df["order_status"] = df.order_status.str.strip().str.lower()

    delivered = df.order_status.eq("delivered")
    df["flag_missing_delivery_date"] = (delivered & ts["order_delivered_customer_date"].isna()).astype(int)
    df["flag_carrier_before_purchase"] = (ts["order_delivered_carrier_date"] < ts["order_purchase_timestamp"]).astype(int)
    df["flag_delivered_before_carrier"] = (ts["order_delivered_customer_date"] < ts["order_delivered_carrier_date"]).astype(int)
    df["has_items"] = df.order_id.isin(items.order_id).astype(int)
    log(t, "status 'delivered' but no delivery date", df.flag_missing_delivery_date.sum(), "flagged")
    log(t, "handed to carrier before purchase timestamp", df.flag_carrier_before_purchase.sum(), "flagged")
    log(t, "delivered to customer before carrier pickup", df.flag_delivered_before_carrier.sum(), "flagged")
    log(t, "orders with no order_items rows", (df.has_items == 0).sum(), "flagged")

    df["delivery_days"] = (ts["order_delivered_customer_date"] - ts["order_purchase_timestamp"]).dt.total_seconds() / 86400
    df["estimated_days"] = (ts["order_estimated_delivery_date"] - ts["order_purchase_timestamp"]).dt.total_seconds() / 86400
    df["is_late"] = (ts["order_delivered_customer_date"] > ts["order_estimated_delivery_date"]).astype(int)
    df.loc[ts["order_delivered_customer_date"].isna(), "is_late"] = None

    # One convenience flag that every logistics analysis can filter on
    df["is_valid_delivered"] = (delivered & ts["order_delivered_customer_date"].notna() & df.has_items.eq(1)
                                & df.flag_delivered_before_carrier.eq(0)).astype(int)
    log(t, "valid delivered orders (delivered + date + items + consistent dates)", df.is_valid_delivered.sum(), "is_valid_delivered = 1")
    for c in ts_cols:
        df[c] = ts_text(ts[c])
    return df


def clean_order_items(raw):
    t = "order_items"
    df = raw.copy()
    df["order_item_id"] = df.order_item_id.astype(int)
    df["price"] = pd.to_numeric(df.price)
    df["freight_value"] = pd.to_numeric(df.freight_value)
    df["shipping_limit_date"] = ts_text(to_ts(df.shipping_limit_date))
    log(t, "freight_value = 0 (free shipping)", (df.freight_value == 0).sum(), "kept (legitimate)")
    log(t, "price <= 0 or freight < 0", ((df.price <= 0) | (df.freight_value < 0)).sum(), "none found")
    return df


def clean_order_payments(raw):
    t = "order_payments"
    df = raw.copy()
    df["payment_sequential"] = df.payment_sequential.astype(int)
    df["payment_installments"] = df.payment_installments.astype(int)
    df["payment_value"] = pd.to_numeric(df.payment_value)
    df["payment_type"] = df.payment_type.str.strip().str.lower()
    zero = df.payment_installments == 0
    df.loc[zero, "payment_installments"] = 1
    log(t, "payment_installments = 0", zero.sum(), "set to 1 (a payment has at least one installment)")
    log(t, "payment_type = 'not_defined'", (df.payment_type == "not_defined").sum(), "kept, value is 0")
    return df


def clean_order_reviews(raw):
    t = "order_reviews"
    df = raw.copy()
    df["review_score"] = df.review_score.astype(int)
    df["has_comment"] = df.review_comment_message.notna().astype(int)
    log(t, "free-text columns review_comment_title (88% empty) / review_comment_message (59% empty)", 2,
        "dropped columns (not used in supply-chain analyses); kept has_comment flag")
    df = df.drop(columns=["review_comment_title", "review_comment_message"])
    for c in ["review_creation_date", "review_answer_timestamp"]:
        df[c] = ts_text(to_ts(df[c]))
    dup = df.duplicated(["review_id", "order_id"])
    log(t, "duplicate (review_id, order_id) pairs", dup.sum(), "dropped")
    df = df[~dup]
    log(t, "orders with more than one review", df.order_id.duplicated().sum(), "kept (customer re-reviewed)")
    return df


def clean_products(raw, translation):
    t = "products"
    df = raw.rename(columns={"product_name_lenght": "product_name_length",
                             "product_description_lenght": "product_description_length"})
    log(t, "column-name typos ('lenght')", 2, "renamed to '_length'")
    num = ["product_name_length", "product_description_length", "product_photos_qty",
           "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    df[num] = df[num].apply(pd.to_numeric, errors="coerce")

    missing_cat = df.product_category_name.isna()
    df["product_category_name"] = df.product_category_name.fillna("unknown")
    log(t, "missing product category", missing_cat.sum(), "set to 'unknown'")
    df["product_category_name_english"] = df.product_category_name.map(translation).fillna(df.product_category_name)

    # Physical attributes are needed for freight and capacity; 0 or missing is not a real weight/size
    dims = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    bad = df[dims].isna().any(axis=1) | (df[dims] <= 0).any(axis=1)
    for c in dims:
        df.loc[df[c] <= 0, c] = np.nan
        df[c] = df[c].fillna(df.groupby("product_category_name")[c].transform("median")).fillna(df[c].median())
    df["flag_dims_imputed"] = bad.astype(int)
    log(t, "weight/dimensions missing or 0", bad.sum(), "imputed with category median, flagged")
    df["product_volume_cm3"] = df.product_length_cm * df.product_height_cm * df.product_width_cm
    return df


# ---------------------------------------------------------------- validation
def validate(tables, cent):
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok))
        log("validation", name, 0 if ok else 1, ("PASS " if ok else "FAIL ") + detail)

    pk = {"customers": ["customer_id"], "sellers": ["seller_id"], "orders": ["order_id"],
          "products": ["product_id"], "order_items": ["order_id", "order_item_id"],
          "order_payments": ["order_id", "payment_sequential"], "order_reviews": ["review_id", "order_id"]}
    for t, cols in pk.items():
        check(f"primary key unique: {t}({', '.join(cols)})", not tables[t].duplicated(cols).any())

    zip_ok = all(tables[t][c].str.fullmatch(r"\d{5}").all() for t, c in
                 [("customers", "customer_zip_code_prefix"), ("sellers", "seller_zip_code_prefix")])
    check("zip codes are 5-digit text", zip_ok)
    check("states are valid Brazilian UFs",
          set(tables["customers"].customer_state) | set(tables["sellers"].seller_state) <= BRAZIL_STATES)
    check("no missing city names", tables["customers"].customer_city.notna().all() and tables["sellers"].seller_city.notna().all())

    fk = [("order_items", "order_id", "orders", "order_id"), ("order_items", "product_id", "products", "product_id"),
          ("order_items", "seller_id", "sellers", "seller_id"), ("orders", "customer_id", "customers", "customer_id"),
          ("order_payments", "order_id", "orders", "order_id"), ("order_reviews", "order_id", "orders", "order_id")]
    for child, ck, parent, pkc in fk:
        check(f"foreign key: {child}.{ck} -> {parent}", tables[child][ck].isin(tables[parent][pkc]).all())

    zips = set(cent.zip_code_prefix)
    cov = tables["customers"].customer_zip_code_prefix.isin(zips).mean() * 100
    check("customer zips with coordinates >= 99.5%", cov >= 99.5, f"({cov:.2f}%)")
    failed = [n for n, ok in checks if not ok]
    if failed:
        raise SystemExit(f"Validation failed: {failed}")


# ---------------------------------------------------------------- main
def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    CLEAN_CSV.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)
    raw = lambda name: pd.read_sql(f"SELECT * FROM raw_{name}", con)

    tr = raw("category_translation")
    translation = {**dict(zip(tr.product_category_name, tr.product_category_name_english)), **EXTRA_TRANSLATIONS}
    log("category_translation", "categories missing an English name", len(EXTRA_TRANSLATIONS), "added manually")

    geo = clean_geolocation(raw("geolocation"))
    items = clean_order_items(raw("order_items"))
    customers = clean_customers(raw("customers"))
    known_cities = set(customers.customer_city.dropna()) | set(geo.geolocation_city.dropna())
    tables = {
        "customers": customers,
        "sellers": clean_sellers(raw("sellers"), geo, known_cities),
        "orders": clean_orders(raw("orders"), items),
        "order_items": items,
        "order_payments": clean_order_payments(raw("order_payments")),
        "order_reviews": clean_order_reviews(raw("order_reviews")),
        "products": clean_products(raw("products"), translation),
        "category_translation": pd.DataFrame(translation.items(),
                                             columns=["product_category_name", "product_category_name_english"]),
    }
    cent = build_zip_centroids(geo, tables["customers"], tables["sellers"])
    validate(tables, cent)

    # Write clean layer: SQLite tables (no prefix) + CSV copies
    tables["geolocation"] = geo
    tables["geo_zip_centroid"] = cent
    summary = []
    for name, df in tables.items():
        df.to_sql(name, con, index=False, if_exists="replace")
        if name != "geolocation":  # 700k rows; the centroid table is what analyses use
            df.to_csv(CLEAN_CSV / f"{name}.csv", index=False)
        raw_rows = con.execute(f"SELECT COUNT(*) FROM raw_{name}").fetchone()[0] if name != "geo_zip_centroid" else "-"
        summary.append({"table": name, "raw_rows": raw_rows, "clean_rows": len(df), "columns": df.shape[1]})

    for stmt in [
        "CREATE INDEX ix_orders_customer ON orders(customer_id)",
        "CREATE INDEX ix_items_order ON order_items(order_id)",
        "CREATE INDEX ix_items_product ON order_items(product_id)",
        "CREATE INDEX ix_customers_id ON customers(customer_id)",
        "CREATE INDEX ix_products_id ON products(product_id)",
        "CREATE INDEX ix_sellers_id ON sellers(seller_id)",
        "CREATE INDEX ix_centroid_zip ON geo_zip_centroid(zip_code_prefix)",
    ]:
        con.execute(stmt)
    con.commit()
    con.close()

    pd.DataFrame(LOG).to_csv(REPORTS / "cleaning_log.csv", index=False)
    summary = pd.DataFrame(summary)
    summary.to_csv(REPORTS / "row_counts.csv", index=False)
    print("\n" + summary.to_string(index=False))
    print(f"\nClean layer written to {DB} and {CLEAN_CSV}; log in {REPORTS}")


if __name__ == "__main__":
    main()
