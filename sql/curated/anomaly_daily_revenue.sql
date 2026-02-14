-- Params:
--   $1 start_date (YYYY-MM-DD)
--   $2 end_date   (YYYY-MM-DD)

WITH order_revenue AS (
  SELECT o.order_id,
         date_trunc('day', o.order_ts)::date AS day,
         (sum(oi.quantity*oi.unit_price - oi.discount) + o.shipping_cost)::numeric(12,2) AS revenue
  FROM orders o
  JOIN order_items oi ON oi.order_id=o.order_id
  WHERE o.status IN ('paid','shipped','delivered','refunded')
    AND o.order_ts >= $1::date
    AND o.order_ts < ($2::date + interval '1 day')
  GROUP BY 1,2, o.shipping_cost
),
daily AS (
  SELECT day, sum(revenue)::numeric(12,2) AS revenue
  FROM order_revenue
  GROUP BY 1
),
stats AS (
  SELECT day,
         revenue,
         avg(revenue) OVER (ORDER BY day ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS mean_28d,
         stddev_samp(revenue) OVER (ORDER BY day ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS sd_28d
  FROM daily
)
SELECT day,
       revenue,
       round(mean_28d, 2) AS trailing_mean_28d,
       round(sd_28d, 2) AS trailing_sd_28d,
       CASE
         WHEN sd_28d IS NULL OR sd_28d = 0 THEN NULL
         ELSE round((revenue - mean_28d) / sd_28d, 2)
       END AS z_score
FROM stats
ORDER BY day;
