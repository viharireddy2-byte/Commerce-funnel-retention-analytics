"""Build a clean, executable analytical narrative without stale cell output."""
from pathlib import Path
import nbformat as n
root=Path(__file__).resolve().parents[1]
nb=n.v4.new_notebook()
nb.cells=[
n.v4.new_markdown_cell('# Commerce Funnel & Retention Analytics\n\nA reproducible investigation of ordered checkout progression, segment differences, and repeat activity. The bundled dataset is synthetic; observed patterns are generator behavior, not customer research.'),
n.v4.new_code_cell("from pathlib import Path\nimport sys\nROOT = Path.cwd() if (Path.cwd()/'sql').exists() else Path.cwd().parent\nsys.path.insert(0,str(ROOT))\nfrom sql.data_engine import DataEngine\nfrom sql.statistics import wilson_interval, sample_size\nimport plotly.express as px\nengine = DataEngine()"),
n.v4.new_markdown_cell('## Validate the measurement contract\nFunnel counts represent ordered sessions. Revenue includes every purchase event; no transaction deduplication is possible without an authoritative identifier.'),
n.v4.new_code_cell('from sql.quality import quality_report\nquality_report(engine)'),
n.v4.new_code_cell("summary = engine.query('SELECT * FROM fct_funnel_summary')\nsummary"),
n.v4.new_code_cell("px.bar(summary, x='device_category', y='visitors', color='traffic_medium', title='Viewing sessions by device and source')"),
n.v4.new_markdown_cell('## Compare acquisition cohorts\nUse actual calendar offsets, include zero-activity months, and leave future months blank. Interpret the latest partial calendar month cautiously.'),
n.v4.new_code_cell("cohort = engine.query('SELECT * FROM fct_cohort_retention')\npx.imshow(cohort.pivot(index='cohort_month',columns='month_number',values='user_retention_rate'), text_auto='.1%', aspect='auto')"),
n.v4.new_code_cell("px.imshow(cohort.pivot(index='cohort_month',columns='month_number',values='revenue_retention_rate'), text_auto='.1%', aspect='auto')"),
n.v4.new_markdown_cell('## Plan a test\nA two-sided fixed-horizon design with 80% power and 5% significance. Randomize users, check allocation imbalance, and protect purchase conversion and revenue per assigned user. Observational device differences do not identify checkout latency as a cause.'),
n.v4.new_code_cell("sample_size(baseline=.414, absolute_lift=.05)"),
n.v4.new_markdown_cell('## Composition sensitivity and transaction auditing\nUse one first-cart observation per user, compare common traffic strata, and audit transaction identities separately from event-revenue KPIs.'),
n.v4.new_code_cell("from services.case_study import CaseStudy\nstudy = CaseStudy(engine)\nstudy.observations()"),
n.v4.new_code_cell('study.standardized_gap()'),
n.v4.new_code_cell("from services.revenue import RevenueService\nRevenueService(engine).reconciliation()"),
n.v4.new_code_cell("from services.monitoring import monitor\nmonitor(engine)"),
n.v4.new_code_cell('engine.close()')]
nb.metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}}
n.write(nb,root/'notebooks/commerce_funnel_retention.ipynb')
