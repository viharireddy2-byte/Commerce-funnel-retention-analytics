# Validation

The 29-test automated suite passes in the clean locked environment and covers legacy model outputs and dashboard controls; revenue identity conflicts, duplicate purchases, refunds and timezone boundaries; aggregate-query equivalence and bounded exports; quality thresholds and freshness; idempotent input publication and failed-batch rollback; empty/malformed schemas; statistical boundary cases; and BigQuery exporter dry-run, streaming and interrupted-write behavior using a mocked client.

Install the tested Python 3.12 dependency set with `python -m pip install -r requirements.lock.txt`, then run `python -m pytest -q`. CI additionally tests compatible dependency resolution on Python 3.10–3.12. The lock records a clean Linux/Python 3.12 environment; use requirements-dev.txt for other supported interpreters and validate a platform-specific lock before deployment.

Measured workload evidence covers 102,028 and 1,000,000 synthetic events, including peak process memory and four shared-engine readers. These are SQL/service workload profiles, not full HTTP load tests. The 50M target is supported by the generator but has no recorded execution evidence.

The BigQuery adapter has offline contract tests. A credentialed cloud round-trip is not included in these results. Use a dry run first and validate actual exports before operating against live analytics data.
