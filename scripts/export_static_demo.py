"""Export precomputed query results for GitHub Pages static demo.

Writes:
  pages_demo/mock_output/queries.json
  pages_demo/mock_output/<query_id>.json

Run with docker-compose up, then:
  docker compose exec app python -m scripts.export_static_demo
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone

import asyncpg

from app.queries.registry import QUERIES
from app.queries.runner import run_curated_query

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/warehouse")
BASE_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BASE_DIR / "pages_demo" / "mock_output"


def _date(d: datetime):
    """Return a datetime.date for asyncpg bind params."""
    return d.date()


async def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    start_date = _date(now - timedelta(days=90))
    end_date = _date(now)
    start_month = (now.replace(day=1) - timedelta(days=180)).replace(day=1).date()
    end_month = now.replace(day=1).date()

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # list
        queries_payload = {
            "generated_at": now.isoformat(),
            "queries": [
                {
                    "id": q.id,
                    "title": q.title,
                    "description": q.description,
                    "params": q.params,
                    "chart": q.chart,
                }
                for q in QUERIES.values()
            ],
        }
        (OUT_DIR / "queries.json").write_text(json.dumps(queries_payload, indent=2), encoding="utf-8")

        # results
        for qid, q in QUERIES.items():
            params = {}
            if "start_date" in q.params:
                params["start_date"] = start_date
            if "end_date" in q.params:
                params["end_date"] = end_date
            if "start_month" in q.params:
                params["start_month"] = start_month
            if "end_month" in q.params:
                params["end_month"] = end_month

            result = await run_curated_query(conn, qid, params)
            (OUT_DIR / f"{qid}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
