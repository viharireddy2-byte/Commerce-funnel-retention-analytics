"""Compare lazy SQL views and one-time materialized models on identical input."""
import argparse,json,sys,time,platform,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import DataEngine
p=argparse.ArgumentParser();p.add_argument('--output',default='docs/benchmark.json');p.add_argument('--repeats',type=int,default=5);a=p.parse_args()
if a.repeats<1: p.error('--repeats must be positive')
sql='SELECT * FROM fct_funnel_summary ORDER BY device_category,traffic_medium'
results={};frames=[]
for mode in [False,True]:
    start=time.perf_counter()
    with DataEngine(materialize=mode) as e:
        startup=time.perf_counter()-start
        runs=[]
        for _ in range(a.repeats):
            t=time.perf_counter();frame=e.query(sql);runs.append(time.perf_counter()-t)
        frames.append(frame)
        results['materialized' if mode else 'views']={'startup_seconds':startup,'query_median_seconds':statistics.median(runs),'query_seconds':runs}
        count=int(e.query('SELECT COUNT(*) FROM raw_ga4_events').iloc[0,0])
from pandas.testing import assert_frame_equal
assert_frame_equal(frames[0],frames[1],check_exact=False,rtol=1e-10,atol=1e-8)
import duckdb
payload={'python':platform.python_version(),'duckdb':duckdb.__version__,'platform':platform.platform(),'events':count,'repeats':a.repeats,'cache':'same-process repeated query; OS cache uncontrolled','results':results}
Path(a.output).write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(payload,indent=2))
