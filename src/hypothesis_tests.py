"""
The 5 pre-registered tests and the Holm-Bonferroni correction, exactly as written
in HYPOTHESES.md. Each test first reduces the data to one number per store
(rule 6), drops stores without enough days (rule 7), then tests across stores.
"""
import numpy as np
import pandas as pd
from scipy import stats

HYPOTHESES = {
    "H1": "Promotions raise daily sales",
    "H2": "Promotions raise customer traffic",
    "H3": "Promotions raise basket size",
    "H4": "Sales lift is larger during school holidays",
    "H5": "Day after a promo sells less (pull-forward)",
}


def group_mean(d, col, mask, min_days):
    """Mean of `col` per store over the rows in `mask`, or NaN if too few days."""
    g = d[mask].groupby("store")[col]
    means, counts = g.mean(), g.size()
    return means.where(counts >= min_days)


def per_store_lift(d, col, min_days, extra=None):
    """Promo-day mean minus non-promo-day mean, per store (rule 8).
    `extra` optionally restricts both groups (used by H4)."""
    base = np.ones(len(d), dtype=bool) if extra is None else extra.to_numpy()
    promo = d["promo"].to_numpy() == 1
    a = group_mean(d, col, base & promo, min_days)
    b = group_mean(d, col, base & ~promo, min_days)
    return a.sub(b)


def per_store_numbers(d, min_days):
    """One Series per hypothesis: index = store, value = that store's number."""
    all_stores = pd.Index(sorted(d["store"].unique()))
    school = d["school_holiday"] == 1
    non_promo = d["promo"].to_numpy() == 0
    after = d["day_after"].to_numpy() == 1

    numbers = {
        "H1": per_store_lift(d, "dev_sales", min_days),
        "H2": per_store_lift(d, "dev_customers", min_days),
        "H3": per_store_lift(d, "dev_basket", min_days),
        # H4: lift inside school holidays minus lift outside them
        "H4": per_store_lift(d, "dev_sales", min_days, school)
              .sub(per_store_lift(d, "dev_sales", min_days, ~school)),
        # H5: day-after-promo days minus every other non-promo day
        "H5": group_mean(d, "dev_sales", non_promo & after, min_days)
              .sub(group_mean(d, "dev_sales", non_promo & ~after, min_days)),
    }
    return {k: v.reindex(all_stores) for k, v in numbers.items()}


def holm(pvalues):
    """Holm-Bonferroni: sort p-values, multiply the smallest by 5, the next by 4,
    and so on, never letting an adjusted value drop below the one before it."""
    p = np.asarray(pvalues, dtype=float)
    order = np.argsort(p)
    m = len(p)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        running_max = max(running_max, (m - rank) * p[idx])
        adjusted[idx] = min(1.0, running_max)
    return adjusted


def run_tests(d, min_days, alpha):
    """Run all 5 tests and return the results table (one row per hypothesis)."""
    numbers = per_store_numbers(d, min_days)
    rows = []
    for hid, values in numbers.items():
        x = values.dropna().to_numpy()
        n_total = len(values)
        direction = "less" if hid == "H5" else "greater"
        row = {"id": hid, "hypothesis": HYPOTHESES[hid], "direction": direction,
               "stores_used": len(x), "stores_dropped": n_total - len(x)}
        if len(x) < 2:
            # Not testable: too few stores passed the minimum-data rule.
            # Counted as "did not hold" (p = 1 in the Holm step); see Deviations.
            row.update(effect_pct=np.nan, ci_low_pct=np.nan, ci_high_pct=np.nan,
                       t_stat=np.nan, p_raw=1.0, p_wilcoxon=1.0, testable=False)
            rows.append(row)
            continue
        t_res = stats.ttest_1samp(x, 0.0, alternative=direction)
        w_res = stats.wilcoxon(x, alternative=direction)
        # 95% confidence interval for the mean (two-sided, not corrected)
        se = x.std(ddof=1) / np.sqrt(len(x))
        half = stats.t.ppf(0.975, len(x) - 1) * se
        mean = x.mean()
        row.update(
            effect_pct=100 * (np.exp(mean) - 1),
            ci_low_pct=100 * (np.exp(mean - half) - 1),
            ci_high_pct=100 * (np.exp(mean + half) - 1),
            t_stat=t_res.statistic, p_raw=t_res.pvalue, p_wilcoxon=w_res.pvalue,
            testable=True)
        rows.append(row)
    table = pd.DataFrame(rows)
    table["p_holm"] = holm(table["p_raw"])
    table["verdict"] = np.where(table["p_holm"] < alpha, "held", "did not hold")

    # Flags from "What would make me distrust a result" in HYPOTHESES.md
    flags = []
    for _, r in table.iterrows():
        f = []
        if not r["testable"]:
            f.append("not testable: fewer than 2 stores had enough days")
        elif (r["p_wilcoxon"] < alpha) != (r["p_raw"] < alpha):
            f.append("t-test and Wilcoxon disagree at 0.05 (uncorrected)")
        if r["stores_dropped"] > 0.25 * (r["stores_used"] + r["stores_dropped"]):
            f.append("thin: over a quarter of stores dropped")
        flags.append("; ".join(f))
    table["flags"] = flags
    return table, numbers
