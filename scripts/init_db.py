"""Initialize schema + seed demo data.

Runs on container start. Safe to re-run; by default it will skip seeding if data exists.
Set FORCE_SEED=1 to drop/reseed.
"""

import asyncio
import os
from pathlib import Path

import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/warehouse")
FORCE_SEED = os.getenv("FORCE_SEED", "0") == "1"

BASE_DIR = Path(__file__).resolve().parents[1]
SCHEMA_SQL = (BASE_DIR / "sql" / "schema" / "001_create_tables.sql").read_text(encoding="utf-8")


async def _has_data(conn: asyncpg.Connection) -> bool:
    try:
        return await conn.fetchval("select exists(select 1 from orders limit 1)")
    except asyncpg.UndefinedTableError:
        return False


async def main() -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        if FORCE_SEED:
            await conn.execute(SCHEMA_SQL)
            from scripts.seed_data import seed_all
            await seed_all(conn)
            return

        has_data = await _has_data(conn)
        if not has_data:
            await conn.execute(SCHEMA_SQL)
            from scripts.seed_data import seed_all
            await seed_all(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
