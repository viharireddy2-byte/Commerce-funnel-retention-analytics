"""Emit machine-readable quality status; exit 1 when configured gates fail."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import DataEngine
from services.monitoring import monitor

def main():
    p=argparse.ArgumentParser();p.add_argument('--thresholds',default=None);p.add_argument('--max-age-hours',type=float);p.add_argument('--output')
    a=p.parse_args()
    thresholds=None if a.thresholds is None else json.loads(Path(a.thresholds).read_text())
    with DataEngine() as e:
        report=monitor(e,thresholds,a.max_age_hours)
    body=json.dumps(report,indent=2)
    if a.output:Path(a.output).write_text(body+'\n')
    print(body)
    return 0 if report['passed'] else 1
if __name__=='__main__':sys.exit(main())
