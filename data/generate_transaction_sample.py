"""Create an explicit synthetic transaction-audit demo without changing the default sample."""
import argparse,copy,random
from pathlib import Path
import pandas as pd

def generate(source, destination, seed=42):
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    rows=pd.read_parquet(source).to_dict('records');extra=[];rng=random.Random(seed)
    for index,row in enumerate(rows):
        params=[copy.deepcopy(p) for p in row['event_params']]
        row['event_params']=params
        if row['event_name']!='purchase':continue
        txn=f'synthetic-transaction-{index}'
        def param(key,text=None,value=None):
            return {'key':key,'value':{'string_value':text,'int_value':None,'double_value':value}}
        params.extend([param('transaction_id',txn),param('currency','USD'),param('event_id',f'synthetic-event-{index}')])
        if rng.random()<.03:extra.append(copy.deepcopy(row))
        if rng.random()<.1:
            refund=copy.deepcopy(row);refund['event_name']='refund'
            amount=next(p['value']['double_value'] for p in params if p['key']=='value')
            refund['event_params']=[p for p in refund['event_params'] if p['key'] not in ('value','event_id')]
            refund['event_params'].extend([param('value',value=amount/2),param('event_id',f'synthetic-refund-{index}')])
            extra.append(refund)
    destination.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows+extra).to_parquet(destination,index=False)
    return len(rows)+len(extra)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='data/ga4_sample_events.parquet');p.add_argument('--output',default='data/commerce_transaction_events.parquet');a=p.parse_args()
    print(f'Wrote {generate(a.source,a.output):,} synthetic events')
if __name__=='__main__':main()
