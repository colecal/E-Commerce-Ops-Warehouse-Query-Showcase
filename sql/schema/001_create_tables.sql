-- E-Commerce Ops Warehouse (Postgres)
-- Drop/recreate for demo purposes

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DROP TABLE IF EXISTS refunds CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS shipments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS web_events CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

CREATE TABLE customers (
  customer_id      BIGSERIAL PRIMARY KEY,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  email            TEXT NOT NULL UNIQUE,
  first_name       TEXT NOT NULL,
  last_name        TEXT NOT NULL,
  country          TEXT NOT NULL,
  marketing_opt_in BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE products (
  product_id   BIGSERIAL PRIMARY KEY,
  sku          TEXT NOT NULL UNIQUE,
  name         TEXT NOT NULL,
  category     TEXT NOT NULL,
  unit_price   NUMERIC(12,2) NOT NULL,
  active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE orders (
  order_id     BIGSERIAL PRIMARY KEY,
  customer_id  BIGINT NOT NULL REFERENCES customers(customer_id),
  order_ts     TIMESTAMPTZ NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('placed','paid','shipped','delivered','cancelled','refunded')),
  channel      TEXT NOT NULL CHECK (channel IN ('web','mobile','marketplace')),
  currency     TEXT NOT NULL DEFAULT 'USD',
  shipping_cost NUMERIC(12,2) NOT NULL DEFAULT 0
);
CREATE INDEX idx_orders_customer_ts ON orders(customer_id, order_ts);
CREATE INDEX idx_orders_ts ON orders(order_ts);

CREATE TABLE order_items (
  order_item_id BIGSERIAL PRIMARY KEY,
  order_id      BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  product_id    BIGINT NOT NULL REFERENCES products(product_id),
  quantity      INT NOT NULL CHECK (quantity > 0),
  unit_price    NUMERIC(12,2) NOT NULL,
  discount      NUMERIC(12,2) NOT NULL DEFAULT 0
);
CREATE INDEX idx_order_items_order ON order_items(order_id);
CREATE INDEX idx_order_items_product ON order_items(product_id);

CREATE TABLE payments (
  payment_id   BIGSERIAL PRIMARY KEY,
  order_id     BIGINT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
  paid_ts      TIMESTAMPTZ NOT NULL,
  method       TEXT NOT NULL CHECK (method IN ('card','paypal','apple_pay','klarna')),
  amount       NUMERIC(12,2) NOT NULL,
  status       TEXT NOT NULL CHECK (status IN ('paid','failed','refunded','partial_refund'))
);
CREATE INDEX idx_payments_paid_ts ON payments(paid_ts);

CREATE TABLE refunds (
  refund_id    BIGSERIAL PRIMARY KEY,
  order_id     BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
  refund_ts    TIMESTAMPTZ NOT NULL,
  amount       NUMERIC(12,2) NOT NULL,
  reason       TEXT NOT NULL CHECK (reason IN ('damaged','late_delivery','wrong_item','changed_mind','other'))
);
CREATE INDEX idx_refunds_ts ON refunds(refund_ts);

CREATE TABLE shipments (
  shipment_id   BIGSERIAL PRIMARY KEY,
  order_id      BIGINT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
  carrier       TEXT NOT NULL,
  service_level TEXT NOT NULL CHECK (service_level IN ('standard','expedited','overnight')),
  shipped_ts    TIMESTAMPTZ,
  delivered_ts  TIMESTAMPTZ,
  status        TEXT NOT NULL CHECK (status IN ('pending','shipped','delivered','lost','returned'))
);
CREATE INDEX idx_shipments_shipped_ts ON shipments(shipped_ts);

CREATE TABLE web_events (
  event_id     BIGSERIAL PRIMARY KEY,
  event_ts     TIMESTAMPTZ NOT NULL,
  session_id   UUID NOT NULL,
  customer_id  BIGINT REFERENCES customers(customer_id),
  event_type   TEXT NOT NULL CHECK (event_type IN ('session_start','product_view','add_to_cart','checkout_start','purchase')),
  product_id   BIGINT REFERENCES products(product_id),
  channel      TEXT NOT NULL CHECK (channel IN ('web','mobile')),
  utm_source   TEXT,
  utm_campaign TEXT
);
CREATE INDEX idx_web_events_ts ON web_events(event_ts);
CREATE INDEX idx_web_events_type_ts ON web_events(event_type, event_ts);
