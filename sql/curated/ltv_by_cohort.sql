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
order_revenue AS (
  SELECT o.order_id,
         o.customer_id,
         date_trunc('month', o.order_ts)::date AS order_month,
         (sum(oi.quantity*oi.unit_price - oi.discount) + o.shipping_cost)::numeric(12,2) AS revenue
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status IN ('paid','shipped','delivered','refunded')
  GROUP BY 1,2,3, o.shipping_cost
),
cohort_orders AS (
  SELECT f.cohort_month,
         r.customer_id,
         r.order_month,
         (extract(year from age(r.order_month, f.cohort_month)) * 12
          + extract(month from age(r.order_month, f.cohort_month)))::int AS month_n,
         r.revenue
  FROM first_order f
  JOIN order_revenue r ON r.customer_id = f.customer_id
  WHERE f.cohort_month BETWEEN $1::date AND $2::date
    AND r.order_month >= f.cohort_month
),
cohort_monthly AS (
  SELECT cohort_month, month_n,
         sum(revenue) AS cohort_revenue,
         count(distinct customer_id) AS customers
  FROM cohort_orders
  WHERE month_n BETWEEN 0 AND 12
  GROUP BY 1,2
),
cohort_cume AS (
  SELECT cohort_month, month_n,
         sum(cohort_revenue) OVER (PARTITION BY cohort_month ORDER BY month_n) AS cume_revenue,
         max(customers) OVER (PARTITION BY cohort_month) AS cohort_customers
  FROM cohort_monthly
)
SELECT cohort_month,
       month_n,
       cohort_customers,
       round(cume_revenue / nullif(cohort_customers,0), 2) AS avg_cumulative_ltv
FROM cohort_cume
ORDER BY cohort_month, month_n;
