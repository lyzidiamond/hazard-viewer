import os
import asyncpg
from contextlib import asynccontextmanager

_pool = None

# creates pool against database
async def init_pool():
    global _pool
    _pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"])


# closes all connections
async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# acquires connection from the pool for request duration, automatically returns when the block exits
@asynccontextmanager
async def get_conn():
    assert _pool is not None, "Database pool not initialized"
    async with _pool.acquire() as conn:
        yield conn
