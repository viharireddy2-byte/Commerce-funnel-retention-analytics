"""Local SQL analytics engine. Each instance owns its connection and model snapshot."""
import os
import threading
import time
import logging
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]

def get_parquet_path():
    return str(Path(os.getenv('COMMERCE_DATA_PATH', ROOT / 'data/ga4_sample_events.parquet')).resolve())

class DataEngine:
    def __init__(self, parquet_path=None, materialize=True):
        if parquet_path is None and os.getenv('COMMERCE_MANIFEST_PATH'):
            payload=json.loads(Path(os.environ['COMMERCE_MANIFEST_PATH']).read_text())
            parquet_path=payload['files']
        self.parquet_path = parquet_path if isinstance(parquet_path,list) else str(parquet_path or get_parquet_path())
        self._lock = threading.RLock()
        self.con = duckdb.connect(':memory:')
        try:
            self.con.execute("SET memory_limit='2GB'")
            self.con.execute('SET threads=4')
            # Relation API binds paths rather than interpolating them into SQL.
            self.con.read_parquet(self.parquet_path, hive_partitioning=True).create_view('raw_ga4_events')
            models = [('stg_ga4__events','staging/stg_ga4__events.sql'),
                      ('int_sessions','intermediate/int_sessions.sql'),
                      ('int_funnel_stages','intermediate/int_funnel_stages.sql'),
                      ('fct_funnel_summary','marts/funnel_summary.sql'),
                      ('fct_cohort_retention','marts/cohort_retention.sql'),
                      ('fct_funnel_diagnostics','marts/funnel_diagnostics.sql')]
            for name, path in models:
                kind = 'TABLE' if materialize else 'VIEW'
                self.con.execute(f'CREATE {kind} {name} AS ' + (ROOT/'sql'/path).read_text())
            self.con.execute('CREATE VIEW fct_revenue_ledger AS ' + (ROOT/'sql/marts/revenue_ledger.sql').read_text())
        except Exception:
            self.con.close()
            raise

    def query(self, sql, parameters=None):
        with self._lock:
            started = time.perf_counter()
            try:
                result = self.con.execute(sql, parameters or []).df()
                logging.getLogger(__name__).debug('query_completed rows=%d seconds=%.6f', len(result), time.perf_counter()-started)
                return result
            except Exception:
                logging.getLogger(__name__).exception('query_failed seconds=%.6f', time.perf_counter()-started)
                raise

    def close(self):
        with self._lock:
            self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

_engine = None
_engine_lock = threading.Lock()
def get_engine():
    global _engine
    with _engine_lock:
        if _engine is None:
            _engine = DataEngine()
        return _engine

def query(sql, parameters=None):
    return get_engine().query(sql, parameters)
