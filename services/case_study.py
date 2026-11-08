"""Confounding and sensitivity analysis on one first-cart observation per user."""
from math import sqrt

class CaseStudy:
    def __init__(self, engine):
        self.engine = engine

    def observations(self, grouping='traffic_medium'):
        expressions={'traffic_medium':'traffic_medium',
            'acquisition_month':"strftime(session_start_time,'%Y-%m')",
            'session_month':"strftime(session_start_time,'%Y-%m')",
            'latency_band':"CASE WHEN avg_page_load_time_ms IS NULL THEN 'unknown' WHEN avg_page_load_time_ms<2000 THEN '<2s' ELSE '>=2s' END"}
        if grouping not in expressions:
            raise ValueError('Unsupported grouping')
        return self.engine.query(f'''WITH first_cart AS (
            SELECT *,ROW_NUMBER() OVER(PARTITION BY user_pseudo_id ORDER BY session_start_time,session_id) rn
            FROM int_funnel_stages WHERE has_added_to_cart=1
        ) SELECT device_category,{expressions[grouping]} stratum,COUNT(*) users,
            SUM(has_checkout) checkouts,AVG(has_checkout) conversion
            FROM first_cart WHERE rn=1 AND device_category IN ('mobile','desktop')
            GROUP BY 1,2 ORDER BY 2,1''')

    def standardized_gap(self, minimum_users=30):
        if minimum_users<1:
            raise ValueError('minimum_users must be positive')
        frame=self.observations()
        eligible=[]
        for key,part in frame.groupby('stratum',dropna=False):
            by={r.device_category:r for r in part.itertuples()}
            if set(by)=={'mobile','desktop'} and min(r.users for r in by.values())>=minimum_users:
                eligible.append(by)
        total=sum(sum(r.users for r in by.values()) for by in eligible)
        if total==0:
            return {'common_strata':0,'eligible_users':0,'gap':None,'ci_lower':None,'ci_upper':None}
        rates={'mobile':0.,'desktop':0.};variance=0.
        for by in eligible:
            weight=sum(r.users for r in by.values())/total
            for device,r in by.items():
                rates[device]+=weight*r.conversion
                variance+=weight**2*r.conversion*(1-r.conversion)/r.users
        gap=rates['mobile']-rates['desktop'];margin=1.95996398454*sqrt(variance)
        return {'common_strata':len(eligible),'eligible_users':int(total),
                'standardized_mobile':rates['mobile'],'standardized_desktop':rates['desktop'],
                'gap':gap,'ci_lower':max(-1.,gap-margin),'ci_upper':min(1.,gap+margin)}
