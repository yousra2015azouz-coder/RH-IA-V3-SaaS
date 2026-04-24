"""
modules/notifications/service.py — Service d'envoi de notifications
"""
import logging
from backend.config import supabase_admin

logger = logging.getLogger(__name__)

async def send_notification(user_id: str, tenant_id: str, title: str, message: str, type: str = "info"):
    """Envoie une notification interne (stockée en base)."""
    try:
        supabase_admin.table("notifications").insert({
            "user_id": user_id,
            "tenant_id": tenant_id,
            "title": title,
            "message": message,
            "type": type,
            "is_read": False
        }).execute()
        logger.debug(f"Notification envoyée à {user_id}: {title}")
    except Exception as e:
        logger.error(f"Erreur envoi notification: {e}")

async def mark_as_read(notification_id: str, user_id: str):
    """Marque une notification comme lue."""
    supabase_admin.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
