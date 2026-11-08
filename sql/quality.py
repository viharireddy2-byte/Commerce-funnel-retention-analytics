"""Non-destructive checks; invalid rows remain visible for diagnosis."""
def quality_report(engine):
    checks={
      'missing user': 'SELECT COUNT(*) FROM stg_ga4__events WHERE user_pseudo_id IS NULL',
      'missing session': 'SELECT COUNT(*) FROM stg_ga4__events WHERE session_id IS NULL',
      'negative purchase value': "SELECT COUNT(*) FROM stg_ga4__events WHERE event_name='purchase' AND event_value<0",
      'duplicate candidate': 'SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM stg_ga4__events GROUP BY user_pseudo_id,session_id,event_time,event_name HAVING COUNT(*)>1)',
      'funnel order violation': 'SELECT COUNT(*) FROM int_funnel_stages WHERE has_purchased>has_checkout OR has_checkout>has_added_to_cart OR has_added_to_cart>has_viewed',
      'retention outside bounds': 'SELECT COUNT(*) FROM fct_cohort_retention WHERE user_retention_rate<0 OR user_retention_rate>1'
    }
    return [{'check':name,'affected_rows':int(engine.query(sql).iloc[0,0])} for name,sql in checks.items()]
