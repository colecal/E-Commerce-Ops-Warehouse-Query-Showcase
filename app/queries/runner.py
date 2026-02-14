from typing import Any
import asyncpg
from app.queries.registry import QUERIES, load_sql


def _coerce_param(name: str, value: str) -> Any:
    # Keep coercion simple and explicit.
    # Dates/months come in as ISO strings and are cast in SQL.
    if name in {"limit"}:
        return int(value)
    return value


async def run_curated_query(conn: asyncpg.Connection, query_id: str, params: dict[str, str]) -> dict[str, Any]:
    if query_id not in QUERIES:
        raise KeyError(f"Unknown query_id: {query_id}")

    q = QUERIES[query_id]
    sql = load_sql(query_id)

    values = []
    for pname in q.params:
        if pname not in params:
            raise ValueError(f"Missing required param '{pname}'")
        values.append(_coerce_param(pname, params[pname]))

    records = await conn.fetch(sql, *values)
    columns = list(records[0].keys()) if records else []
    rows = [list(r.values()) for r in records]

    return {
        "query_id": q.id,
        "title": q.title,
        "description": q.description,
        "params": {k: params[k] for k in q.params},
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "chart": q.chart,
    }
