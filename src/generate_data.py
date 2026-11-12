"""
Builds a synthetic store-sales dataset, one row per store per day.

Why synthetic: this repo downloads nothing. The layout copies the public Rossmann
Store Sales dataset (Store, Date, Sales, Customers, Open, Promo, SchoolHoliday), so
the real file can be dropped in later with no code change (see NEEDS.md).

Everything is driven by one seed, so the same seed always produces the same file.

PLANTED EFFECTS. Because I wrote this generator, I know the true answers. They are
listed in PLANTED below and in the README. That makes the synthetic run a check that
the method finds what is really there and does not find what is not. It is a
rehearsal of the method, not evidence about real shoppers.
"""
import numpy as np
import pandas as pd

from config import load_config, path

# The true effects built into the data, on the log scale (0.10 is about +10.5%).
PLANTED = {
    "promo_on_customers": 0.15,     # promotions bring in more people (average across stores)
    "promo_on_customers_sd": 0.05,  # stores differ in how much they respond
    "promo_on_basket": -0.01,       # discounts make each basket slightly smaller
    "promo_x_school_holiday": 0.0,  # no extra lift during school holidays
    "day_after_promo": -0.03,       # a small dip on the first open day after a promo
}


def school_holiday_dates(start, end):
    """Rough school-holiday calendar: winter break, spring break, a late-May week,
    summer and a fall week, repeated every year."""
    days = []
    for year in range(start.year, end.year + 1):
        spans = [
            (f"{year}-01-01", f"{year}-01-05"),   # end of winter break
            (f"{year}-03-30", f"{year}-04-10"),   # spring break
            (f"{year}-05-25", f"{year}-05-29"),   # late-May week
            (f"{year}-07-01", f"{year}-08-14"),   # summer
            (f"{year}-10-19", f"{year}-10-23"),   # fall week
            (f"{year}-12-21", f"{year}-12-31"),   # winter break
        ]
        for a, b in spans:
            days.extend(pd.date_range(a, b))
    return set(d for d in days if start <= d <= end)


def closed_holidays(start, end):
    """Days every store is closed (like public holidays in Rossmann)."""
    days = []
    for year in range(start.year, end.year + 1):
        days += [f"{year}-01-01", f"{year}-05-01", f"{year}-12-25", f"{year}-12-26"]
    return set(pd.Timestamp(d) for d in days if start <= pd.Timestamp(d) <= end)


def main():
    cfg = load_config()
    s = cfg["synthetic"]
    rng = np.random.default_rng(s["seed"])
    start, end = pd.Timestamp(s["start"]), pd.Timestamp(s["end"])
    dates = pd.date_range(start, end, freq="D")
    n = s["n_stores"]

    school = school_holiday_dates(start, end)
    closed = closed_holidays(start, end)

    # Chain-wide promo calendar: promotions run Monday to Friday in alternating weeks,
    # the same pattern Rossmann uses. Some weeks are skipped at random.
    week_index = ((dates - start).days // 7).to_numpy()
    promo_week = week_index % 2 == 0
    skip_weeks = set(rng.choice(np.unique(week_index), size=10, replace=False))
    promo_week &= ~np.isin(week_index, list(skip_weeks))
    chain_promo = promo_week & (dates.dayofweek < 5)  # 0 = Monday ... 4 = Friday

    # Store traits: size, basket, how strongly each store responds to promotions
    store_size = rng.normal(np.log(600), 0.35, n)       # typical customers per day
    store_basket = rng.normal(np.log(9.5), 0.15, n)     # typical spend per customer
    promo_resp = rng.normal(PLANTED["promo_on_customers"], PLANTED["promo_on_customers_sd"], n)

    # Weekday pattern (Mon..Sun). Sundays are closed.
    dow_effect = np.array([0.05, -0.02, -0.03, -0.01, 0.04, 0.10, 0.0])
    # Gentle yearly season and about 3% growth a year
    t = (dates - start).days.to_numpy()
    season = 0.06 * np.sin(2 * np.pi * (dates.dayofyear.to_numpy() - 80) / 365.25)
    trend = 0.03 * t / 365.25

    rows = []
    for i in range(n):
        store_promo = chain_promo & (rng.random(len(dates)) > 0.03)  # a few stores sit out a day
        is_school = np.array([d in school for d in dates])
        is_open = (dates.dayofweek < 6) & ~np.array([d in closed for d in dates])
        # A few random closures per store (renovation, staffing)
        is_open &= rng.random(len(dates)) > 0.005

        # "Day after promo": first open non-promo day right after a promo day
        day_after = np.zeros(len(dates), dtype=bool)
        last_open_was_promo = False
        for k in range(len(dates)):
            if not is_open[k]:
                continue
            if not store_promo[k] and last_open_was_promo:
                day_after[k] = True
            last_open_was_promo = bool(store_promo[k])

        log_cust = (store_size[i] + dow_effect[dates.dayofweek] + season + trend
                    + 0.03 * is_school
                    + promo_resp[i] * store_promo
                    + PLANTED["promo_x_school_holiday"] * store_promo * is_school
                    + PLANTED["day_after_promo"] * day_after
                    + rng.normal(0, 0.08, len(dates)))
        log_basket = (store_basket[i] + 0.5 * season
                      + PLANTED["promo_on_basket"] * store_promo
                      + rng.normal(0, 0.05, len(dates)))

        customers = np.where(is_open, np.round(np.exp(log_cust)), 0).astype(int)
        sales = np.where(is_open, np.round(customers * np.exp(log_basket)), 0).astype(int)

        rows.append(pd.DataFrame({
            "Store": i + 1,
            "Date": dates.strftime("%Y-%m-%d"),
            "Sales": sales,
            "Customers": customers,
            "Open": is_open.astype(int),
            "Promo": (store_promo & is_open).astype(int),
            "SchoolHoliday": is_school.astype(int),
        }))

    df = pd.concat(rows, ignore_index=True)
    out = path(cfg["data"]["path"])
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out, index=False)
    print(f"Wrote {len(df):,} rows for {n} stores to {out.relative_to(path('.'))}")


if __name__ == "__main__":
    main()
