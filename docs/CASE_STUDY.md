# Checkout progression: segment sensitivity case study

## Decision and measurement

Question: does the observed device gap persist after holding traffic-medium mix constant, and what evidence would justify a checkout experiment?

The bundled data is synthetic. These findings describe generation assumptions and demonstrate an analytical method; they are not customer research findings or realized business impact. Rerun against a consented real export before making a product decision.

Unit: each user's first observed cart session. Outcome: an ordered checkout within that session. Users without a cart session are outside this estimand. Device and medium come from that session. Repeated sessions are not treated as independent users.

## Observed conversion

| Device | Eligible unique users | Checkout users | Conversion |
|---|---:|---:|---:|
| desktop | 3,272 | 1,907 | 58.28% |
| mobile | 5,598 | 1,795 | 32.07% |

## Composition sensitivity

Traffic-standardized mobile minus desktop gap: **-26.23 percentage points**, approximate 95% interval **[-28.31, -24.14]**. 8,870 users across 5 common traffic strata contribute.

Weights represent the pooled medium mix across common strata with at least 30 users/device. The normal interval conditions on fixed weights. Excluded small/nonoverlapping strata limit generalization. Adjusted and unadjusted estimates use different population weights.

## Alternative explanations

- **Traffic composition:** inspect case-study-traffic.csv and the adjusted result. Disappearance of the gap after standardization would support acquisition mix as an explanation.
- **Calendar effects:** case-study-month.csv uses first eligible cart-session month, not true acquisition. Inspect stability across observed months.
- **Recorded load time:** case-study-latency.csv uses broad bands of session-average event load time, not checkout-specific latency or Core Web Vitals. Network, intent and device can confound this relationship.
- **Measurement loss:** blocked instrumentation, missing identifiers, late events, cross-device users and truncated sessions may bias denominators. Quality checks cannot detect all of these.
- **Revenue:** event revenue can contain duplicates. Use the separate accepted-transaction ledger for revenue reconciliation and keep currencies separate; do not extrapolate checkout conversion directly into annual revenue.

## Recommendation and falsification

Validate source completeness on real traffic and instrument step-level form errors and checkout-specific latency. If the gap persists within comparable sources and months, randomize eligible users to checkout simplification. Prespecify the MDE and fixed horizon; protect purchase conversion, net revenue per assigned user and payment errors. Check allocation ratios before inference.

Evidence that weakens the recommendation includes disappearance after traffic/calendar adjustment, differential event loss, insufficient overlap, or a randomized result excluding a practically important lift. The synthetic gap does not establish causality.

## Reproduce

Run `python scripts/analyze_case_study.py`. Supporting CSVs and adjusted JSON are generated from SQL; numerical conclusions are computed from the configured dataset.
