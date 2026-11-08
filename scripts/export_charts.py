"""Export browser-viewable charts without requiring a browser or image driver."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import plotly.express as px
from sql.data_engine import DataEngine,ROOT
with DataEngine() as engine:
    summary=engine.query('SELECT * FROM fct_funnel_summary')
    cohort=engine.query('SELECT * FROM fct_cohort_retention')
    charts={'device_funnel':px.bar(summary,x='device_category',y=['visitors','cart_adders','checkout_starters','purchasers'],barmode='group'),
            'cohort_retention':px.imshow(cohort.pivot(index='cohort_month',columns='month_number',values='user_retention_rate'),text_auto='.1%',aspect='auto'),
            'revenue_retention':px.imshow(cohort.pivot(index='cohort_month',columns='month_number',values='revenue_retention_rate'),text_auto='.1%',aspect='auto')}
    for name,figure in charts.items():figure.write_html(ROOT/'images'/f'{name}.html',include_plotlyjs=True)
