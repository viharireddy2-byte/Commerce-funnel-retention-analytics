from datetime import datetime,timezone
import pandas as pd
import pytest
import pyarrow.parquet as pq
from sql.data_engine import DataEngine,ROOT
from services.analytics import AnalyticsService
from services.case_study import CaseStudy
from services.monitoring import monitor
from services.revenue import RevenueService
from services.ingestion import publish_batch
from scripts.export_sessions import export

@pytest.fixture
def engine():
    with DataEngine() as e:yield e

def test_aggregations_match_legacy(engine):
    service=AnalyticsService(engine)
    for devices in [['mobile'],['desktop','tablet'],[]]:
        summary=service.summary(devices)
        marks=','.join('?' for _ in devices)
        expected=engine.query(f'SELECT COUNT(*) n FROM int_funnel_stages WHERE device_category IN ({marks})' if devices else 'SELECT 0 n',devices).iloc[0,0]
        assert summary.sessions==expected
        assert len(service.session_page(devices,10000))<=10000
        assert service.segments(devices,'device_category').has_viewed.sum()==summary.has_viewed
    with pytest.raises(ValueError):service.segments(['mobile'],'bad_column')
    with pytest.raises(ValueError):service.session_page(['mobile'],10001)
    with pytest.raises(ValueError):service.summary(["mobile'); DROP TABLE int_sessions;--"])
    assert len(service.cart_sample(['mobile'],15))<=15
    assert len(service.timing(['mobile']))<=24

def test_quality_and_freshness(engine):
    assert monitor(engine,thresholds={})['passed']
    assert not monitor(engine,max_age_hours=1,now=datetime(2026,1,1,tzinfo=timezone.utc))['passed']
    with pytest.raises(ValueError):monitor(engine,{'unknown':1})
    with pytest.raises(ValueError):monitor(engine,max_age_hours=-1)

def test_transaction_ledger(tmp_path):
    base=pq.read_table(ROOT/'data/ga4_sample_events.parquet').slice(0,1).to_pylist()[0]
    rows=[]
    entries=[('purchase','a','p1',100,'USD'),('purchase','a','p1',100,'USD'),
      ('refund','a','r1',25,'USD'),('refund','a','r1',25,'USD'),
      ('purchase','b','p2',10,'EUR'),('purchase','b','p3',20,'EUR'),
      ('purchase',None,None,15,None),('refund','missing','r2',5,'USD'),
      ('purchase','c','p4',10,'GBP'),('refund','c','r3',20,'GBP')]
    for i,(name,tid,eid,value,currency) in enumerate(entries):
        row=dict(base);row['event_name']=name;row['event_timestamp']=1704070800000000+i
        params=[dict(x) for x in base['event_params'] if x['key'] not in ['value','transaction_id','currency','event_id']]
        for key,text,number in [('value',None,value),('transaction_id',tid,None),('event_id',eid,None),('currency',currency,None)]:
            params.append({'key':key,'value':{'int_value':None,'double_value':number,'string_value':text}})
        row['event_params']=params;rows.append(row)
    path=tmp_path/'transactions.parquet';pd.DataFrame(rows).to_parquet(path)
    with DataEngine(path) as e:
        ledger=e.query('SELECT * FROM fct_revenue_ledger')
        assert len(ledger)==10
        for status,n in [('duplicate',2),('conflicting_identity',2),('unmatched_refund',1),('excess_refund',1)]:
            assert (ledger.status==status).sum()==n
        daily=RevenueService(e).daily('America/New_York')
        usd=daily[daily.currency=='USD'].iloc[0]
        assert usd.net_revenue==75
        assert str(usd.local_date.date())=='2023-12-31'
        with pytest.raises(Exception):RevenueService(e).daily('Invalid/Zone')

def test_manifest_idempotence_and_failure(tmp_path,monkeypatch):
    source=tmp_path/'good.parquet';pq.write_table(pq.read_table(ROOT/'data/ga4_sample_events.parquet').slice(0,100),source)
    root=tmp_path/'store'
    assert publish_batch(source,root,thresholds={})['version']==1
    assert publish_batch(source,root,thresholds={})['status']=='already_ingested'
    original=(root/'manifest.json').read_bytes()
    bad=tmp_path/'bad.parquet';bad.write_text('invalid parquet')
    with pytest.raises(Exception):publish_batch(bad,root,thresholds={})
    assert (root/'manifest.json').read_bytes()==original
    assert not (root/'.publish.lock').exists()
    monkeypatch.setenv('COMMERCE_MANIFEST_PATH',str(root/'manifest.json'))
    with DataEngine() as e:assert len(e.query('SELECT * FROM raw_ga4_events'))==100

def test_empty_and_malformed_inputs(tmp_path):
    empty=tmp_path/'empty.parquet';pq.write_table(pq.read_table(ROOT/'data/ga4_sample_events.parquet').slice(0,0),empty)
    with DataEngine(empty) as e:
        assert not monitor(e,thresholds={})['passed']
        assert AnalyticsService(e).summary(['mobile']).sessions==0
    malformed=tmp_path/'malformed.parquet';pd.DataFrame({'a':[1]}).to_parquet(malformed)
    with pytest.raises(Exception):DataEngine(malformed)

def test_complete_export(engine,tmp_path):
    path=tmp_path/'sessions.csv';export(engine,path,['tablet'],page_size=17)
    frame=pd.read_csv(path)
    assert len(frame)==int(AnalyticsService(engine).summary(['tablet']).sessions)
    assert not frame.duplicated(['user_pseudo_id','session_id']).any()
    with pytest.raises(FileExistsError):export(engine,path,['tablet'])

def test_case_study(engine):
    study=CaseStudy(engine);report=study.standardized_gap()
    assert report['common_strata']>0
    assert -1<=report['gap']<=1
    assert report['ci_lower']<=report['gap']<=report['ci_upper']
    assert study.standardized_gap(10**9)['gap'] is None
    for grouping in ['traffic_medium','acquisition_month','latency_band']:
        data=study.observations(grouping);assert data.checkouts.le(data.users).all()
    with pytest.raises(ValueError):study.observations('bad')

def test_missing_identity_gate(tmp_path):
    table=pq.read_table(ROOT/'data/ga4_sample_events.parquet').slice(0,3)
    rows=table.to_pylist()
    rows[0]['user_pseudo_id']=None
    rows[1]['event_timestamp']=None
    path=tmp_path/'missing.parquet';pd.DataFrame(rows).to_parquet(path)
    with DataEngine(path) as e:
        result=monitor(e)
        assert not result['passed']
        failures={c['check'] for c in result['checks'] if c['status']=='fail'}
        assert 'missing user' in failures and 'missing timestamp' in failures

def test_transaction_demo():
    with DataEngine(ROOT/'data/commerce_transaction_events.parquet') as e:
        totals=RevenueService(e).daily()
        assert len(totals)>0
        assert totals.net_revenue.sum()<totals.gross_revenue.sum()
        statuses=RevenueService(e).reconciliation().status
        assert 'accepted' in statuses.values and 'duplicate' in statuses.values
