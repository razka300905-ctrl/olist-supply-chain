"""Forecasting methods shared by the backtest (03) and the stock simulation (04).

Every function takes a weekly demand series y and returns f, where f[t] is the forecast for week t
made with y[:t] only (one-step-ahead, no peeking). Forecasts are never negative.
"""
import numpy as np
import pandas as pd

WARMUP = 8   # weeks used to initialise level / size / probability


def naive(y):
    return np.r_[np.nan, y[:-1]]


def ma(y, window=4):
    return pd.Series(y).rolling(window, min_periods=1).mean().shift(1).to_numpy()


def ses(y, alpha=0.2):
    f = np.full(len(y), np.nan)
    level = y[:WARMUP].mean()
    for t in range(len(y)):
        f[t] = level
        level = alpha * y[t] + (1 - alpha) * level
    return f


def holt(y, alpha=0.2, beta=0.1, phi=1.0):
    """Holt's linear trend; phi < 1 damps the trend so it fades instead of running forever."""
    f = np.full(len(y), np.nan)
    level, trend = y[:WARMUP].mean(), 0.0
    for t in range(len(y)):
        f[t] = max(level + phi * trend, 0.0)
        new_level = alpha * y[t] + (1 - alpha) * (level + phi * trend)
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    return f


def croston_sba(y, alpha=0.1):
    """Croston with the Syntetos-Boylan bias correction, built for intermittent demand."""
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


def tsb(y, alpha_d=0.1, alpha_p=0.1):
    """Teunter-Syntetos-Babai: updates the demand probability every week, so it reacts when a product dies."""
    f = np.full(len(y), np.nan)
    nz = y[:WARMUP] > 0
    prob = nz.mean() if nz.any() else 0.1
    size = y[:WARMUP][nz].mean() if nz.any() else 1.0
    for t in range(len(y)):
        f[t] = prob * size
        prob = alpha_p * (y[t] > 0) + (1 - alpha_p) * prob
        if y[t] > 0:
            size = alpha_d * y[t] + (1 - alpha_d) * size
    return f


# Fixed-parameter versions used inside the weekly re-plan (refitting every product every week is not needed
# to compare methods, and keeps the simulation fast)
METHODS = {
    "naive": naive,
    "ma4": ma,
    "ses": ses,
    "holt": holt,
    "holt_damped": lambda y: holt(y, phi=0.9),
    "croston": croston_sba,
    "tsb": tsb,
}

LABELS = {"naive": "Naive", "ma4": "Moving avg (4 wk)", "ses": "Exp. smoothing", "holt": "Holt",
          "holt_damped": "Holt damped", "croston": "Croston (SBA)", "tsb": "TSB"}


def next_week(method, y):
    """Forecast for the week after the last observation."""
    return float(METHODS[method](np.r_[y, 0.0])[-1])
