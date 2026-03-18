import os
import asyncpg
from contextlib import asynccontextmanager

_pool = None


async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"])


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_conn():
    async with _pool.acquire() as conn:
        yield conn
