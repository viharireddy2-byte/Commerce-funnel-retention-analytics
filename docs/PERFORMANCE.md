# Performance measurements

## Repeated summary query

`python scripts/benchmark.py` compares the same funnel-summary query using lazy views and materialized models. The retained `benchmark.json` records startup separately, five query samples, runtime versions and input count. It checks result equivalence with a floating-point tolerance. This demonstrates the benefit of precomputation, not an equivalent full-application speedup.

## Workload and memory profile

`python scripts/profile_workload.py` measures construction, default SQL-backed chart reads, a bounded 10,000-session cart sample, a 1,000-row export page and four shared-engine readers. It excludes browser rendering, optional audit panels, ingestion and HTTP load. The engine serializes connection access. OS cache state is uncontrolled; these local timings are not service-level guarantees.

| Events | Sessions | Model build | Median chart-query workload | Peak process RSS | Four-reader wall time |
|---|---:|---:|---:|---:|---:|
| 102,028 | 39,836 | 1.912 s | 0.046 s | 467 MiB | 0.187 s |
| 1,000,000 | 390,454 | 16.155 s | 0.110 s | 1,915 MiB | 0.420 s |

See `workload-sample.json` and `workload-1m.json` for exact observations and individual samples. Both profiles used Python 3.12.14 in the same Linux execution environment. The 1M input replicates the sample with isolated identities; it is load-testing data, not independent behavioral observations. Peak RSS includes the whole process, and the DuckDB memory setting is not an RSS cap.

## Reproduce

```bash
python scripts/profile_workload.py --output docs/workload-sample.json
python scripts/scale_dataset.py --events 1000000 --output data/scale-1m
COMMERCE_DATA_PATH='data/scale-1m/*.parquet' python scripts/profile_workload.py --output docs/workload-1m.json
```

The generator supports a 50M-event target, but no 50M runtime, memory or latency result is asserted. Large deployments still require representative source cardinalities, complete dashboard HTTP/browser load, and host-specific capacity validation. ZSTD and row-group sizing are implemented; date partition pruning and incremental SQL mart maintenance are not claimed.
