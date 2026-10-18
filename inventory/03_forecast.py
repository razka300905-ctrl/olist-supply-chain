"""Step 3 - Weekly demand forecasts per stocked product, compared in a backtest.

Methods (one-step-ahead, each forecast only uses weeks before it; code in forecasting.py):
  naive        last week's demand
  ma4          average of the last 4 weeks
  ses          simple exponential smoothing, alpha fitted per product on the calibration weeks
  holt         Holt's linear trend (level + trend), alpha/beta fitted per product on the calibration weeks
  holt_damped  Holt with a damped trend (phi = 0.9), so a trend fades instead of running forever
  croston      Croston with the SBA bias correction, built for intermittent demand
  tsb          Teunter-Syntetos-Babai: like Croston, but reacts when a product stops selling
Holt-Winters (seasonal) is NOT used at this level: it needs at least two full seasons (2 x 52 weeks of history;
we have 34 calibration weeks), and the many zero weeks make a seasonal pattern meaningless. It is tested on the
FC's total daily demand instead, which has a clear weekday pattern (03b_forecast_daily.py).

Backtest: the 16 test weeks. Metrics:
  WAPE        = sum|error| / sum(actual)      (rewards forecasts near the median; for intermittent demand that is ~0)
  scaled RMSE = RMSE / mean(actual)           (rewards getting the average right, which is what stock needs)
  bias        = sum(error) / sum(actual)      (positive = forecasts too high)
Because the two error metrics disagree, the final choice is made on the stock outcome: each method is plugged
into the inventory simulation (04_policy_simulation.py, sweep "forecast").
"""
from pathlib import Path

import numpy as np
import pandas as pd

from forecasting import WARMUP, croston_sba, holt, ma, naive, ses, tsb

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TEST_START = pd.Timestamp("2018-04-30")
SES_ALPHAS = np.round(np.arange(0.05, 0.55, 0.05), 2)
HOLT_ALPHAS, HOLT_BETAS = [0.1, 0.2, 0.3, 0.5], [0.05, 0.1, 0.2]


def fit(y, n_cal, candidates, model):
    """Pick the parameters with the lowest squared error on the calibration weeks only."""
    cal = slice(WARMUP, n_cal)
    best = min(candidates, key=lambda p: np.nanmean((model(y[:n_cal], *p)[cal] - y[cal]) ** 2))
    return model(y, *best)


def main() -> None:
    weekly = pd.read_csv(OUT / "weekly_demand.csv", parse_dates=["week"])
    seg = pd.read_csv(OUT / "segmentation.csv")
    stocked = seg[seg.stock_in_fc].set_index("product_id")

    weeks = pd.date_range(weekly.week.min(), weekly.week.max(), freq="W-MON")
    grid = (weekly[weekly.product_id.isin(stocked.index)]
            .pivot_table(index="week", columns="product_id", values="units", aggfunc="sum")
            .reindex(weeks).fillna(0))
    n_cal = int((weeks < TEST_START).sum())
    holt_grid = [(a, b) for a in HOLT_ALPHAS for b in HOLT_BETAS]

    rows = []
    for pid in grid.columns:
        y = grid[pid].to_numpy(float)
        fc = {
            "naive": naive(y), "ma4": ma(y), "ses": fit(y, n_cal, [(a,) for a in SES_ALPHAS], ses),
            "holt": fit(y, n_cal, holt_grid, lambda v, a, b: holt(v, a, b, 1.0)),
            "holt_damped": fit(y, n_cal, holt_grid, lambda v, a, b: holt(v, a, b, 0.9)),
            "croston": croston_sba(y), "tsb": tsb(y),
        }
        for m, f in fc.items():
            err = f - y
            rows.append({"product_id": pid, "method": m,
                         "abs_err_test": np.abs(err[n_cal:]).sum(), "err_test": err[n_cal:].sum(),
                         "sq_err_test": (err[n_cal:] ** 2).sum(), "n_test": len(y) - n_cal,
                         "actual_test": y[n_cal:].sum()})

    res = pd.DataFrame(rows).merge(stocked[["pattern"]], left_on="product_id", right_index=True)

    def score(df):
        mean_actual = df.actual_test.sum() / df.n_test.sum()
        return pd.Series({"wape_pct": df.abs_err_test.sum() / df.actual_test.sum() * 100,
                          "scaled_rmse_pct": np.sqrt(df.sq_err_test.sum() / df.n_test.sum()) / mean_actual * 100,
                          "bias_pct": df.err_test.sum() / df.actual_test.sum() * 100})

    overall = res.groupby("method").apply(score, include_groups=False).sort_values("wape_pct")
    by_pattern = res.groupby(["pattern", "method"]).apply(score, include_groups=False).unstack("method")["wape_pct"]
    overall.round(2).to_csv(OUT / "forecast_backtest.csv")
    by_pattern.round(2).to_csv(OUT / "forecast_backtest_by_pattern.csv")

    print("Backtest on 16 test weeks (stocked products):\n", overall.round(1).to_string())
    print("\nWAPE % by demand pattern:\n", by_pattern.round(1).to_string())


if __name__ == "__main__":
    main()
