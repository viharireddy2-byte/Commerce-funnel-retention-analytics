"""Bounded, dry-run-first BigQuery import with streamed atomic Parquet output."""
import argparse
import os
import tempfile
from pathlib import Path
from datetime import datetime
from google.cloud import bigquery

SQL = '''SELECT event_date,event_timestamp,event_name,user_pseudo_id,device,traffic_source,
ARRAY_CONCAT(event_params,
 IF(ecommerce.transaction_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM UNNEST(event_params) p WHERE p.key='transaction_id'),
 [STRUCT('transaction_id' AS key, STRUCT(ecommerce.transaction_id AS string_value,
    CAST(NULL AS INT64) AS int_value,CAST(NULL AS FLOAT64) AS float_value,
    CAST(NULL AS FLOAT64) AS double_value) AS value)], [])) AS event_params
FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
WHERE _TABLE_SUFFIX BETWEEN @start AND @end'''

def export(client, start, end, destination, maximum_bytes_billed=1_000_000_000, execute=False):
    for date in (start,end):datetime.strptime(date,'%Y%m%d')
    if start>end or maximum_bytes_billed<1:
        raise ValueError('Invalid date range or billing cap')
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    params=[bigquery.ScalarQueryParameter('start','STRING',start),bigquery.ScalarQueryParameter('end','STRING',end)]
    config=bigquery.QueryJobConfig(query_parameters=params,dry_run=not execute,
        use_query_cache=False,maximum_bytes_billed=maximum_bytes_billed)
    job=client.query(SQL,job_config=config)
    if not execute:
        return {'dry_run':True,'estimated_bytes':job.total_bytes_processed,'rows':0}
    import pyarrow.parquet as pq
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(dir=destination.parent,suffix='.parquet');os.close(fd)
    writer=None;count=0
    try:
        for batch in job.result().to_arrow_iterable(bqstorage_client=None):
            if writer is None:writer=pq.ParquetWriter(name,batch.schema,compression='zstd')
            writer.write_batch(batch);count+=batch.num_rows
        if writer is None:raise ValueError('Query returned no batches; no output published')
        writer.close();writer=None
        with open(name,'rb') as f:os.fsync(f.fileno())
        os.replace(name,destination)
        return {'dry_run':False,'processed_bytes':job.total_bytes_processed,'rows':count}
    finally:
        if writer is not None:writer.close()
        Path(name).unlink(missing_ok=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--start',required=True);p.add_argument('--end',required=True)
    p.add_argument('--billing-project',required=True);p.add_argument('--output',default='data/bigquery_events.parquet')
    p.add_argument('--maximum-bytes-billed',type=int,default=1_000_000_000);p.add_argument('--execute',action='store_true');a=p.parse_args()
    print(export(bigquery.Client(project=a.billing_project),a.start,a.end,a.output,a.maximum_bytes_billed,a.execute))
if __name__=='__main__':main()
