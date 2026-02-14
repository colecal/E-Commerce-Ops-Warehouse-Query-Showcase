-- Params:
--   $1 start_date (YYYY-MM-DD)
--   $2 end_date   (YYYY-MM-DD)

WITH base AS (
  SELECT *
  FROM web_events
  WHERE event_ts >= $1::date
    AND event_ts < ($2::date + interval '1 day')
),
sessions AS (
  SELECT count(distinct session_id) AS n
  FROM base
  WHERE event_type = 'session_start'
),
views AS (
  SELECT count(distinct session_id) AS n
  FROM base
  WHERE event_type = 'product_view'
),
adds AS (
  SELECT count(distinct session_id) AS n
  FROM base
  WHERE event_type = 'add_to_cart'
),
checkouts AS (
  SELECT count(distinct session_id) AS n
  FROM base
  WHERE event_type = 'checkout_start'
),
purchases AS (
  SELECT count(distinct session_id) AS n
  FROM base
  WHERE event_type = 'purchase'
),
sessions_n AS (
  SELECT (SELECT n FROM sessions) AS sessions
)
SELECT stage,
       n,
       round(n::numeric / nullif(sn.sessions,0), 4) AS pct_of_sessions
FROM (
  SELECT 'sessions' AS stage, (SELECT n FROM sessions) AS n, 1 AS ord
  UNION ALL SELECT 'product_view', (SELECT n FROM views), 2
  UNION ALL SELECT 'add_to_cart', (SELECT n FROM adds), 3
  UNION ALL SELECT 'checkout_start', (SELECT n FROM checkouts), 4
  UNION ALL SELECT 'purchase', (SELECT n FROM purchases), 5
) s
CROSS JOIN sessions_n sn
ORDER BY ord;
