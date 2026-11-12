"""
Step 3: open the sealed holdout ONCE and run the 5 pre-registered tests on it.

Safeguards (rule 3 of HYPOTHESES.md):
  * The holdout file must match the fingerprint taken when it was sealed.
  * HYPOTHESES.md must be committed with no unsaved edits, and its commit is recorded.
  * A lock file is written the moment the holdout is read. If that lock already
    exists for this exact holdout, the script refuses to run again and just shows
    the stored result.
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from config import load_config, path, ROOT
from features import clean, mark_day_after, fit_baseline, add_deviations
from hypothesis_tests import run_tests

CHARTS = path("results/charts")


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def git(*args):
    """Run a git command in the project folder; return its output or '' if git fails."""
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ""


def check_plan_is_committed():
    """Refuse to open the holdout if HYPOTHESES.md has uncommitted changes."""
    if git("status", "--porcelain", "HYPOTHESES.md"):
        sys.exit("HYPOTHESES.md has uncommitted edits. Commit the plan before opening the holdout.")
    first = git("log", "--diff-filter=A", "--format=%H %cI", "--", "HYPOTHESES.md")
    last = git("log", "-1", "--format=%H %cI", "--", "HYPOTHESES.md")
    return {"plan_first_commit": first.splitlines()[-1] if first else "unknown",
            "plan_latest_commit": last or "unknown"}


def main():
    cfg = load_config()
    plan = cfg["plan"]
    info = json.load(open(path("results/split_info.json")))
    holdout_path = path("data/holdout.csv")

    # 1. The holdout must be exactly the file that was sealed
    fingerprint = sha256(holdout_path)
    if fingerprint != info["holdout_sha256"]:
        sys.exit("Holdout file does not match its sealed fingerprint. Stopping.")

    # 2. One opening per holdout
    lock = path(f"results/holdout_opened_{fingerprint[:12]}.json")
    if lock.exists():
        print(f"This holdout was already opened on {json.load(open(lock))['opened_at']}.")
        print("Refusing to run again. The stored result is in results/RESULTS.md:\n")
        print(open(path("results/RESULTS.md")).read())
        return

    plan_commits = check_plan_is_committed()

    # 3. Write the lock BEFORE reading the data, so even a crash counts as opened
    record = {"opened_at": dt.datetime.now().isoformat(timespec="seconds"),
              "holdout_sha256": fingerprint, "holdout_start": info["holdout_start"],
              "holdout_end": info["holdout_end"], **plan_commits,
              "code_commit": git("rev-parse", "HEAD") or "unknown"}
    json.dump(record, open(lock, "w"), indent=2)

    train = pd.read_csv(path("data/train.csv"), parse_dates=["date"])
    holdout = pd.read_csv(holdout_path, parse_dates=["date"])

    # Baseline comes from training only (rule 5)
    train_clean = clean(train)
    baseline = fit_baseline(train_clean)

    # Mark "day after promo" with the last training week attached, so the first
    # holdout day can still see the day before it; then keep holdout days only.
    tail = train_clean[train_clean["date"] >= train_clean["date"].max() - pd.Timedelta(days=7)]
    both = mark_day_after(pd.concat([tail, clean(holdout)]))
    d = add_deviations(both[both["date"] >= pd.Timestamp(info["holdout_start"])], baseline)

    table, numbers = run_tests(d, plan["min_days_per_group"], plan["alpha"])
    table.to_csv(path("results/results_table.csv"), index=False)
    write_results_md(table, info, record, d)
    charts(table, numbers)
    print(open(path("results/RESULTS.md")).read())


def write_results_md(table, info, record, d):
    held = (table["verdict"] == "held").sum()
    lines = [
        "# Results: sealed holdout, opened once",
        "",
        f"Holdout {info['holdout_start']} to {info['holdout_end']}, "
        f"{d['store'].nunique()} stores, {len(d):,} open store-days. "
        f"Opened {record['opened_at']}.",
        f"Plan first committed: `{record['plan_first_commit']}`.",
        "",
        f"**{held} of 5 hypotheses held and {5 - held} did not**, at a family-wise alpha of "
        "0.05 with Holm-Bonferroni correction. Every hypothesis is listed, including the nulls.",
        "",
        "| # | Hypothesis | Effect | 95% CI | Stores | p (raw) | p (Holm) | Wilcoxon p | Verdict | Flags |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for _, r in table.iterrows():
        if not r["testable"]:
            lines.append(f"| {r['id']} | {r['hypothesis']} | n/a | n/a | {r['stores_used']} "
                         f"({r['stores_dropped']} dropped) | n/a | 1 | n/a | **{r['verdict']}** | {r['flags']} |")
            continue
        lines.append(
            f"| {r['id']} | {r['hypothesis']} | {r['effect_pct']:+.1f}% | "
            f"{r['ci_low_pct']:+.1f}% to {r['ci_high_pct']:+.1f}% | "
            f"{r['stores_used']} ({r['stores_dropped']} dropped) | {r['p_raw']:.2g} | "
            f"{r['p_holm']:.2g} | {r['p_wilcoxon']:.2g} | **{r['verdict']}** | {r['flags'] or 'none'} |")
    lines += ["", "Effect = average across stores, as a percentage. For H4 it is the extra lift "
              "inside school holidays; for H5 it is the day-after-promo gap versus other "
              "non-promo days. The CI is two-sided and not corrected; the verdict uses only the Holm p-value."]
    open(path("results/RESULTS.md"), "w").write("\n".join(lines) + "\n")


def charts(table, numbers):
    # Chart 3: every effect with its interval, coloured by verdict
    fig, ax = plt.subplots(figsize=(9, 4))
    y = np.arange(len(table))[::-1]
    for yi, (_, r) in zip(y, table.iterrows()):
        if not r["testable"]:
            ax.text(0, yi, "  not testable", va="center", color="#9e9e9e")
            continue
        color = "#2e7d32" if r["verdict"] == "held" else "#9e9e9e"
        ax.plot([r["ci_low_pct"], r["ci_high_pct"]], [yi, yi], color=color, linewidth=2)
        ax.scatter([r["effect_pct"]], [yi], color=color, s=60, zorder=3)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{i}: {h}" for i, h in zip(table["id"], table["hypothesis"])])
    ax.set_xlabel("effect, % (95% CI)   green = held after Holm correction, grey = did not hold")
    ax.set_title("Holdout result for all 5 pre-registered hypotheses")
    fig.tight_layout()
    fig.savefig(CHARTS / "03_holdout_effects.png", dpi=150)
    plt.close(fig)

    # Chart 4: how the per-store numbers spread for each hypothesis
    fig, axes = plt.subplots(1, 5, figsize=(14, 3), sharey=True)
    for ax, (hid, vals) in zip(axes, numbers.items()):
        pct = 100 * (np.exp(vals.dropna()) - 1)
        if len(pct):
            ax.hist(pct, bins=15, color="#1f4e79")
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_title(hid)
        ax.set_xlabel("% per store")
    axes[0].set_ylabel("stores")
    fig.suptitle("Holdout: one number per store, per hypothesis")
    fig.tight_layout()
    fig.savefig(CHARTS / "04_holdout_per_store.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
