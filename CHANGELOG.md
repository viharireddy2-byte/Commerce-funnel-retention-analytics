# Implementation changes

## Commerce Funnel & Retention Analytics

- Retained Python/SQL, nested Parquet, DuckDB, Streamlit, Plotly, SciPy, Jupyter and the staging/intermediate/mart folder structure.
- Centralized executable SQL in the model files instead of maintaining separate dashboard and engine definitions.
- Enforced chronological within-session progression and preserved composite user/session identity.
- Replaced maximum-value revenue proxies with summed purchase-event revenue; labeled purchase-event denominators explicitly.
- Corrected revenue retention to use acquisition-month revenue, added calendar offsets and observed zero-activity months.
- Added first-cart-session-per-user diagnostics, reusable Wilson intervals, sample-size calculations and guards for insufficient chi-square samples.
- Replaced fixed numerical conclusions with computed summaries and explicitly labeled experiment hypotheses.
- Added parameter-bound device filters, data-quality inspection, CSV downloads and explicit empty-state handling.
- Added materialized model snapshots, serialized connection access and measured view-versus-table benchmarks. Materialization changes execution strategy within the same DuckDB architecture; it does not add a new storage service.
- Added bounded-chunk, exact-size synthetic load generation and a bounded BigQuery-to-Parquet export utility. Cloud import is explicit, rather than an unimplemented automatic live-mode fallback.
- Added metric contracts, operations guidance, reproducible notebook generation and interactive chart exports.

## Additional analytical and operational modules

- Added SQL-side chart aggregation, deterministic samples, paginated previews and streamed full exports; retained all six original dashboard tabs and small-dataset complete downloads.
- Added an independent audited revenue ledger for transaction identities, duplicate/conflicting payloads, partial refunds, per-currency totals and timezone-specific daily reporting. Original KPI semantics are unchanged.
- Added quality thresholds, freshness diagnostics, JSON monitoring output and validation-gated atomic batch manifests with file-level idempotence.
- Added input metadata refresh detection, a bounded engine-resource cache, optional shared-workspace access sessions and query timing/error logging.
- Added a common-stratum sensitivity workbench, reproducible case study and synthetic transaction reconciliation fixture.
- Added measured 1M-event workload/memory/shared-reader evidence, a clean Python 3.12 dependency lock, exporter contract tests and additional edge-case tests.
