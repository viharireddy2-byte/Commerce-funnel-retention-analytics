"""Measure build, chart-query workload, peak memory and shared-reader contention."""
import argparse,json,platform,statistics,sys,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import DataEngine
from services.analytics import AnalyticsService

def workload(engine):
    s=AnalyticsService(engine);d=['mobile','desktop','tablet']
    return [len(s.segments(d,'device_category')),len(s.segments(d,'traffic_medium')),
      len(s.session_page(d,1000)),len(s.cart_sample(d)),len(s.timing(d)),len(s.latency(d)),
      len(engine.query('SELECT * FROM fct_cohort_retention'))]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='docs/workload-profile.json');p.add_argument('--clients',type=int,default=4);p.add_argument('--repeats',type=int,default=3);a=p.parse_args()
    if min(a.clients,a.repeats)<1:p.error('clients and repeats must be positive')
    start=time.perf_counter()
    with DataEngine() as e:
        build=time.perf_counter()-start
        events=int(e.query('SELECT COUNT(*) FROM raw_ga4_events').iloc[0,0])
        sessions=int(e.query('SELECT COUNT(*) FROM int_funnel_stages').iloc[0,0])
        sequential=[]
        for _ in range(a.repeats):
            t=time.perf_counter();sizes=workload(e);sequential.append(time.perf_counter()-t)
        def reader(_):
            t=time.perf_counter();workload(e);return time.perf_counter()-t
        t=time.perf_counter()
        with ThreadPoolExecutor(max_workers=a.clients) as pool:concurrent=list(pool.map(reader,range(a.clients)))
        wall=time.perf_counter()-t
    try:
        import resource
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss_bytes=int(rss if sys.platform=='darwin' else rss*1024)
    except ImportError:rss_bytes=None
    result={'python':platform.python_version(),'platform':platform.platform(),'events':events,
      'sessions':sessions,'build_seconds':build,'sequential_workload_seconds':sequential,
      'median_workload_seconds':statistics.median(sequential),'returned_frame_rows':sizes,
      'concurrent_clients':a.clients,'concurrent_wall_seconds':wall,'concurrent_client_seconds':concurrent,
      'peak_process_rss_bytes':rss_bytes,
      'scope':'Default chart SQL, bounded sample and export page; excludes browser rendering, optional audit panels, ingestion and HTTP concurrency. Shared engine serializes queries. OS caches uncontrolled.'}
    Path(a.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
