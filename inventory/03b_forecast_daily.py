"""Step 3b - Forecast the São Paulo FC's TOTAL daily volume: where Holt-Winters belongs.

Why a second level: per-product weekly demand is mostly zeros (step 3), so seasonal models don't fit there.
The FC's total daily volume is smooth and has a clear weekday pattern (Mon/Tue ~13% above average, Sat ~24% below),
which is exactly what Holt-Winters is built for. This forecast drives warehouse staffing and the daily fleet (project 2).

Backtest: every Monday of the 16 test weeks, each model is refitted on all days before it and forecasts the next
7 days (rolling origin, 112 forecast days). Metrics: WAPE, scaled RMSE, bias (as in step 3).
Methods:
  naive            yesterday's volume, repeated
  seasonal_naive   same weekday last week
  ma7              average of the last 7 days
  ses              simple exponential smoothing
  holt             level + trend
  holt_damped      level + damped trend
  hw_additive      Holt-Winters: level + damped trend + additive weekday season (period 7)
  hw_multiplicative Holt-Winters with a multiplicative weekday season (the weekday effect scales with volume)
  seasonal_ses     level + weekday season, no trend (ETS A,N,A)
"""
from pathlib import Path
import warnings

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TEST_START, TEST_END = pd.Timestamp("2018-04-30"), pd.Timestamp("2018-08-19")
HORIZON = 7

LABELS = {"naive": "Naive", "seasonal_naive": "Seasonal naive", "ma7": "Moving avg (7 d)", "ses": "Exp. smoothing",
          "holt": "Holt", "holt_damped": "Holt damped", "seasonal_ses": "Seasonal ES (no trend)",
          "hw_additive": "Holt-Winters (additive)", "hw_multiplicative": "Holt-Winters (multiplicative)"}


def forecast(method, y):
    """7-day-ahead forecast from history y (pd.Series, daily)."""
    if method == "naive":
        return np.repeat(y.iloc[-1], HORIZON)
    if method == "seasonal_naive":
        return y.iloc[-7:].to_numpy()
    if method == "ma7":
        return np.repeat(y.iloc[-7:].mean(), HORIZON)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if method == "ses":
            m = SimpleExpSmoothing(y, initialization_method="estimated").fit()
        elif method == "holt":
            m = ExponentialSmoothing(y, trend="add", initialization_method="estimated").fit()
        elif method == "holt_damped":
            m = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
        elif method == "seasonal_ses":
            m = ExponentialSmoothing(y, seasonal="add", seasonal_periods=7, initialization_method="estimated").fit()
        elif method == "hw_additive":
            m = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add", seasonal_periods=7,
                                     initialization_method="estimated").fit()
        elif method == "hw_multiplicative":
            m = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="mul", seasonal_periods=7,
                                     initialization_method="estimated").fit()
        return np.clip(m.forecast(HORIZON).to_numpy(), 0, None)


def main() -> None:
    d = pd.read_csv(OUT / "daily_demand.csv", parse_dates=["order_date"])
    total = d.groupby("order_date").units.sum()
    total = total.reindex(pd.date_range(total.index.min(), TEST_END), fill_value=0).astype(float)
    total.index.freq = "D"

    rows, series = [], []
    for origin in pd.date_range(TEST_START, TEST_END, freq="7D"):
        hist = total[:origin - pd.Timedelta(days=1)]
        actual = total[origin:origin + pd.Timedelta(days=HORIZON - 1)]
        for method in LABELS:
            f = forecast(method, hist)[:len(actual)]
            for day, a, p in zip(actual.index, actual.to_numpy(), f):
                rows.append({"method": method, "date": day, "actual": a, "forecast": p})

    res = pd.DataFrame(rows)
    res["err"] = res.forecast - res.actual

    def score(g):
        return pd.Series({"wape_pct": g.err.abs().sum() / g.actual.sum() * 100,
                          "scaled_rmse_pct": np.sqrt((g.err ** 2).mean()) / g.actual.mean() * 100,
                          "bias_pct": g.err.sum() / g.actual.sum() * 100})

    table = res.groupby("method").apply(score, include_groups=False).sort_values("wape_pct")
    table["label"] = table.index.map(LABELS)
    table.round(2).to_csv(OUT / "forecast_daily_backtest.csv")
    best = table.index[0]
    keep = res[res.method.isin([best, "ma7", "seasonal_naive"])].pivot(index="date", columns="method", values="forecast")
    keep.insert(0, "actual", res.drop_duplicates("date").set_index("date").actual)
    keep.round(1).to_csv(OUT / "forecast_daily_series.csv")

    weekday = total[:TEST_START - pd.Timedelta(days=1)]
    idx = (weekday.groupby(weekday.index.dayofweek).mean() / weekday.mean()).rename(
        index=dict(enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])))
    idx.round(3).to_csv(OUT / "weekday_index.csv", header=["index"])

    print("FC daily volume, 7-day-ahead rolling backtest (112 days):\n",
          table[["label", "wape_pct", "scaled_rmse_pct", "bias_pct"]].round(1).to_string())
    print("\nWeekday index:", idx.round(2).to_dict())


if __name__ == "__main__":
    main()
