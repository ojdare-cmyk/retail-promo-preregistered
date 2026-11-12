# Results: sealed holdout, opened once

Holdout 2026-04-01 to 2026-06-30, 60 stores, 4,601 open store-days. Opened 2026-10-20T10:27:29.
Plan first committed: `d896797e2af18119e8e725ec31acfb09e8522a97 2026-10-20T10:22:55-07:00`.

**3 of 5 hypotheses held and 2 did not**, at a family-wise alpha of 0.05 with Holm-Bonferroni correction. Every hypothesis is listed, including the nulls.

| # | Hypothesis | Effect | 95% CI | Stores | p (raw) | p (Holm) | Wilcoxon p | Verdict | Flags |
|---|---|---|---|---|---|---|---|---|---|
| H1 | Promotions raise daily sales | +14.5% | +12.9% to +16.2% | 60 (0 dropped) | 1.4e-27 | 5.8e-27 | 8.1e-12 | **held** | none |
| H2 | Promotions raise customer traffic | +15.4% | +13.8% to +17.0% | 60 (0 dropped) | 1.2e-28 | 6e-28 | 8.1e-12 | **held** | none |
| H3 | Promotions raise basket size | -0.7% | -1.0% to -0.4% | 60 (0 dropped) | 1 | 1 | 1 | **did not hold** | none |
| H4 | Sales lift is larger during school holidays | -5.1% | -6.7% to -3.4% | 46 (14 dropped) | 1 | 1 | 1 | **did not hold** | none |
| H5 | Day after a promo sells less (pull-forward) | -2.7% | -3.9% to -1.6% | 60 (0 dropped) | 1.1e-05 | 3.3e-05 | 4.1e-05 | **held** | none |

Effect = average across stores, as a percentage. For H4 it is the extra lift inside school holidays; for H5 it is the day-after-promo gap versus other non-promo days. The CI is two-sided and not corrected; the verdict uses only the Holm p-value.
