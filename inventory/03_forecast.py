"""Step 3 - Weekly demand forecasts for the stocked products, compared in a backtest.

Methods (one-step-ahead, each forecast only uses weeks before it):
  naive     last week's demand
  ma4       average of the last 4 weeks
  ses       simple exponential smoothing, alpha fitted per product on the calibration weeks
  croston   Croston with the SBA bias correction (alpha = 0.1), built for intermittent demand
Backtest: the 16 test weeks. Metrics: WAPE = sum|error| / sum(actual), bias = sum(error) / sum(actual).
Choice for the stock policy (04): MA4. Naive and MA4 are within ~2 points of WAPE, but naive jumps with every
single busy week (one spike doubles the reorder point), which causes order spikes; SES and Croston over-forecast
because many products fade after their peak.
"""
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TEST_START = pd.Timestamp("2018-04-30")
WARMUP = 8                      # weeks before in-sample errors are counted
SES_ALPHAS = np.round(np.arange(0.05, 0.55, 0.05), 2)
CROSTON_ALPHA = 0.1


def naive(y):
    return np.r_[np.nan, y[:-1]]


def ma4(y):
    f = pd.Series(y).rolling(4, min_periods=1).mean().shift(1).to_numpy()
    return f


def ses(y, alpha):
    f = np.full(len(y), np.nan)
    level = y[:WARMUP].mean()
    for t in range(len(y)):
        f[t] = level
        level = alpha * y[t] + (1 - alpha) * level
    return f


def croston_sba(y, alpha=CROSTON_ALPHA):
    f = np.full(len(y), np.nan)
    nz = np.flatnonzero(y[:WARMUP] > 0)
    z = y[nz].mean() if len(nz) else 1.0            # demand size when it occurs
    p = WARMUP / max(len(nz), 1)                     # weeks between demands
    q = 1
    for t in range(len(y)):
        f[t] = (1 - alpha / 2) * z / p
        if y[t] > 0:
            z = alpha * y[t] + (1 - alpha) * z
            p = alpha * q + (1 - alpha) * p
            q = 1
        else:
            q += 1
    return f


def main() -> None:
    weekly = pd.read_csv(OUT / "weekly_demand.csv", parse_dates=["week"])
    seg = pd.read_csv(OUT / "segmentation.csv")
    stocked = seg[seg.stock_in_fc].set_index("product_id")

    weeks = pd.date_range(weekly.week.min(), weekly.week.max(), freq="W-MON")
    grid = (weekly[weekly.product_id.isin(stocked.index)]
            .pivot_table(index="week", columns="product_id", values="units", aggfunc="sum")
            .reindex(weeks).fillna(0))
    n_cal = int((weeks < TEST_START).sum())

    rows = []
    for pid in grid.columns:
        y = grid[pid].to_numpy(float)
        cal = slice(WARMUP, n_cal)
        # SES: choose alpha by in-sample squared error on the calibration weeks only
        best_a = min(SES_ALPHAS, key=lambda a: np.nanmean((ses(y[:n_cal], a)[cal] - y[cal]) ** 2))
        fc = {"naive": naive(y), "ma4": ma4(y), "ses": ses(y, best_a), "croston": croston_sba(y)}
        for m, f in fc.items():
            err = f - y
            rows.append({"product_id": pid, "method": m,
                         "abs_err_test": np.abs(err[n_cal:]).sum(), "err_test": err[n_cal:].sum(),
                         "actual_test": y[n_cal:].sum()})

    res = pd.DataFrame(rows).merge(stocked[["pattern"]], left_on="product_id", right_index=True)

    def score(df):
        return pd.Series({"wape_pct": df.abs_err_test.sum() / df.actual_test.sum() * 100,
                          "bias_pct": df.err_test.sum() / df.actual_test.sum() * 100})

    overall = res.groupby("method").apply(score, include_groups=False).sort_values("wape_pct")
    by_pattern = res.groupby(["pattern", "method"]).apply(score, include_groups=False).unstack("method")["wape_pct"]

    overall.round(2).to_csv(OUT / "forecast_backtest.csv")
    by_pattern.round(2).to_csv(OUT / "forecast_backtest_by_pattern.csv")

    print("Backtest on 16 test weeks (stocked products):\n", overall.round(1).to_string())
    print("\nWAPE % by demand pattern:\n", by_pattern.round(1).to_string())
    print("\nUsed in the stock policy: ma4 (see docstring)")


if __name__ == "__main__":
    main()
