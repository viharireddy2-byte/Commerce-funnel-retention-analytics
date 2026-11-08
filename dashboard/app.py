"""Interactive commerce analytics workbench."""
import sys
import glob
import os
import pandas as pd
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sql.data_engine import DataEngine,get_parquet_path
from sql.statistics import wilson_interval,compare_groups,sample_size
from sql.quality import quality_report
st.set_page_config(page_title='Commerce Funnel & Retention Analytics',layout='wide')
from services.access import require_access
require_access(st)
st.title('Commerce Funnel & Retention Analytics')
st.caption('Checkout progression • acquisition cohorts • experiment planning')
@st.cache_resource(max_entries=1)
def load(path, fingerprint=None):
    return DataEngine(None if os.getenv('COMMERCE_MANIFEST_PATH') else path)
try:
    path=get_parquet_path()
    manifest=os.getenv('COMMERCE_MANIFEST_PATH')
    files=[manifest] if manifest else sorted(glob.glob(path))
    fingerprint=tuple((p,os.stat(p).st_mtime_ns,os.stat(p).st_size) for p in files)
    engine=load(path,fingerprint)
except Exception as exc:
    st.error(f'Dataset could not be loaded: {exc}')
    st.stop()
if st.sidebar.button('Reload dataset'):
    load.clear(); st.rerun()
metadata=engine.query('SELECT COUNT(*) events,COUNT(DISTINCT user_pseudo_id) users,MIN(event_time) first_event,MAX(event_time) last_event FROM stg_ga4__events').iloc[0]
st.sidebar.caption(f'Local DuckDB | {metadata.events:,} events | {metadata.users:,} users')
st.sidebar.caption(f'{metadata.first_event} through {metadata.last_event}')
devices=st.sidebar.multiselect('Devices',['mobile','desktop','tablet'],default=['mobile','desktop','tablet'])
if not devices:
    st.info('Select at least one device.'); st.stop()
marks=','.join('?' for _ in devices)
from services.analytics import AnalyticsService
analytics=AnalyticsService(engine)
summary=analytics.summary(devices)
if not summary.sessions:
    st.info('No matching sessions.'); st.stop()
cols=['has_viewed','has_added_to_cart','has_checkout','has_purchased']
counts=[int(summary[c]) for c in cols]
revenue=float(summary.revenue); orders=int(summary.orders)
values=[f'{counts[0]:,}',f'{counts[2]/counts[1]:.1%}' if counts[1] else 'N/A',f'{counts[3]/counts[0]:.1%}' if counts[0] else 'N/A',f'${revenue/orders:,.2f}' if orders else 'N/A',f'${revenue:,.0f}']
for col,label,value in zip(st.columns(5),['Viewing sessions','Cart → checkout','View → purchase','Revenue / purchase event','Recorded revenue'],values):
    col.metric(label,value)
