"""
Shared data steps used by both the exploratory script and the confirmatory script,
so the training dry run and the holdout run do exactly the same thing.

Rules 4 and 5 in HYPOTHESES.md live here.
"""
import numpy as np
import pandas as pd

METRICS = ["sales", "customers", "basket"]


def clean(df):
    """Rule 4: keep open days with sales and customers above zero, add basket size."""
    d = df[(df["open"] == 1) & (df["sales"] > 0) & (df["customers"] > 0)].copy()
    d["basket"] = d["sales"] / d["customers"]
    d["weekday"] = d["date"].dt.dayofweek
    return d


def mark_day_after(d):
    """Flag the first open non-promo day right after a promo day, per store (H5).

    Works on cleaned rows only, so "previous day" means the previous OPEN day.
    The first day in the frame has no previous day and is never flagged.
    """
    d = d.sort_values(["store", "date"]).copy()
    prev_promo = d.groupby("store")["promo"].shift(1)
    d["day_after"] = ((d["promo"] == 0) & (prev_promo == 1)).astype(int)
    return d


def fit_baseline(train):
    """Rule 5: each store's normal level per weekday, from non-promo training days.

    Returns one row per (store, weekday) with the mean of log(value) for
    sales, customers and basket.
    """
    t = train[train["promo"] == 0]
    logs = t[["store", "weekday"]].copy()
    for m in METRICS:
        logs[m] = np.log(t[m])
    return logs.groupby(["store", "weekday"]).mean().add_prefix("base_").reset_index()


def add_deviations(d, baseline):
    """Turn each day into how far it sits above or below that store's normal
    for that weekday, on the log scale. 0.05 means about 5% above normal.
    Days with no baseline (a weekday the store never opened in training) drop out.
    """
    out = d.merge(baseline, on=["store", "weekday"], how="inner")
    for m in METRICS:
        out[f"dev_{m}"] = np.log(out[m]) - out[f"base_{m}"]
    return out
