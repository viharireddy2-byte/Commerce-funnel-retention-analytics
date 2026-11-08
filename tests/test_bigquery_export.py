from unittest.mock import Mock
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from scripts.export_bigquery import export

def test_dry_run_bounds_and_no_write(tmp_path):
    client=Mock();client.query.return_value.total_bytes_processed=123
    target=tmp_path/'events.parquet'
    result=export(client,'20201101','20201102',target,1000)
    config=client.query.call_args.kwargs['job_config']
    assert config.dry_run and config.maximum_bytes_billed==1000
    assert [p.value for p in config.query_parameters]==['20201101','20201102']
    assert result['estimated_bytes']==123 and not target.exists()
    client.query.return_value.result.assert_not_called()

def test_streamed_export_and_cleanup(tmp_path):
    client=Mock();job=client.query.return_value;job.total_bytes_processed=456
    batch=pa.record_batch({'value':[1,2]})
    job.result.return_value.to_arrow_iterable.return_value=iter([batch,batch])
    target=tmp_path/'good.parquet'
    assert export(client,'20201101','20201102',target,1000,True)['rows']==4
    assert pq.read_table(target).num_rows==4
    def broken():
        yield batch
        raise RuntimeError('stream interrupted')
    job.result.return_value.to_arrow_iterable.return_value=broken()
    failed=tmp_path/'failed.parquet'
    with pytest.raises(RuntimeError):export(client,'20201101','20201102',failed,1000,True)
    assert not failed.exists()
    assert list(tmp_path.iterdir())==[target]
    with pytest.raises(ValueError):export(client,'20201103','20201102',failed)
