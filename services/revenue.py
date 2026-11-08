"""Transaction audit reporting, separate from original event-revenue metrics."""
from zoneinfo import ZoneInfo

class RevenueService:
    def __init__(self, engine):
        self.engine = engine

    def reconciliation(self):
        return self.engine.query('''SELECT currency,event_name,status,COUNT(*) events,
            SUM(signed_amount) signed_amount FROM fct_revenue_ledger
            GROUP BY 1,2,3 ORDER BY 1,2,3''')

    def daily(self, timezone='UTC'):
        ZoneInfo(timezone)  # Validate an IANA timezone before SQL execution.
        return self.engine.query('''SELECT
            CAST(timezone(?,timezone('UTC',event_time)) AS DATE) local_date,
            currency,SUM(CASE WHEN event_name='purchase' THEN amount ELSE 0 END) gross_revenue,
            SUM(CASE WHEN event_name='refund' THEN amount ELSE 0 END) refunds,
            SUM(signed_amount) net_revenue
            FROM fct_revenue_ledger WHERE status='accepted' GROUP BY 1,2 ORDER BY 1,2''', [timezone])
