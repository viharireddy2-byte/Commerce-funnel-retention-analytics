# Deployment and operation

1. Provision Python 3.11, 4 GB RAM for initial sample evaluation, and writable temporary disk. This is an initial configuration, not a capacity guarantee.
2. Install `requirements.txt` in a virtual environment. Keep a deployment-specific lockfile after validating your target platform; some inherited dependency ranges remain intentionally compatible.
3. Provide a schema-compatible Parquet path or glob through `COMMERCE_DATA_PATH`. Keep analytics exports outside the Git checkout. Avoid placing credentials in environment files committed to Git.
4. Start `streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true`.
5. Restrict access with host authentication and TLS. A single process serves a shared dataset snapshot; there is no tenant isolation.
6. Check `/_stcore/health` and open all six dashboard tabs. Run the test suite and benchmark against representative inputs before increasing workload.

## Refresh and recovery

The engine owns an in-memory snapshot. Replace the configured input atomically, then use **Reload dataset** or restart the service. Do not overwrite a Parquet file while a process reads it. Roll back by restoring the prior input and restarting. There are no persistent database migrations or write endpoints.

DuckDB is configured for four threads and a 2 GB query memory limit. That limit is not a process RSS cap. Pandas frames, Arrow exports, Streamlit caches, and model materialization require additional memory. Full session downloads and diagnostics can become large. The 50M-event generator is a load fixture; deployment at that scale requires end-to-end profiling, including startup and concurrent sessions. Diagnostic samples and SQL-side chart aggregation bound dashboard transfers. Model construction still needs separate capacity validation at larger volumes.

## Validation

`python -m pytest -q` checks modeled data, key isolation, temporal eligibility, multi-purchase revenue, zero-activity retention months, M0 denominator correctness and statistical boundaries. CI runs Python 3.10, 3.11 and 3.12. Synthetic significance checks validate the included fixture only. BigQuery integration needs real credentials and is not a CI claim.

For incidents inspect the startup error, configured path, schema, permissions, dataset size and available disk. Missing sessions and duplicate candidates are surfaced in the data-quality tab; they are not silently repaired. Freshness is shown as first/last observed timestamps, without an invented SLA.

## Quality gates and input publication

Run `scripts/monitor.py --thresholds config/quality_thresholds.json` from a host scheduler or deployment check. It emits JSON and exits 1 for failed gates or an empty dataset. Optional `--max-age-hours` applies a freshness SLA; historical fixtures should leave it unset. Query errors are logged with elapsed time. Configure Python logging at DEBUG to capture successful query timings; SQL parameters are not logged on success.

`services.ingestion.publish_batch` copies a new batch into immutable content-addressed storage, validates the combined snapshot and atomically replaces its manifest. It uses an exclusive local publisher lock. Failed candidates can remain unreferenced on disk but are never visible to readers through the active manifest. Clean up unreferenced files only after comparing them with all retained manifests/backups. After a publisher crash, verify no publisher process is active before manually removing `.publish.lock`. Atomic rename and lock guarantees assume a local filesystem; network/object stores need a different publication adapter.

Back up each manifest before publishing if historical rollback is needed. Restore a known manifest atomically and rerun/restart the dashboard. Input files referenced by a manifest must remain immutable and available. Updates append source files; full SQL snapshots rebuild on refresh. Identical files are skipped by SHA-256; overlapping files are not automatically event-deduplicated.

## Access and resource boundaries

Set `COMMERCE_ACCESS_PASSWORD` through the host secret manager for the optional shared-workspace gate. Sessions expire after one hour or when the password changes; users can sign out. This gate provides neither multi-user authorization, audit identity, brute-force protection nor tenant isolation. Use host SSO, TLS and rate limiting for externally accessible deployments.

Optional audit, sensitivity and health workbenches execute when their controls are enabled. Charts aggregate in SQL; cart distributions use a stable sample of at most 10,000 sessions; export previews are 1,000 rows. Full in-dashboard exports are retained below 50,000 sessions. Use the streamed complete-export command above that size. Immutable snapshots, a bounded resource cache and input metadata fingerprints support refresh. The single shared engine serializes queries, so concurrent users can queue.

Prefer `requirements.lock.txt` on the tested Linux/Python 3.12 platform. Run `python -m pip check` after installation. The compatible-range file remains available for Python 3.10/3.11; validate those environments independently.
