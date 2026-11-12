# Notes from the training window, written before the holdout was opened

These come from `src/explore_train.py`, which reads only `data/train.csv`. They are
written down now so it is on the record that they were seen **before** the holdout
was opened. None of them changed the plan in HYPOTHESES.md.

1. **The dry run works end to end.** All 5 tests ran on the training window with all
   60 stores passing the minimum-data rule. Those numbers are in
   `results/exploratory_train_tests.csv` and are in-sample, so they are not results.

2. **A weakness in H4, found in training and left in place.** The baseline takes out
   store size and weekday, but not the time of year. Inside school holidays, the promo
   days and the non-promo days fall in different months (for example, in this calendar
   the March and late-May school-holiday days happen to be non-promo weeks, and those
   are seasonally strong days). So "lift during school holidays" is partly a season
   comparison. In training this made the H4 number negative (about -2.8%) even though
   the generator plants no interaction at all.

   I am **not** changing H4, because rule 2 says training data may not be used to
   rewrite a hypothesis. The holdout result for H4 should be read with this in mind,
   and a better design (a baseline that also takes out week of year, or comparing
   promo and non-promo days inside the same week) is listed as a next step.

3. **Why H5 is a fair test here.** Promotions run Monday to Friday, so nearly every
   "day after a promo" is a Saturday. Because the baseline is per weekday, that
   Saturday is compared with a normal Saturday, not with a Friday, which is what keeps
   H5 from simply measuring "Saturdays are different".
