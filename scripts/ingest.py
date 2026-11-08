"""Publish a schema-compatible Parquet batch into a versioned input manifest."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services.ingestion import publish_batch

def main():
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--directory',required=True);p.add_argument('--thresholds');p.add_argument('--max-age-hours',type=float)
    a=p.parse_args();thresholds=None if a.thresholds is None else json.loads(Path(a.thresholds).read_text())
    print(json.dumps(publish_batch(a.source,a.directory,thresholds,a.max_age_hours),indent=2))
if __name__=='__main__':main()