st.caption('Funnel unit: ordered sessions. Equal timestamps qualify. Revenue includes all purchase events, including those outside the ordered funnel.')
tabs=st.tabs(['Executive funnel','Segments','Retention','Diagnostics','Experiment planner','Data quality'])
with tabs[0]:
    st.plotly_chart(go.Figure(go.Funnel(y=['View','Cart','Checkout','Purchase'],x=counts,textinfo='value+percent previous')),use_container_width=True)
    losses=[counts[i]-counts[i+1] for i in range(3)]; biggest=max(range(3),key=losses.__getitem__)
    st.write(f"Largest absolute loss: {['View → cart','Cart → checkout','Checkout → purchase'][biggest]}, {losses[biggest]:,} sessions.")
    page=st.number_input('Session export page (1,000 rows per page)',min_value=1,max_value=max(1,(int(summary.sessions)+999)//1000),value=1)
    session_page=analytics.session_page(devices,limit=1000,offset=(page-1)*1000)
    st.download_button('Download current session page',session_page.to_csv(index=False),'funnel_sessions_page.csv','text/csv')
    if int(summary.sessions)<=50000:
        complete=pd.concat([analytics.session_page(devices,10000,offset)
                            for offset in range(0,int(summary.sessions),10000)],ignore_index=True)
        st.download_button('Download funnel sessions',complete.to_csv(index=False),'funnel_sessions.csv','text/csv')
    else:
        st.info('For a complete export above 50,000 sessions, use the streamed export command documented below.')
    st.caption('Downloads are paginated to bound memory. Use scripts/export_sessions.py for a complete streamed CSV export.')
with tabs[1]:
    for dim in ['device_category','traffic_medium']:
        grouped=analytics.segments(devices,dim)
        st.subheader(dim.replace('_',' ').title())
        st.plotly_chart(px.bar(grouped,x=dim,y=cols,barmode='group'),use_container_width=True)
        st.dataframe(grouped,use_container_width=True)
with tabs[2]:
    st.caption('All-device cohorts; device filters affect session charts only. Latest calendar month is partial. Future months are absent; observed inactive months are zero.')
    cohort=engine.query('SELECT * FROM fct_cohort_retention')
    metric=st.radio('Metric',['user_retention_rate','revenue_retention_rate'],horizontal=True)
    if not cohort.empty:
        st.plotly_chart(px.imshow(cohort.pivot(index='cohort_month',columns='month_number',values=metric),text_auto='.1%',aspect='auto'),use_container_width=True)
    st.caption('First observed activity defines acquisition. Revenue retention compares against actual acquisition-month revenue; this is not subscription NDR.')
    st.download_button('Download cohorts',cohort.to_csv(index=False),'cohort_retention.csv','text/csv')
with tabs[3]:
    st.subheader('Mobile vs desktop: first cart session per user')
    evidence=engine.query('''WITH ranked AS (
        SELECT *,ROW_NUMBER() OVER(PARTITION BY user_pseudo_id ORDER BY session_start_time,session_id) rn
        FROM int_funnel_stages WHERE has_added_to_cart=1
    ) SELECT device_category,COUNT(*) trials,SUM(has_checkout) successes FROM ranked
    WHERE rn=1 AND device_category IN ('mobile','desktop') GROUP BY 1 ORDER BY 1''')
    rows=[]; table=[]
    for r in evidence.itertuples():
        lo,hi=wilson_interval(r.successes,r.trials)
        rows.append(dict(device=r.device_category,users=r.trials,conversion=r.successes/r.trials,lower_95=lo,upper_95=hi))
        table.append([r.successes,r.trials-r.successes])
    st.dataframe(rows,use_container_width=True)
    result=compare_groups(table)
    if result:
        st.write(f"Chi-square p-value: {result['p_value']:.3g}. " + ('Association detected at α=.05.' if result['p_value']<.05 else 'Insufficient evidence at α=.05.'))
    else:
        st.info('Insufficient expected cell counts for chi-square inference.')
    st.caption('Comparison uses all mobile/desktop users. Observational association does not establish causality.')
    carts=analytics.cart_sample(devices)
    st.caption('Cart distributions use a stable sample of at most 10,000 sessions.')
    if not carts.empty:
        st.plotly_chart(px.box(carts,x='outcome',y='cart_value',color='device_category',points=False),use_container_width=True)
    timing=analytics.timing(devices).set_index('hour')
    st.plotly_chart(px.imshow(timing.T,aspect='auto',labels={'x':'Session start hour','y':'Stage','color':'Sessions'}),use_container_width=True)
    st.dataframe(analytics.latency(devices))
with tabs[4]:
    st.write('Hypothesis: simplifying mobile checkout increases cart-to-checkout conversion. Confirm causes with instrumentation and user-level randomization.')
    baseline=st.number_input('Baseline conversion',min_value=.01,max_value=.98,value=.41,step=.01)
    lift=st.number_input('Minimum detectable absolute lift',min_value=.001,max_value=.5,value=.05,step=.005)
    daily=st.number_input('Eligible unique users per day (both arms)',min_value=1,value=500)
    if baseline+lift<1:
        n=sample_size(baseline,lift)
        st.metric('Required users per arm',f'{n:,}')
        st.write(f'Plan at least {max(14,-(-2*n//daily))} days, with two weekly cycles. 50/50 split, two-sided α=.05, power=.80, normal approximation, fixed horizon.')
    else:
        st.warning('Baseline plus lift must be below one.')
    st.write('Primary metric: eligible assigned users reaching checkout / eligible assigned cart users. Guardrails: purchase conversion, revenue per assigned user, payment errors and p95 latency. Check sample-ratio mismatch; avoid repeated significance checks. No realized business lift is claimed.')
with tabs[5]:
    st.dataframe(quality_report(engine),use_container_width=True)
    st.caption('Duplicate candidates are flagged, not deleted. An authoritative event or transaction ID is required for reliable deduplication.')

# Additional workbenches keep the original six tabs and metric contracts intact.
with st.expander('Revenue reconciliation'):
    if st.checkbox('Load transaction audit'):
        from services.revenue import RevenueService
        ledger=RevenueService(engine)
        st.caption('Audited transaction metrics are separate from the original event-revenue KPIs. Missing identities and conflicts are excluded; currencies are never summed together.')
        st.dataframe(ledger.reconciliation(),use_container_width=True)
        tz=st.selectbox('Revenue reporting timezone',['UTC','America/New_York','America/Chicago','Europe/London'])
        st.dataframe(ledger.daily(tz),use_container_width=True)

with st.expander('Segment sensitivity analysis'):
    if st.checkbox('Run segment sensitivity'):
        from services.case_study import CaseStudy
        study=CaseStudy(engine)
        dim=st.selectbox('Sensitivity grouping',['traffic_medium','session_month','latency_band'])
        st.dataframe(study.observations(dim),use_container_width=True)
        adjusted=study.standardized_gap()
        st.write(adjusted)
        st.caption('Adjusted gap: mobile minus desktop, standardized to the pooled traffic-medium mix in common strata with at least 30 users/device. Normal confidence interval conditions on fixed weights. This is an association; unmeasured confounding and selection remain.')

with st.expander('Operational health'):
    if st.checkbox('Run operational checks'):
        from services.monitoring import monitor
        health=monitor(engine)
        st.write({k:v for k,v in health.items() if k!='checks'})
        st.dataframe(health['checks'],use_container_width=True)
