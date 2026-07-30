"""Lazy asyncpg connection pool. Raw SQL only — matches the migrations
convention (see migrations/env.py), no ORM models.
"""
from __future__ import annotations

import os

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    return _pool
