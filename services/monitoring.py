"""Configurable quality gates and freshness diagnostics."""
from datetime import datetime, timezone
import pandas as pd
from sql.quality import quality_report

DEFAULT_THRESHOLDS = {'missing user': 0, 'missing session': 0,
    'negative purchase value': 0, 'funnel order violation': 0, 'retention outside bounds': 0, 'missing timestamp': 0}

def monitor(engine, thresholds=None, max_age_hours=None, now=None):
    thresholds = DEFAULT_THRESHOLDS if thresholds is None else thresholds
    if any(not isinstance(v, (int,float)) or v < 0 for v in thresholds.values()):
        raise ValueError('Thresholds must be nonnegative numbers')
    if max_age_hours is not None and max_age_hours < 0:
        raise ValueError('Freshness limit must be nonnegative')
    checks = quality_report(engine)
    checks.append({'check':'missing timestamp','affected_rows':int(engine.query('SELECT COUNT(*) FROM stg_ga4__events WHERE event_time IS NULL').iloc[0,0])})
    known = {c['check'] for c in checks}
    if set(thresholds)-known:
        raise ValueError('Unknown quality check: ' + ', '.join(sorted(set(thresholds)-known)))
    for row in checks:
        row['threshold'] = thresholds.get(row['check'])
        row['status'] = ('observed' if row['threshold'] is None else
                         'pass' if row['affected_rows'] <= row['threshold'] else 'fail')
    data = engine.query('SELECT COUNT(*) events,MAX(event_time) latest FROM stg_ga4__events').iloc[0]
    latest = None if int(data.events)==0 or pd.isna(data.latest) else data.latest
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('now must be timezone-aware')
    age = None if latest is None else (now-latest.to_pydatetime().replace(tzinfo=timezone.utc)).total_seconds()/3600
    freshness_ok = max_age_hours is None or (age is not None and 0 <= age <= max_age_hours)
    passed = int(data.events)>0 and freshness_ok and not any(c['status']=='fail' for c in checks)
    return {'passed':passed,'events':int(data.events),'latest_event':None if latest is None else latest.isoformat(),
            'age_hours':age,'max_age_hours':max_age_hours,'freshness_passed':freshness_ok,'checks':checks}
