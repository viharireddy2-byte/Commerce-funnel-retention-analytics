-- Independent audit ledger: legacy funnel/revenue models remain unchanged.
WITH enriched AS (
 SELECT *,
 (SELECT param.value.string_value FROM UNNEST(event_params) t(param) WHERE param.key='transaction_id' LIMIT 1) transaction_id,
 (SELECT param.value.string_value FROM UNNEST(event_params) t(param) WHERE param.key='currency' LIMIT 1) currency,
 (SELECT param.value.string_value FROM UNNEST(event_params) t(param) WHERE param.key='event_id' LIMIT 1) event_id,
 (SELECT COALESCE(param.value.double_value,param.value.int_value::DOUBLE) FROM UNNEST(event_params) t(param) WHERE param.key='value' LIMIT 1) amount
 FROM raw_ga4_events WHERE event_name IN ('purchase','refund')
), identified AS (
 SELECT *,nullif(trim(transaction_id),'') tid,upper(nullif(trim(currency),'')) ccy,
 CASE WHEN event_name='purchase' THEN transaction_id ELSE event_id END operation_id
 FROM enriched
), signatures AS (
 SELECT *,
 CASE WHEN event_name='purchase' THEN tid ELSE nullif(trim(event_id),'') END dedup_id
 FROM identified
), audited AS (
 SELECT *,
 COUNT(*) OVER(PARTITION BY event_name,dedup_id) copies,
 MIN(amount) OVER(PARTITION BY event_name,dedup_id) min_amount,
 MAX(amount) OVER(PARTITION BY event_name,dedup_id) max_amount,
 COUNT(DISTINCT tid) OVER(PARTITION BY event_name,dedup_id) transaction_variants,
 COUNT(DISTINCT ccy) OVER(PARTITION BY event_name,dedup_id) currency_variants,
 COUNT(*) FILTER(WHERE ccy IS NULL OR amount IS NULL) OVER(PARTITION BY event_name,dedup_id) missing_payload,
 ROW_NUMBER() OVER(PARTITION BY event_name,dedup_id ORDER BY event_timestamp,user_pseudo_id,amount,ccy) copy_number
 FROM signatures
), classified AS (
SELECT make_timestamp(event_timestamp::BIGINT) event_time,event_name,user_pseudo_id,
 tid transaction_id,ccy currency,event_id,amount,
 CASE
 WHEN tid IS NULL THEN 'missing_transaction_id'
 WHEN ccy IS NULL THEN 'missing_currency'
 WHEN NOT regexp_full_match(ccy,'[A-Z]{3}') THEN 'invalid_currency'
 WHEN event_timestamp IS NULL THEN 'missing_timestamp'
 WHEN amount IS NULL OR NOT isfinite(amount) OR amount<0 THEN 'invalid_amount'
 WHEN dedup_id IS NULL THEN 'missing_refund_event_id'
 WHEN min_amount<>max_amount OR currency_variants>1 OR transaction_variants>1 OR missing_payload>0 THEN 'conflicting_identity'
 WHEN copy_number>1 THEN 'duplicate'
 ELSE 'accepted' END base_status,
 CASE WHEN event_name='refund' THEN -amount ELSE amount END signed_amount
FROM audited
), purchases AS (
 SELECT transaction_id,currency,amount FROM classified WHERE base_status='accepted' AND event_name='purchase'
), refund_totals AS (
 SELECT transaction_id,currency,SUM(amount) amount FROM classified
 WHERE base_status='accepted' AND event_name='refund' GROUP BY 1,2
)
SELECT c.* EXCLUDE(base_status), CASE
 WHEN c.base_status<>'accepted' THEN c.base_status
 WHEN c.event_name='refund' AND p.transaction_id IS NULL THEN 'unmatched_refund'
 WHEN c.event_name='refund' AND r.amount>p.amount THEN 'excess_refund'
 ELSE 'accepted' END status
FROM classified c LEFT JOIN purchases p USING(transaction_id,currency)
LEFT JOIN refund_totals r USING(transaction_id,currency)
