-- Params:
--   $1 start_month (YYYY-MM-01)
--   $2 end_month   (YYYY-MM-01)

WITH first_order AS (
  SELECT customer_id,
         date_trunc('month', min(order_ts))::date AS cohort_month
  FROM orders
  WHERE status IN ('paid','shipped','delivered','refunded')
  GROUP BY 1
),
orders_by_month AS (
  SELECT o.customer_id,
         date_trunc('month', o.order_ts)::date AS order_month
  FROM orders o
  WHERE o.status IN ('paid','shipped','delivered','refunded')
),
cohort_activity AS (
  SELECT f.cohort_month,
         obm.order_month,
         (extract(year from age(obm.order_month, f.cohort_month)) * 12
          + extract(month from age(obm.order_month, f.cohort_month)))::int AS month_n,
         count(distinct obm.customer_id) AS active_customers
  FROM first_order f
  JOIN orders_by_month obm
    ON obm.customer_id = f.customer_id
  WHERE f.cohort_month BETWEEN $1::date AND $2::date
    AND obm.order_month >= f.cohort_month
  GROUP BY 1,2,3
),
cohort_sizes AS (
  SELECT cohort_month, count(*) AS cohort_size
  FROM first_order
  WHERE cohort_month BETWEEN $1::date AND $2::date
  GROUP BY 1
)
SELECT a.cohort_month,
       a.month_n,
       s.cohort_size,
       a.active_customers,
       round(a.active_customers::numeric / nullif(s.cohort_size,0), 4) AS retention_rate
FROM cohort_activity a
JOIN cohort_sizes s USING (cohort_month)
WHERE a.month_n BETWEEN 0 AND 12
ORDER BY a.cohort_month, a.month_n;
