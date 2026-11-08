# Data contract and interfaces

Input: nested GA4-style Parquet, resolved from `COMMERCE_DATA_PATH` or the bundled file. Dates are event dates; timestamps are UTC epoch microseconds. No local timezone conversion or currency conversion is applied.

| Field | Type | Meaning |
|---|---|---|
| event_date | string YYYYMMDD | Source calendar date |
| event_timestamp | integer | UTC epoch microseconds |
| event_name | string | page_view, view_item, add_to_cart, begin_checkout, purchase or other event |
| user_pseudo_id | string | Pseudonymous user identifier |
| device | struct | category and operating_system |
| traffic_source | struct | medium and source |
| event_params | list of structs | key, value.int_value, value.double_value, value.string_value |

Parameter keys: `ga_session_id`, `page_title`, `value`, `page_load_time_ms`. Session ID is numeric; page load time is milliseconds. Monetary values must use one consistent currency. A missing optional parameter becomes null. Duplicate parameter keys use the first source-list entry. Required nested structures must be present; malformed schema fails startup visibly.

| Model | Grain | Key outputs |
|---|---|---|
| stg_ga4__events | source event | event_time, session_id, event_value, page_load_time_ms, segment fields |
| int_sessions | user/session | start/end, event count, deterministic first device and source, session sequence |
| int_funnel_stages | user/session | ordered timestamps, four stage flags, cart_value, purchase_events, purchase_revenue |
| fct_funnel_summary | device/medium | session stage counts, conditional rates, recorded purchase revenue |
| fct_cohort_retention | acquisition month/age month | cohort size, actual M0 revenue, retained users/revenue and rates |
| fct_funnel_diagnostics | user/session | ordered stages, hour/day, cart outcome, recorded load time |

Cart value is the maximum recorded add-to-cart value in the session; it is an observed event-value proxy, not a reconstructed item-level cart balance. Purchases before a view or checkout remain in revenue but do not qualify as ordered conversions. Repeated purchase events are counted separately; transaction IDs are absent from the local contract.

Python entry points: `DataEngine`, `get_engine`, `query`, `get_parquet_path` in `sql/data_engine.py`; `quality_report(engine)` returns check names and affected-row counts; `wilson_interval(k,n)`, `compare_groups(table)`, `sample_size(baseline,absolute_lift,alpha=.05,power=.8)` support statistical diagnostics. Empty Wilson samples return `(None,None)`; invalid success counts raise `ValueError`; unsuitable chi-square tables return `None`.

Keep SQL inputs trusted. Bind user-provided filter values using `?` parameters. Rates with zero denominators are null. The dashboard displays N/A for undefined headline rates. SQL files execute in dependency order; changes apply when the engine is reconstructed.

## Optional transaction audit contract

The additive `fct_revenue_ledger` reads `transaction_id`, `currency`, `event_id` and `value` from nested event parameters. The BigQuery exporter additionally copies `ecommerce.transaction_id` into parameters when absent. Original funnel models and event-revenue totals are unchanged.

- Purchase identity: a globally unique transaction ID within the input workspace. Refund identity: a globally unique refund event ID, linked to its transaction ID. Scope input by merchant/workspace if IDs are not globally unique.
- Currency is uppercased and must have a three-letter format. There is no ISO currency lookup or FX conversion. Different currencies remain separate.
- Repeated identical operation identities retain one accepted row; extra copies are `duplicate`. Conflicting amount, transaction or currency payloads are excluded as `conflicting_identity`.
- Missing timestamps/transaction IDs/currency, nonfinite or invalid values and missing refund event IDs are excluded. Refunds without an accepted purchase in the observed dataset are `unmatched_refund`; total accepted refund candidates exceeding purchase amount are `excess_refund`. Amounts are nonnegative source values; refunds receive a negative signed amount.
- Valid identities do not prove source completeness. An out-of-window purchase can cause a refund to be unmatched. Partial refunds require distinct refund event IDs. These rules are unsuitable for transaction revisions unless source revisions are reconciled first.
- `RevenueService.daily(timezone)` interprets event timestamps as UTC and converts to the requested IANA timezone before deriving a date. Monetary arithmetic uses source double precision; this is an analytics ledger, not a financial accounting system.

`AnalyticsService` provides summary, validated dimension grouping, deterministic cart samples (max 10,000), timing/latency summaries and stable session pages (max 10,000). The dashboard retains full downloads up to 50,000 sessions; larger full exports use `scripts/export_sessions.py`.

`CaseStudy` uses one first-cart observation per user. The `session_month` grouping refers to eligible session month. The adjusted gap standardizes mobile and desktop to a common pooled traffic-medium mix with at least 30 users/device/stratum. Its normal interval conditions on fixed weights; this is observational evidence, not causal adjustment for every confounder.
