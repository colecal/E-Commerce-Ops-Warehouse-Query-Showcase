-- Params:
--   $1 start_date (YYYY-MM-DD)
--   $2 end_date   (YYYY-MM-DD)

WITH category_orders AS (
  SELECT p.category,
         count(distinct o.order_id) AS orders_with_category,
         sum(oi.quantity) AS units_sold
  FROM orders o
  JOIN order_items oi ON oi.order_id=o.order_id
  JOIN products p ON p.product_id=oi.product_id
  WHERE o.status IN ('paid','shipped','delivered','refunded')
    AND o.order_ts >= $1::date
    AND o.order_ts < ($2::date + interval '1 day')
  GROUP BY 1
),
category_refunds AS (
  SELECT p.category,
         count(distinct r.order_id) AS refunded_orders,
         sum(r.amount)::numeric(12,2) AS refund_amount
  FROM refunds r
  JOIN order_items oi ON oi.order_id=r.order_id
  JOIN products p ON p.product_id=oi.product_id
  WHERE r.refund_ts >= $1::date
    AND r.refund_ts < ($2::date + interval '1 day')
  GROUP BY 1
)
SELECT co.category,
       co.orders_with_category,
       co.units_sold,
       coalesce(cr.refunded_orders,0) AS refunded_orders,
       coalesce(cr.refund_amount,0)::numeric(12,2) AS refund_amount,
       round(coalesce(cr.refunded_orders,0)::numeric / nullif(co.orders_with_category,0), 4) AS refund_order_rate
FROM category_orders co
LEFT JOIN category_refunds cr USING(category)
ORDER BY refund_order_rate DESC, co.units_sold DESC;
