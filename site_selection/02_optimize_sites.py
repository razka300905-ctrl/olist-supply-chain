"""Step 2 - Choose fulfilment-centre (FC) locations with a p-median model, for k = 1..6.

p-median: open exactly k sites and assign every demand zone to one open site so that the
order-weighted road distance is minimal. Solved exactly with HiGHS via PuLP.

Distances are converted into business KPIs using two regressions fitted on the
as-is data (seller -> customer shipments):
    delivery_days ~ road_km
    freight_value ~ road_km + weight_kg
"""
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import pulp

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "olist.db"
OUT = HERE / "outputs"

K_VALUES = range(1, 7)
ROAD_FACTOR = 1.3          # straight-line -> road distance (common rule of thumb)
SERVICE_KM = (300, 800)    # ~next-day and ~2-day ground reach


def road_km(lat1, lng1, lat2, lng2):
    """Haversine distance x road factor. Works on scalars or broadcast arrays."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a)) * ROAD_FACTOR


def ols(X, y):
    """Least squares with intercept; returns coefficients and R^2."""
    X = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    r2 = 1 - ((y - X @ beta) ** 2).sum() / ((y - y.mean()) ** 2).sum()
    return beta, r2


def fit_asis(con):
    s = pd.read_sql("SELECT * FROM asis_shipments", con)
    s["km"] = road_km(s.sell_lat, s.sell_lng, s.cust_lat, s.cust_lng)
    s = s[s.delivery_days.between(0, 60)]  # drop a handful of extreme outliers

    days_beta, days_r2 = ols(s[["km"]].to_numpy(), s.delivery_days.to_numpy())
    freight_beta, freight_r2 = ols(s[["km", "weight_kg"]].to_numpy(), s.freight_value.to_numpy())

    asis = {
        "scenario": "As-is (seller ships direct)",
        "k": 0,
        "avg_km": s.km.mean(),
        "pct_within_300km": (s.km <= SERVICE_KM[0]).mean() * 100,
        "pct_within_800km": (s.km <= SERVICE_KM[1]).mean() * 100,
        "est_delivery_days": s.delivery_days.mean(),
        "est_freight_per_item": s.freight_value.mean(),
        "est_freight_total": s.freight_value.sum(),
    }
    models = {
        "days_intercept": days_beta[0], "days_per_100km": days_beta[1] * 100, "days_r2": days_r2,
        "freight_intercept": freight_beta[0], "freight_per_100km": freight_beta[1] * 100,
        "freight_per_kg": freight_beta[2], "freight_r2": freight_r2, "n_shipments": len(s),
    }
    return asis, models, days_beta, freight_beta


def zone_names(con):
    """Most common customer city per 3-digit zone, for readable site labels."""
    return pd.read_sql("""
        WITH c AS (
            SELECT SUBSTR(customer_zip_code_prefix, 1, 3) AS zone, customer_city AS city,
                   customer_state AS state, COUNT(*) AS n
            FROM customers GROUP BY 1, 2, 3
        )
        SELECT zone, city, state FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY zone ORDER BY n DESC) AS r FROM c
        ) WHERE r = 1
    """, con).set_index("zone")


def solve_p_median(dist, w, k):
    n, m = dist.shape
    prob = pulp.LpProblem("p_median", pulp.LpMinimize)
    y = [pulp.LpVariable(f"y{j}", cat="Binary") for j in range(m)]
    x = [[pulp.LpVariable(f"x{i}_{j}", lowBound=0) for j in range(m)] for i in range(n)]
    prob += pulp.lpSum(w[i] * dist[i, j] * x[i][j] for i in range(n) for j in range(m))
    prob += pulp.lpSum(y) == k
    for i in range(n):
        prob += pulp.lpSum(x[i]) == 1
        for j in range(m):
            prob += x[i][j] <= y[j]
    prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal", pulp.LpStatus[prob.status]
    return [j for j in range(m) if y[j].value() > 0.5]


# Practical 3-FC networks built from large metro areas, compared against the optimum.
PRACTICAL_VARIANTS = {
    "Optimal (model)": None,
    "SP + Rio + Salvador": [("sao paulo", "SP"), ("rio de janeiro", "RJ"), ("salvador", "BA")],
    "SP + Belo Horizonte + Recife": [("sao paulo", "SP"), ("belo horizonte", "MG"), ("recife", "PE")],
    "SP + Rio + Recife": [("sao paulo", "SP"), ("rio de janeiro", "RJ"), ("recife", "PE")],
}


def evaluate_variants(dist, w, cands, names, optimal_idx):
    """Order-weighted KPIs for hand-picked site sets (largest-demand zone of each city)."""
    c = cands.assign(city=cands.zone.map(names.city))
    rows = []
    for label, cities in PRACTICAL_VARIANTS.items():
        if cities is None:
            idx = optimal_idx
        else:
            idx = [c[(c.city == city) & (c.state == st)].orders.idxmax() for city, st in cities]
        km = dist[:, idx].min(axis=1)
        rows.append({
            "variant": label,
            "sites": ", ".join(f"{c.city[j].title()}-{c.state[j]}" for j in idx),
            "avg_km": np.average(km, weights=w),
            "pct_within_300km": w[km <= SERVICE_KM[0]].sum() / w.sum() * 100,
            "pct_within_800km": w[km <= SERVICE_KM[1]].sum() / w.sum() * 100,
        })
    df = pd.DataFrame(rows)
    df["extra_km_vs_optimal_pct"] = (df.avg_km / df.avg_km.iloc[0] - 1) * 100
    return df


def main() -> None:
    con = sqlite3.connect(DB)
    demand = pd.read_sql("SELECT * FROM demand_zone", con)
    cands = pd.read_sql("SELECT * FROM candidate_site", con).reset_index(drop=True)
    names = zone_names(con)

    asis, models, days_beta, freight_beta = fit_asis(con)
    print("As-is regressions:", {k: round(v, 3) for k, v in models.items()})

    dist = road_km(demand.lat.to_numpy()[:, None], demand.lng.to_numpy()[:, None],
                   cands.lat.to_numpy()[None, :], cands.lng.to_numpy()[None, :])
    w = demand.orders.to_numpy()
    kg_per_item = (demand.weight_kg / demand["items"]).to_numpy()

    rows, sites, assign = [asis], [], []
    for k in K_VALUES:
        open_idx = solve_p_median(dist, w, k)
        if k == 3:
            variants = evaluate_variants(dist, w, cands, names, open_idx)
        sub = dist[:, open_idx]
        best = sub.argmin(axis=1)
        km = sub[np.arange(len(demand)), best]

        days = days_beta[0] + days_beta[1] * km
        freight = freight_beta[0] + freight_beta[1] * km + freight_beta[2] * kg_per_item
        rows.append({
            "scenario": f"{k} FC" + ("s" if k > 1 else ""),
            "k": k,
            "avg_km": np.average(km, weights=w),
            "pct_within_300km": w[km <= SERVICE_KM[0]].sum() / w.sum() * 100,
            "pct_within_800km": w[km <= SERVICE_KM[1]].sum() / w.sum() * 100,
            "est_delivery_days": np.average(days, weights=w),
            "est_freight_per_item": np.average(freight, weights=demand["items"]),
            "est_freight_total": (freight * demand["items"]).sum(),
        })

        for rank, j in enumerate(open_idx):
            c = cands.loc[j]
            served = best == rank
            sites.append({
                "k": k, "zone": c.zone, "city": names.city.get(c.zone, ""), "state": c.state,
                "lat": c.lat, "lng": c.lng,
                "orders_served": int(w[served].sum()),
                "share_pct": w[served].sum() / w.sum() * 100,
                "avg_km_served": np.average(km[served], weights=w[served]),
            })
        assign.append(pd.DataFrame({
            "k": k, "zone": demand.zone, "state": demand.state, "orders": w,
            "lat": demand.lat, "lng": demand.lng,
            "fc_zone": cands.zone.to_numpy()[np.array(open_idx)[best]], "road_km": km,
        }))
        print(f"k={k}: " + ", ".join(f"{s['city'].title()}-{s['state']}" for s in sites[-k:]))

    summary = pd.DataFrame(rows)
    # Marginal value of the k-th FC: freight saved vs. k-1 sites, annualised.
    # Delivered orders cover ~23 months; scale totals to 12 months.
    months = pd.read_sql("""SELECT (julianday(MAX(order_purchase_timestamp)) - julianday(MIN(order_purchase_timestamp))) / 30.44
                            FROM fact_delivered_items""", con).iloc[0, 0]
    summary["est_freight_per_year"] = summary.est_freight_total * 12 / months
    summary["marginal_freight_saving_per_year"] = -summary.est_freight_per_year.diff()
    summary.loc[summary.k <= 1, "marginal_freight_saving_per_year"] = np.nan

    summary.round(2).to_csv(OUT / "scenario_summary.csv", index=False)
    pd.DataFrame(sites).round(3).to_csv(OUT / "selected_sites.csv", index=False)
    pd.concat(assign).round(2).to_csv(OUT / "zone_assignment.csv", index=False)
    pd.Series(models).round(4).to_csv(OUT / "asis_regressions.csv", header=["value"])
    variants.round(2).to_csv(OUT / "practical_variants_k3.csv", index=False)
    con.close()

    print("\n" + summary.drop(columns=["est_freight_total"]).round(1).to_string(index=False))
    print("\n3-FC practical variants\n" + variants.round(1).to_string(index=False))


if __name__ == "__main__":
    main()
