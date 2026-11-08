SELECT *, EXTRACT(dow FROM session_start_time) day_of_week,
EXTRACT(hour FROM session_start_time) hour_of_day,
CASE WHEN has_purchased=1 THEN 'Completed' WHEN has_added_to_cart=1 THEN 'Abandoned' ELSE 'No Cart' END cart_outcome
FROM int_funnel_stages
