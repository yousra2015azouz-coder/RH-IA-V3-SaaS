"""
modules/error_tracker/router.py — Dashboard erreurs (super_admin only)
"""
from fastapi import APIRouter, Request, Depends, Query
from typing import Optional
from backend.auth.dependencies import require_roles, SUPER_ADMIN_ONLY
from backend.config import supabase_admin, get_data

router = APIRouter(prefix="/errors", tags=["Error Tracker"])


@router.get("/")
async def list_errors(
    request: Request,
    level: Optional[str] = Query(None, description="ERROR|WARNING|INFO|CRITICAL"),
    module: Optional[str] = None,
    limit: int = Query(100, le=500),
    _=Depends(require_roles(SUPER_ADMIN_ONLY))
):
    """Liste les erreurs filtrées — super_admin uniquement."""
    q = supabase_admin.table("error_logs").select("*")
    if level:
        q = q.eq("level", level.upper())
    if module:
        q = q.eq("module", module)
    result = q.order("created_at", desc=True).limit(limit).execute()
    data = get_data(result) or []
    return {
        "errors": data,
        "total": len(data),
        "filters": {"level": level, "module": module}
    }


@router.get("/stats")
async def error_stats(request: Request, _=Depends(require_roles(SUPER_ADMIN_ONLY))):
    """Statistiques par level et module."""
    from backend.database import db_select
    all_errors = db_select("error_logs", order_by="created_at", limit=1000)

    stats = {"ERROR": 0, "WARNING": 0, "INFO": 0, "CRITICAL": 0}
    modules: dict = {}
    for e in all_errors:
        lvl = e.get("level", "ERROR")
        stats[lvl] = stats.get(lvl, 0) + 1
        mod = e.get("module", "unknown")
        modules[mod] = modules.get(mod, 0) + 1

    return {"by_level": stats, "by_module": modules, "total": len(all_errors)}


@router.delete("/{error_id}")
async def delete_error(error_id: str, _=Depends(require_roles(SUPER_ADMIN_ONLY))):
    """Supprimer une erreur du log."""
    supabase_admin.table("error_logs").delete().eq("id", error_id).execute()
    return {"status": "deleted"}


@router.delete("/")
async def clear_errors(
    level: Optional[str] = None,
    _=Depends(require_roles(SUPER_ADMIN_ONLY))
):
    """Vider les logs d'erreurs (optionnellement par niveau)."""
    q = supabase_admin.table("error_logs").delete()
    if level:
        q = q.eq("level", level.upper())
    else:
        q = q.neq("id", "00000000-0000-0000-0000-000000000000")  # all rows
    q.execute()
    return {"status": "cleared"}
