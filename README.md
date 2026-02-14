# E-Commerce Ops Warehouse Query Showcase (Postgres + FastAPI)

A local-first portfolio project that demonstrates **advanced analytics SQL** on a realistic e-commerce dataset.

- **Database:** Postgres (docker-compose)
- **Backend:** FastAPI (read-only, curated queries only)
- **Frontend:** plain HTML/CSS/JS (framework-free “glass” UI)
- **Optional:** GitHub Pages **static demo** using precomputed JSON responses (no backend required)

## What’s inside

### Seeded warehouse schema
The demo seeds a small warehouse with the following tables:

- `customers`
- `products`
- `orders`
- `order_items`
- `payments`
- `refunds`
- `shipments`
- `web_events`

Schema SQL: [`sql/schema/001_create_tables.sql`](sql/schema/001_create_tables.sql)

### Curated advanced SQL queries
All curated queries live in [`sql/curated/`](sql/curated/):

- **Cohort retention** (monthly)
- **LTV by cohort** (cumulative)
- **AOV trend** (+ rolling window average)
- **Conversion funnel** (sessions → purchase)
- **Anomaly detection** (daily revenue z-score using trailing mean/stddev)
- **Return rate by category**
- **Shipping SLA performance** (percentiles + breach rate)

The API executes only these queries (parameterized) — **no arbitrary SQL**.

## Quickstart (local)

### Prereqs
- Docker + Docker Compose

### Run

```bash
docker compose up --build
```

Open:
- UI: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

On first boot the app will:
1. create/drop/recreate the demo schema (if empty)
2. seed realistic data (customers, products, orders, shipments, refunds, web events)
3. start the FastAPI server

### Reseed from scratch

```bash
FORCE_SEED=1 docker compose up --build
```

## API

### List available queries

```bash
curl http://localhost:8000/api/queries | jq
```

### Run a query

Example (AOV trend):

```bash
curl "http://localhost:8000/api/query/aov_trend?start_date=2025-11-01&end_date=2026-02-14" | jq
```

Response shape:

```json
{
  "query_id": "aov_trend",
  "title": "AOV Trend",
  "description": "...",
  "params": {"start_date": "...", "end_date": "..."},
  "columns": ["week", "orders", "aov", "aov_4wk_ma"],
  "rows": [["2026-01-06", 412, 84.22, 82.91], ...],
  "row_count": 14,
  "chart": {"type": "line"}
}
```

## Frontend

The local UI is served from [`frontend/public/`](frontend/public/) via FastAPI static hosting.

- Query cards (one per curated query)
- Date/month inputs for parameterized queries
- Result table rendering
- Simple Chart.js line chart via lightweight heuristics

## GitHub Pages static demo (optional)

For an iframe-able demo on `colecal.github.io` without hosting a backend, this repo includes `pages_demo/`.

1) Export precomputed responses:

```bash
docker compose exec app python -m scripts.export_static_demo
```

2) Commit the output JSON:
- `pages_demo/mock_output/queries.json`
- `pages_demo/mock_output/<query_id>.json`

3) Configure GitHub Pages to publish from the `pages_demo/` folder.

Static demo entrypoint: `pages_demo/index.html`

## Project structure

```text
app/                 # FastAPI app
  api/               # routes
  db/                # asyncpg pool
  queries/           # query registry + runner
sql/
  schema/            # create tables
  curated/           # portfolio SQL queries
scripts/
  init_db.py         # schema + seed on startup
  seed_data.py       # deterministic fake data
  export_static_demo.py
frontend/public/     # local UI assets
pages_demo/          # static UI + mocked JSON outputs
```

## Notes / design choices

- **Curated-only query execution:** users can’t submit arbitrary SQL, so it’s safe to deploy as a read-only demo.
- **Local-first:** everything runs on your machine via Docker.
- **Warehouse flavor:** the schema is normalized and analytics-friendly (order_items fact table, web events, shipment performance, etc.).

## License

MIT (or replace with your preferred license).
