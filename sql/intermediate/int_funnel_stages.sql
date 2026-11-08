WITH views AS (
 SELECT s.*, MIN(e.event_time) FILTER(WHERE e.event_name IN ('page_view','view_item')) first_view_time
 FROM int_sessions s JOIN stg_ga4__events e USING(user_pseudo_id,session_id) GROUP BY ALL
), carts AS (
 SELECT v.*, MIN(e.event_time) FILTER(WHERE e.event_name='add_to_cart' AND e.event_time>=first_view_time) first_cart_time
 FROM views v JOIN stg_ga4__events e USING(user_pseudo_id,session_id) GROUP BY ALL
), checkouts AS (
 SELECT c.*, MIN(e.event_time) FILTER(WHERE e.event_name='begin_checkout' AND e.event_time>=first_cart_time) first_checkout_time
 FROM carts c JOIN stg_ga4__events e USING(user_pseudo_id,session_id) GROUP BY ALL
)
SELECT c.*, MIN(e.event_time) FILTER(WHERE e.event_name='purchase' AND e.event_time>=first_checkout_time) first_purchase_time,
(first_view_time IS NOT NULL)::INT has_viewed, (first_cart_time IS NOT NULL)::INT has_added_to_cart,
(first_checkout_time IS NOT NULL)::INT has_checkout,
(first_purchase_time IS NOT NULL)::INT has_purchased,
MAX(e.event_value) FILTER(WHERE e.event_name='add_to_cart') cart_value,
COALESCE(SUM(e.event_value) FILTER(WHERE e.event_name='purchase'),0) purchase_revenue,
COUNT(*) FILTER(WHERE e.event_name='purchase') purchase_events,
AVG(e.page_load_time_ms) avg_page_load_time_ms
FROM checkouts c JOIN stg_ga4__events e USING(user_pseudo_id,session_id) GROUP BY ALL
