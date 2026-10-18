"""Step 2 - Which products should the São Paulo FC stock?  ABC x demand-pattern segmentation.

ABC (revenue, calibration window):  A = first 80% of revenue, B = next 15%, C = last 5%.
Demand pattern (Syntetos-Boylan), from weekly units in the calibration window:
    ADI  = average number of weeks between weeks with sales
    CV2  = squared coefficient of variation of the non-zero weekly quantities
    smooth (ADI < 1.32, CV2 < 0.49) | erratic (ADI < 1.32, CV2 >= 0.49)
    intermittent (ADI >= 1.32, CV2 < 0.49) | lumpy (ADI >= 1.32, CV2 >= 0.49)
Stocking rule: stock a product in the FC if it sold in at least 6 of the LAST 12 calibration weeks
(recent and regular demand). Popularity over the whole window is not enough: products past their peak
would sit in the FC. Everything else stays seller-fulfilled, the marketplace's normal model.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TEST_START = pd.Timestamp("2018-04-30")
RECENT_WEEKS = 12            # look-back for the stocking rule
MIN_RECENT_WEEKS_WITH_SALES = 6   # same rule as the chosen policy in 04 (6 of the last 12 weeks)


def main() -> None:
    weekly = pd.read_csv(OUT / "weekly_demand.csv", parse_dates=["week"])
    prod = pd.read_csv(OUT / "products.csv")
    cal = weekly[weekly.week < TEST_START]
    n_weeks = cal.week.nunique()

    g = cal.groupby("product_id").units
    seg = pd.DataFrame({
        "units": g.sum(),
        "weeks_with_sales": g.size(),
        "mean_nonzero": g.mean(),
        "cv2": (g.std(ddof=0) / g.mean()).fillna(0) ** 2,
    })
    seg["adi_weeks"] = n_weeks / seg.weeks_with_sales
    seg = seg.join(prod.set_index("product_id"))
    seg["revenue"] = seg.units * seg.price

    seg = seg.sort_values("revenue", ascending=False)
    cum = seg.revenue.cumsum() / seg.revenue.sum()
    seg["abc"] = np.select([cum <= 0.80, cum <= 0.95], ["A", "B"], "C")
    smooth_adi = seg.adi_weeks < 1.32
    low_cv = seg.cv2 < 0.49
    seg["pattern"] = np.select([smooth_adi & low_cv, smooth_adi, low_cv], ["smooth", "erratic", "intermittent"], "lumpy")
    recent = cal[cal.week >= cal.week.max() - pd.Timedelta(weeks=RECENT_WEEKS - 1)]
    seg["recent_weeks_with_sales"] = recent.groupby("product_id").size().reindex(seg.index).fillna(0).astype(int)
    seg["recent_units"] = recent.groupby("product_id").units.sum().reindex(seg.index).fillna(0).astype(int)
    seg["stock_in_fc"] = seg.recent_weeks_with_sales >= MIN_RECENT_WEEKS_WITH_SALES
    seg = seg.reset_index().rename(columns={"index": "product_id"})
    seg.to_csv(OUT / "segmentation.csv", index=False)

    # Summary matrix and the coverage trade-off (how many SKUs to cover x% of units)
    matrix = seg.pivot_table(index="abc", columns="pattern", values="product_id", aggfunc="count", fill_value=0)
    stocked = seg[seg.stock_in_fc]
    summary = pd.DataFrame([{
        "products_total": len(seg), "products_stocked": len(stocked),
        "share_products_stocked_pct": len(stocked) / len(seg) * 100,
        "share_units_covered_pct": stocked.units.sum() / seg.units.sum() * 100,
        "share_revenue_covered_pct": stocked.revenue.sum() / seg.revenue.sum() * 100,
        "calibration_weeks": n_weeks,
    }])
    summary.round(2).to_csv(OUT / "segmentation_summary.csv", index=False)
    matrix.to_csv(OUT / "abc_pattern_matrix.csv")

    by_units = seg.sort_values("units", ascending=False)
    curve = pd.DataFrame({"skus": np.arange(1, len(by_units) + 1),
                          "units_covered_pct": by_units.units.cumsum().to_numpy() / by_units.units.sum() * 100})
    curve[curve.skus.isin(list(range(25, 1001, 25)) + [2000, 5000, 10000, len(curve)])].round(2).to_csv(
        OUT / "sku_coverage_curve.csv", index=False)

    print("ABC x demand pattern (products):\n", matrix.to_string())
    print("\n", summary.round(1).T.to_string(header=False))
    print("\nStocked products by pattern:", stocked.pattern.value_counts().to_dict(),
          "| by ABC:", stocked.abc.value_counts().to_dict())


if __name__ == "__main__":
    main()
