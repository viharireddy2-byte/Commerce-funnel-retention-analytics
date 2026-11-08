"""Bounded dashboard reads; aggregation stays inside DuckDB."""
class AnalyticsService:
    STAGES = ['has_viewed', 'has_added_to_cart', 'has_checkout', 'has_purchased']

    def __init__(self, engine):
        self.engine = engine

    def _where(self, devices):
        if not devices:
            return 'FALSE', []
        if any(d not in ('mobile', 'desktop', 'tablet') for d in devices):
            raise ValueError('Unsupported device')
        return 'device_category IN (' + ','.join('?' for _ in devices) + ')', list(devices)

    def summary(self, devices):
        where, params = self._where(devices)
        sums = ','.join(f'COALESCE(SUM({c}),0) {c}' for c in self.STAGES)
        return self.engine.query(f'''SELECT COUNT(*) sessions, {sums},
            COALESCE(SUM(purchase_revenue),0) revenue,
            COALESCE(SUM(purchase_events),0) orders
            FROM int_funnel_stages WHERE {where}''', params).iloc[0]

    def segments(self, devices, dimension):
        if dimension not in ('device_category', 'traffic_medium', 'traffic_source'):
            raise ValueError('Unsupported dimension')
        where, params = self._where(devices)
        sums = ','.join(f'SUM({c}) {c}' for c in self.STAGES)
        return self.engine.query(f'''SELECT {dimension}, {sums}
            FROM int_funnel_stages WHERE {where} GROUP BY 1 ORDER BY 1''', params)

    def session_page(self, devices, limit=1000, offset=0):
        if not 1 <= limit <= 10000 or offset < 0:
            raise ValueError('Require limit 1..10000 and nonnegative offset')
        where, params = self._where(devices)
        return self.engine.query(f'''SELECT * FROM int_funnel_stages WHERE {where}
            ORDER BY session_start_time,user_pseudo_id,session_id LIMIT ? OFFSET ?''',
            params + [limit, offset])

    def cart_sample(self, devices, limit=10000):
        if not 1 <= limit <= 10000:
            raise ValueError('Sample limit must be 1..10000')
        where, params = self._where(devices)
        # Stable hash ordering makes repeated chart samples reproducible.
        return self.engine.query(f'''SELECT cart_value,device_category,
            CASE WHEN has_purchased=1 THEN 'Completed' ELSE 'Abandoned' END outcome
            FROM int_funnel_stages WHERE {where} AND has_added_to_cart=1 AND cart_value>0
            ORDER BY hash(user_pseudo_id,session_id) LIMIT ?''', params + [limit])

    def timing(self, devices):
        where, params = self._where(devices)
        sums = ','.join(f'SUM({c}) {c}' for c in self.STAGES)
        return self.engine.query(f'''SELECT EXTRACT(hour FROM session_start_time) AS "hour",
            {sums} FROM int_funnel_stages WHERE {where} GROUP BY 1 ORDER BY 1''', params)

    def latency(self, devices):
        where, params = self._where(devices)
        return self.engine.query(f'''SELECT device_category,
            median(avg_page_load_time_ms) median, AVG(avg_page_load_time_ms) mean,
            quantile_cont(avg_page_load_time_ms,.95) p95,
            COUNT(avg_page_load_time_ms) count
            FROM int_funnel_stages WHERE {where} GROUP BY 1 ORDER BY 1''', params)
