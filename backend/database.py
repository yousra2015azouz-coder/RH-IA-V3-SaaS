"""
database.py — Helpers Supabase réutilisables
"""
from backend.config import supabase_admin, get_data
from typing import Optional


def db_select(table: str, filters: dict = None, select: str = "*",
              order_by: str = None, limit: int = None) -> list:
    q = supabase_admin.table(table).select(select)
    if filters:
        for col, val in filters.items():
            q = q.eq(col, val)
    if order_by:
        q = q.order(order_by, desc=True)
    if limit:
        q = q.limit(limit)
    return get_data(q.execute()) or []


def db_insert(table: str, data: dict) -> Optional[dict]:
    result = supabase_admin.table(table).insert(data).execute()
    rows = get_data(result)
    return rows[0] if rows else None


def db_update(table: str, data: dict, filters: dict) -> Optional[dict]:
    q = supabase_admin.table(table).update(data)
    for col, val in filters.items():
        q = q.eq(col, val)
    result = q.execute()
    rows = get_data(result)
    return rows[0] if rows else None


def db_delete(table: str, filters: dict) -> bool:
    q = supabase_admin.table(table).delete()
    for col, val in filters.items():
        q = q.eq(col, val)
    q.execute()
    return True


def db_count(table: str, filters: dict = None) -> int:
    q = supabase_admin.table(table).select("id", count="exact")
    if filters:
        for col, val in filters.items():
            q = q.eq(col, val)
    result = q.execute()
    return result.count or 0
