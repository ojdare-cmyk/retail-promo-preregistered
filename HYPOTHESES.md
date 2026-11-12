# Pre-registered analysis plan

Written and committed on 2026-10-20, **before any data file existed in this repo and
before any analysis code was written.** The git history is the proof: this file's
first commit comes before the data generator, before the train/holdout split and
before the script that opens the holdout. If anything here changes after the holdout
is opened, the change goes in the "Deviations" section at the bottom, and the
original result stays in the results table.

## The business question

A chain of stores runs promotions. Management wants to know what a promotion actually
does: does it bring more people in, does it make each basket bigger, does it work
better at some times than others, and does it just steal sales from the days after it?

## Data the plan expects

One row per store per day, with these fields (names are set in `config.yaml`, so a
different dataset only needs a config change):

| Field | Meaning |
|---|---|
| store | store id |
| date | calendar date |
| sales | revenue that day |
| customers | number of customers that day |
| open | 1 if the store was open |
| promo | 1 if a promotion ran that day |
| school_holiday | 1 if local schools were on holiday |

## Rules that apply to every test

1. **Holdout.** The last 3 calendar months of the data are the holdout. Everything
   before that is the training window.
2. **What training data may be used for:** building each store's normal level (the
   baseline below), checking that the code runs, and exploratory charts that are
   labelled exploratory. It may not be used to add, drop or rewrite a hypothesis.
3. **The holdout is opened once.** The confirmatory script records the date, time and
   a fingerprint (SHA-256) of the holdout file when it runs, and refuses to run a
   second time on the same data.
4. **Days used:** only days where the store was open and sales were above zero.
5. **Baseline.** For each store and each day of the week, the baseline is the mean of
   log(value) on open, non-promo days in the training window. Every holdout day is
   turned into a deviation: `dev = log(value) - baseline[store, weekday]`. This takes
   out store size and the weekday pattern, so a big store or a busy Saturday does not
   look like a promotion effect.
6. **Unit of analysis is the store, not the day.** Days inside one store are not
   independent, so each test first reduces the holdout to one number per store, then
   tests across stores.
7. **Minimum data.** A store enters a test only if it has at least 5 holdout days in
   every group that test compares. The number of stores dropped is reported for every
   test.
8. **Lift** for a store = mean dev on promo days minus mean dev on non-promo days.
   It is reported as a percentage, `exp(lift) - 1`.

## The 5 hypotheses

| # | Hypothesis | Per-store number | Test | Direction |
|---|---|---|---|---|
| H1 | Promotions raise daily sales | sales lift | one-sample t-test across stores, mean > 0 | greater |
| H2 | Promotions raise customer traffic | customer-count lift | one-sample t-test across stores, mean > 0 | greater |
| H3 | Promotions raise basket size (sales per customer) | basket lift | one-sample t-test across stores, mean > 0 | greater |
| H4 | The sales lift is larger during school holidays | sales lift on school-holiday days minus sales lift on other days | one-sample t-test across stores, mean > 0 | greater |
| H5 | Promotions pull sales forward: the first open non-promo day after a promo day sells less than other non-promo days | mean sales dev on those "day after" days minus mean sales dev on other non-promo days | one-sample t-test across stores, mean < 0 | less |

## Significance and correction

- Family-wise alpha: **0.05**.
- Correction for running 5 tests: **Holm-Bonferroni** across all 5 p-values.
- A hypothesis **held** if its Holm-adjusted p-value is below 0.05 in the stated
  direction. Otherwise it **did not hold**. Both outcomes are reported with the same
  prominence.
- Also reported for each test, but not used for the verdict: the effect size as a
  percentage, a 95% confidence interval, the number of stores used, and a Wilcoxon
  signed-rank p-value as a check that the t-test is not being driven by a few
  unusual stores.

## What would make me distrust a result

- A verdict that flips between the t-test and the Wilcoxon check gets flagged in the
  results, not hidden.
- If more than a quarter of stores are dropped by the minimum-data rule for a test,
  that test's result is flagged as thin.

## Deviations

Any change to the plan is listed here with the date and the reason.

1. **2026-10-20, before the holdout was opened.** Added one rule the plan had not
   covered: if fewer than 2 stores pass the minimum-data rule for a test, that test is
   reported as "not testable" and counted as **did not hold** (its p-value enters the
   Holm step as 1). Found by rehearsing `confirm_holdout.py` on a fake holdout cut
   from the training window, where H4 had no school-holiday promo days and the script
   crashed. This makes the plan stricter, not looser: a test that cannot be run can
   never count as a success.
