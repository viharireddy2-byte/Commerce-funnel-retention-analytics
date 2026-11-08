"""Create an exact-size synthetic load fixture from the bundled sample, in bounded chunks.
Identity replication preserves per-user behavior; this is not independent behavioral evidence.
"""
import argparse,sys,json
from pathlib import Path
import duckdb
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import get_parquet_path
p=argparse.ArgumentParser();p.add_argument('--events',type=int,default=50_000_000);p.add_argument('--output',default='data/scale');p.add_argument('--chunk-size',type=int,default=1_000_000);a=p.parse_args()
if min(a.events,a.chunk_size)<1:p.error('sizes must be positive')
out=Path(a.output)
if out.exists():p.error('Output must not exist; refusing to mix datasets')
out.mkdir(parents=True)
con=duckdb.connect();con.execute("SET memory_limit='2GB'");con.read_parquet(get_parquet_path()).create_view('source')
con.execute('CREATE TABLE base AS SELECT row_number() OVER() - 1 AS idx,* FROM source')
size=con.execute('SELECT COUNT(*) FROM base').fetchone()[0]
if not size:raise ValueError('Source is empty')
for start in range(0,a.events,a.chunk_size):
    end=min(a.events,start+a.chunk_size)
    con.execute('''CREATE OR REPLACE TEMP TABLE batch AS SELECT b.* EXCLUDE(idx,user_pseudo_id),
      b.user_pseudo_id || '_replica_' || CAST(g.i // ? AS VARCHAR) user_pseudo_id
      FROM range(?,?) g(i) JOIN base b ON b.idx=g.i % ?''',[size,start,end,size])
    # Generated filenames are controlled integers, never external SQL fragments.
    target=str((out/f'part-{start:012d}.parquet').resolve()).replace("'","''")
    con.execute(f"COPY batch TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 122880)")
    print(f'{end:,}/{a.events:,}',flush=True)
(out/'manifest.json').write_text(json.dumps({'events':a.events,'behavior':'replicated sample with isolated user IDs; final replica can be truncated','compression':'zstd','row_group_target':122880},indent=2))
