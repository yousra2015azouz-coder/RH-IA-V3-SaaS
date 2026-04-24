"""
modules/error_tracker/service.py — Capture et stockage des erreurs
"""
import logging
import traceback as tb
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


async def log_error(
    message: str,
    module: str = "unknown",
    endpoint: str = "",
    level: str = "ERROR",
    traceback: str = "",
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_data: Optional[dict] = None
):
    """Stocke une erreur en base + log console."""
    try:
        from backend.config import supabase_admin
        supabase_admin.table("error_logs").insert({
            "tenant_id": tenant_id,
            "user_id": user_id,
            "level": level,
            "module": module,
            "endpoint": endpoint,
            "message": message,
            "traceback": traceback or tb.format_exc(),
            "request_data": request_data or {},
            "created_at": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"[ErrorTracker] Impossible d'enregistrer l'erreur en DB: {e}")

    log_fn = getattr(logger, level.lower(), logger.error)
    log_fn(f"[{module}] {endpoint} — {message}")


async def log_warning(message: str, module: str = "unknown", **kwargs):
    await log_error(message=message, module=module, level="WARNING", **kwargs)


async def log_info(message: str, module: str = "unknown", **kwargs):
    await log_error(message=message, module=module, level="INFO", **kwargs)
