-- Params:
--   $1 start_date (YYYY-MM-DD)
--   $2 end_date   (YYYY-MM-DD)

WITH order_revenue AS (
  SELECT o.order_id,
         date_trunc('week', o.order_ts)::date AS week,
         (sum(oi.quantity*oi.unit_price - oi.discount) + o.shipping_cost)::numeric(12,2) AS revenue
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status IN ('paid','shipped','delivered','refunded')
    AND o.order_ts >= $1::date
    AND o.order_ts < ($2::date + interval '1 day')
  GROUP BY 1,2, o.shipping_cost
),
weekly AS (
  SELECT week,
         count(*) AS orders,
         round(avg(revenue), 2) AS aov
  FROM order_revenue
  GROUP BY 1
)
SELECT week,
       orders,
       aov,
       round(avg(aov) OVER (ORDER BY week ROWS BETWEEN 3 PRECEDING AND CURRENT ROW), 2) AS aov_4wk_ma
FROM weekly
ORDER BY week;
