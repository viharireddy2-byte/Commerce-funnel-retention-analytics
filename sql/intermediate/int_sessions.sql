SELECT user_pseudo_id, session_id, MIN(event_time) session_start_time,
MAX(event_time) session_end_time, FIRST(device_category ORDER BY event_time, device_category) device_category,
FIRST(traffic_medium ORDER BY event_time, traffic_medium) traffic_medium,
FIRST(traffic_source ORDER BY event_time, traffic_source) traffic_source,
COUNT(*) total_events,
ROW_NUMBER() OVER(PARTITION BY user_pseudo_id ORDER BY MIN(event_time), session_id) session_sequence_number
FROM stg_ga4__events WHERE session_id IS NOT NULL AND user_pseudo_id IS NOT NULL
GROUP BY user_pseudo_id, session_id
