"""
jobs/scheduler.py — Tâches planifiées (APScheduler)
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import supabase_admin, get_data

logger = logging.getLogger(__name__)

async def daily_cleanup():
    """Tâche quotidienne: nettoyage des logs ou sessions expirées."""
    logger.info("[Scheduler] Début du nettoyage quotidien...")
    # Exemple: Supprimer les vieilles notifications lues (> 30 jours)
    # supabase_admin.table("notifications").delete().eq("is_read", True)...
    logger.info("[Scheduler] Nettoyage terminé.")

async def check_pending_approvals():
    """Vérifie les approbations en attente depuis longtemps et relance."""
    logger.info("[Scheduler] Vérification des approbations en attente...")
    # Logique de relance par notification
    logger.info("[Scheduler] Vérification terminée.")

def start_scheduler():
    """Initialise et démarre le scheduler."""
    scheduler = AsyncIOScheduler()
    
    # Exécuter tous les jours à minuit
    scheduler.add_job(daily_cleanup, CronTrigger(hour=0, minute=0))
    
    # Exécuter toutes les 6 heures pour les approbations
    scheduler.add_job(check_pending_approvals, CronTrigger(hour="0,6,12,18", minute=0))
    
    scheduler.start()
    logger.info("[Scheduler] APScheduler démarré.")
    return scheduler
