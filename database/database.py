import asyncpg
import asyncio
from typing import Optional, List, Any


class Database:
    def __init__(self, dsn: str):
        self.dsn = dsn
        self.pool: Optional[asyncpg.Pool] = None
    

    async def connect(self):
        self.pool = await asyncpg.create_pool(dsn=self.dsn)


    async def disconnect(self):
        if self.pool:
            await self.pool.close()


    async def fetch(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
        
    async def execute(self, query, *args):
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    

