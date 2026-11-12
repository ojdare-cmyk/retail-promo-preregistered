"""
Step 2: exploratory look at the TRAINING window only.

Allowed by rule 2 of HYPOTHESES.md: charts and a dry run of the 5 tests to check
the code works. Nothing here reads data/holdout.csv. Every output is labelled
EXPLORATORY because the baseline is fit on the same days it is tested on, which
makes these numbers optimistic.
"""
import json

import matplotlib
matplotlib.use("Agg")  # save charts to files, no window
import matplotlib.pyplot as plt
import pandas as pd

from config import load_config, path
from features import clean, mark_day_after, fit_baseline, add_deviations
from hypothesis_tests import run_tests

CHARTS = path("results/charts")


def main():
    cfg = load_config()
    plan = cfg["plan"]
    info = json.load(open(path("results/split_info.json")))
    train = pd.read_csv(path("data/train.csv"), parse_dates=["date"])

    d = mark_day_after(clean(train))
    d = add_deviations(d, fit_baseline(d))

    # Chart 1: chain-wide weekly sales, with the sealed holdout shown as an empty box
    weekly = d.set_index("date")["sales"].resample("W").sum() / 1e6
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(weekly.index, weekly.values, color="#1f4e79")
    ax.axvspan(pd.Timestamp(info["holdout_start"]), pd.Timestamp(info["holdout_end"]),
               color="#bbbbbb", alpha=0.5, label="sealed holdout (not plotted)")
    ax.set_title("EXPLORATORY: weekly chain sales, training window only")
    ax.set_ylabel("sales, millions")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(CHARTS / "01_train_weekly_sales.png", dpi=150)
    plt.close(fig)

    # Chart 2: average deviation from normal by weekday, promo vs non-promo days
    by_day = d.groupby(["weekday", "promo"])["dev_sales"].mean().unstack() * 100
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_day.index = [names[i] for i in by_day.index]  # works if some stores open Sundays
    ax = by_day.rename(columns={0: "no promo", 1: "promo"}).plot.bar(
        figsize=(8, 4), color=["#999999", "#d9822b"], rot=0)
    # No-promo bars sit at 0 by construction: the baseline IS the no-promo average
    ax.set_title("EXPLORATORY (training): promo-day sales vs the store's normal no-promo day")
    ax.set_ylabel("% above normal (log scale x 100)")
    ax.axhline(0, color="black", linewidth=0.8)
    plt.tight_layout()
    plt.savefig(CHARTS / "02_train_weekday_promo.png", dpi=150)
    plt.close()

    # Dry run of the 5 pre-registered tests on training data
    table, _ = run_tests(d, plan["min_days_per_group"], plan["alpha"])
    table.insert(0, "window", "TRAINING (exploratory, in-sample)")
    table.to_csv(path("results/exploratory_train_tests.csv"), index=False)
    print("EXPLORATORY dry run on training data (not the result):")
    print(table[["id", "stores_used", "effect_pct", "p_holm", "verdict"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
