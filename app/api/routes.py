from fastapi import APIRouter, Depends, HTTPException, Query
import asyncpg

from app.db.pool import get_pool
from app.queries.registry import QUERIES
from app.queries.runner import run_curated_query

router = APIRouter()


async def db_conn() -> asyncpg.Connection:
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


@router.get("/health")
async def health(conn: asyncpg.Connection = Depends(db_conn)):
    v = await conn.fetchval("select 1")
    return {"ok": True, "db": v}


@router.get("/queries")
async def list_queries():
    return {
        "queries": [
            {
                "id": q.id,
                "title": q.title,
                "description": q.description,
                "params": q.params,
                "chart": q.chart,
            }
            for q in QUERIES.values()
        ]
    }


@router.get("/query/{query_id}")
async def run_query(
    query_id: str,
    conn: asyncpg.Connection = Depends(db_conn),
    # common params (others are validated in runner)
    start_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYY-MM-DD"),
    start_month: str | None = Query(default=None, description="YYYY-MM-01"),
    end_month: str | None = Query(default=None, description="YYYY-MM-01"),
):
    params = {
        k: v
        for k, v in {
            "start_date": start_date,
            "end_date": end_date,
            "start_month": start_month,
            "end_month": end_month,
        }.items()
        if v is not None
    }

    try:
        return await run_curated_query(conn, query_id, params)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown query")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
