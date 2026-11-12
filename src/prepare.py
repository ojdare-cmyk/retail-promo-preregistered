"""
Step 1 of the pipeline: load the raw CSV, rename columns to the plan's names,
split it into a training window and a sealed holdout, and fingerprint the holdout.

The holdout file is written here but NOT read by any analysis script except
confirm_holdout.py, which opens it once.
"""
import hashlib
import json

import pandas as pd

from config import load_config, path


def file_sha256(p):
    """Fingerprint a file. If even one number in it changes, this changes."""
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_raw(cfg):
    """Read the CSV and rename its columns to the plan's field names."""
    d = cfg["data"]
    cols = d["columns"]
    raw = pd.read_csv(path(d["path"]), usecols=list(cols.values()), low_memory=False)
    df = raw.rename(columns={v: k for k, v in cols.items()})
    df["date"] = pd.to_datetime(df["date"], format=d["date_format"])
    for c in ["open", "promo", "school_holiday"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df.sort_values(["store", "date"]).reset_index(drop=True)


def main():
    cfg = load_config()
    df = load_raw(cfg)

    # Holdout = the last N calendar months (rule 1 in HYPOTHESES.md)
    last_day = df["date"].max()
    months = cfg["plan"]["holdout_months"]
    # Start of the month (months - 1) before the last month, e.g. data ending in June
    # with 3 holdout months gives a holdout of April, May and June.
    holdout_start = (last_day.to_period("M") - (months - 1)).start_time

    train = df[df["date"] < holdout_start]
    holdout = df[df["date"] >= holdout_start]

    train_path, holdout_path = path("data/train.csv"), path("data/holdout.csv")
    train.to_csv(train_path, index=False, date_format="%Y-%m-%d")
    holdout.to_csv(holdout_path, index=False, date_format="%Y-%m-%d")

    info = {
        "source_file": cfg["data"]["path"],
        "source_sha256": file_sha256(path(cfg["data"]["path"])),
        "train_start": str(train["date"].min().date()),
        "train_end": str(train["date"].max().date()),
        "holdout_start": str(holdout["date"].min().date()),
        "holdout_end": str(holdout["date"].max().date()),
        "train_rows": len(train),
        "holdout_rows": len(holdout),
        "holdout_sha256": file_sha256(holdout_path),
    }
    with open(path("results/split_info.json"), "w") as f:
        json.dump(info, f, indent=2)
    print(f"Training window {info['train_start']} to {info['train_end']} ({len(train):,} rows)")
    print(f"Holdout sealed  {info['holdout_start']} to {info['holdout_end']} ({len(holdout):,} rows)")
    print(f"Holdout fingerprint {info['holdout_sha256'][:16]}...")


if __name__ == "__main__":
    main()
