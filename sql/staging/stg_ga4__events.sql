SELECT event_date, make_timestamp(event_timestamp::BIGINT) AS event_time,
 event_name, user_pseudo_id, device.category AS device_category,
 device.operating_system AS operating_system,
 traffic_source.medium AS traffic_medium, traffic_source.source AS traffic_source,
 (SELECT param.value.int_value FROM UNNEST(event_params) t(param) WHERE param.key='ga_session_id' LIMIT 1) AS session_id,
 (SELECT param.value.string_value FROM UNNEST(event_params) t(param) WHERE param.key='page_title' LIMIT 1) AS page_title,
 (SELECT COALESCE(param.value.double_value, param.value.int_value::DOUBLE) FROM UNNEST(event_params) t(param) WHERE param.key='value' LIMIT 1) AS event_value,
 (SELECT param.value.int_value FROM UNNEST(event_params) t(param) WHERE param.key='page_load_time_ms' LIMIT 1) AS page_load_time_ms
FROM raw_ga4_events
