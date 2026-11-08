WITH first_touch AS (
 SELECT user_pseudo_id,date_trunc('month',MIN(event_time)) cohort_month FROM stg_ga4__events GROUP BY 1
), monthly AS (
 SELECT user_pseudo_id,date_trunc('month',event_time) activity_month,
 SUM(CASE WHEN event_name='purchase' THEN COALESCE(event_value,0) ELSE 0 END) revenue
 FROM stg_ga4__events GROUP BY 1,2
), sizes AS (
 SELECT f.cohort_month,COUNT(*) cohort_size,SUM(m.revenue) cohort_initial_revenue
 FROM first_touch f JOIN monthly m ON f.user_pseudo_id=m.user_pseudo_id AND f.cohort_month=m.activity_month GROUP BY 1
), activity AS (
 SELECT f.cohort_month, m.activity_month,COUNT(*) retained_users,SUM(m.revenue) retained_revenue
 FROM first_touch f JOIN monthly m USING(user_pseudo_id) GROUP BY 1,2
), offsets AS (
 SELECT s.*,r.i month_number,s.cohort_month + r.i*INTERVAL '1 month' activity_month
 FROM sizes s CROSS JOIN range(0,1+date_diff('month',s.cohort_month,(SELECT MAX(activity_month) FROM monthly))) r(i)
)
SELECT o.cohort_month,o.cohort_size,o.cohort_initial_revenue,o.month_number,o.activity_month,
COALESCE(a.retained_users,0) retained_users,COALESCE(a.retained_revenue,0) retained_revenue,
COALESCE(a.retained_users,0)*1.0/o.cohort_size user_retention_rate,
COALESCE(a.retained_revenue,0)/NULLIF(o.cohort_initial_revenue,0) revenue_retention_rate
FROM offsets o LEFT JOIN activity a USING(cohort_month,activity_month) ORDER BY 1,4
