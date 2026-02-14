-- Params:
--   $1 start_date (YYYY-MM-DD)
--   $2 end_date   (YYYY-MM-DD)

-- SLA targets by service level
WITH cfg AS (
  SELECT * FROM (VALUES
    ('standard'::text, 5::int),
    ('expedited'::text, 3::int),
    ('overnight'::text, 1::int)
  ) v(service_level, sla_days)
),
base AS (
  SELECT s.carrier,
         s.service_level,
         s.shipped_ts,
         s.delivered_ts,
         CASE
           WHEN s.shipped_ts IS NULL OR s.delivered_ts IS NULL THEN NULL
           ELSE extract(epoch from (s.delivered_ts - s.shipped_ts)) / 86400.0
         END AS transit_days
  FROM shipments s
  WHERE s.shipped_ts >= $1::date
    AND s.shipped_ts < ($2::date + interval '1 day')
    AND s.status IN ('delivered','returned')
),
agg AS (
  SELECT b.carrier,
         b.service_level,
         count(*) AS shipments,
         percentile_cont(0.5) within group (order by b.transit_days) AS p50_days,
         percentile_cont(0.9) within group (order by b.transit_days) AS p90_days,
         avg(b.transit_days) AS avg_days
  FROM base b
  WHERE b.transit_days IS NOT NULL
  GROUP BY 1,2
),
breaches AS (
  SELECT b.carrier,
         b.service_level,
         count(*) FILTER (WHERE b.transit_days > c.sla_days) AS sla_breaches
  FROM base b
  JOIN cfg c USING(service_level)
  WHERE b.transit_days IS NOT NULL
  GROUP BY 1,2
)
SELECT a.carrier,
       a.service_level,
       a.shipments,
       round(a.p50_days::numeric, 2) AS p50_transit_days,
       round(a.p90_days::numeric, 2) AS p90_transit_days,
       round(a.avg_days::numeric, 2) AS avg_transit_days,
       br.sla_breaches,
       round(br.sla_breaches::numeric / nullif(a.shipments,0), 4) AS sla_breach_rate
FROM agg a
JOIN breaches br USING(carrier, service_level)
ORDER BY sla_breach_rate DESC, a.shipments DESC;
