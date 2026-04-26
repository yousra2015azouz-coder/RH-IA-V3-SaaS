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

async def send_welcome_email(email: str, password: str, full_name: str, tenant_name: str = "Votre Entreprise"):
    """
    Simule l'envoi d'un email de bienvenue avec les accès SaaS.
    En production, connectez ceci à Resend, SendGrid ou SMTP.
    """
    subject = f"Bienvenue chez {tenant_name} ! Vos accès à la plateforme RH IA"
    body = f"""
    Bonjour {full_name},
    
    Nous sommes ravis de vous accueillir dans l'équipe.
    
    Voici vos accès pour vous connecter à notre plateforme RH IA :
    - URL : http://localhost:8000/static/auth/login.html
    - Identifiant : {email}
    - Mot de passe temporaire : {password}
    
    IMPORTANT : Pour des raisons de sécurité, veuillez changer votre mot de passe dès votre première connexion.
    
    À bientôt,
    L'équipe RH.
    """
    
    # Simulation
    logger.info("==========================================================")
    logger.info(f"📧 ENVOI EMAIL À : {email}")
    logger.info(f"📝 OBJET : {subject}")
    logger.info(body)
    logger.info("==========================================================")
    
    # On pourrait aussi enregistrer une notification système pour l'admin confirmant l'envoi
    return True

async def mark_as_read(notification_id: str, user_id: str):
    """Marque une notification comme lue."""
    supabase_admin.table("notifications").update({"is_read": True}).eq("id", notification_id).eq("user_id", user_id).execute()
