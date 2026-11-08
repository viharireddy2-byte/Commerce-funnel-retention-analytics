from pathlib import Path
import pandas as pd
import pytest
import duckdb
from sql.data_engine import DataEngine
from sql.statistics import wilson_interval,compare_groups,sample_size

@pytest.fixture
def edge(tmp_path):
    # Microseconds since epoch; same session id for different users must remain isolated.
    entries=[('a',1,'2024-01-01','purchase',9),('a',1,'2024-01-02','page_view',None),
      ('a',1,'2024-01-03','add_to_cart',20),('a',1,'2024-01-04','begin_checkout',None),
      ('a',1,'2024-01-05','purchase',10),('a',1,'2024-01-06','purchase',15),
      ('b',1,'2024-01-01','page_view',None),('a',2,'2024-03-01','purchase',30),
      ('b',2,'2024-03-01','page_view',None)]
    rows=[]
    for user,sid,day,name,val in entries:
        rows.append(dict(event_date=day.replace('-',''),event_timestamp=int(pd.Timestamp(day).timestamp()*1e6),event_name=name,user_pseudo_id=user,
          device={'category':'mobile','operating_system':'test'},traffic_source={'medium':'organic','source':'test'},
          event_params=[{'key':'ga_session_id','value':{'int_value':sid,'double_value':None,'string_value':None}},
                        {'key':'value','value':{'int_value':None,'double_value':val,'string_value':None}}]))
    frame=pd.DataFrame(rows);path=tmp_path/'events.parquet'
    frame.to_parquet(path,index=False)
    with DataEngine(path) as engine:yield engine

def test_revenue_and_identity(edge):
    s=edge.query('SELECT * FROM int_funnel_stages WHERE session_id=1 ORDER BY user_pseudo_id')
    assert len(s)==2
    assert s.iloc[0].purchase_revenue==34 # all purchase events, including pre-funnel purchase
    assert s.iloc[0].has_purchased==1
    assert s.iloc[1].has_purchased==0
    assert len(edge.query('SELECT * FROM int_sessions'))==4

def test_no_funnel_for_purchase_without_view(edge):
    row=edge.query("SELECT * FROM int_funnel_stages WHERE user_pseudo_id='a' AND session_id=2").iloc[0]
    assert row.has_purchased==0 and row.purchase_revenue==30

def test_retention_baseline_and_zero_month(edge):
    rows=edge.query('SELECT * FROM fct_cohort_retention ORDER BY month_number')
    assert list(rows.month_number)==[0,1,2]
    assert rows.iloc[0].cohort_initial_revenue==34
    assert rows.iloc[0].revenue_retention_rate==1
    assert rows.iloc[1].retained_users==0
    assert rows.iloc[2].revenue_retention_rate==pytest.approx(30/34)

def test_statistics_boundaries():
    assert wilson_interval(0,0)==(None,None)
    assert wilson_interval(0,10)[0]==0
    assert wilson_interval(10,10)[1]==1
    with pytest.raises(ValueError):wilson_interval(11,10)
    assert compare_groups([[0,10],[0,10]]) is None
    assert compare_groups([[1,1],[1,1]]) is None
    assert compare_groups([[50,50],[50,50]])['p_value']==1
    assert 1500<sample_size(.414,.05)<1600
    with pytest.raises(ValueError):sample_size(.98,.05)
