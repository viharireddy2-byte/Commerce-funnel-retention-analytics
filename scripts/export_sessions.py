"""Complete session CSV export in bounded pages, with atomic publication."""
import argparse,csv,os,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sql.data_engine import DataEngine
from services.analytics import AnalyticsService

def export(engine, destination, devices, page_size=10000):
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    name=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',newline='',encoding='utf-8',dir=destination.parent,delete=False) as f:
            name=Path(f.name);offset=0
            while True:
                page=AnalyticsService(engine).session_page(devices,page_size,offset)
                if offset==0:page.to_csv(f,index=False)
                elif len(page):page.to_csv(f,index=False,header=False)
                if len(page)<page_size:break
                offset+=len(page)
            f.flush();os.fsync(f.fileno())
        os.replace(name,destination)
    finally:
        if name and name.exists():name.unlink()

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--devices',nargs='+',default=['mobile','desktop','tablet']);a=p.parse_args()
    with DataEngine() as engine:export(engine,a.output,a.devices)
if __name__=='__main__':main()
