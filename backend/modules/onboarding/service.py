"""
modules/onboarding/service.py — Génération de plan d'onboarding IA
"""
import json
import logging
from backend.modules.ai.groq_client import call_groq
from backend.config import supabase_admin, get_data

logger = logging.getLogger(__name__)

async def generate_onboarding_plan(employee_id: str, tenant_id: str) -> list:
    """Utilise GROQ pour générer des tâches d'onboarding personnalisées."""
    # 1. Récupérer les infos de l'employé
    res = supabase_admin.table("employees").select("*, approval_requests(*)").eq("id", employee_id).execute()
    data = get_data(res) or []
    if not data:
        return []
    emp = data[0]

    # 2. Appeler GROQ
    system = """Tu es un expert RH. Génère un plan d'onboarding de 6 tâches clés pour ce nouvel employé.
    Retourne UNIQUEMENT un JSON:
    {
      "tasks": [
        {"title": "string", "category": "IT|Logistique|RH|Formation", "due_days": int}
      ]
    }"""
    user = f"Employé: {emp['full_name']}, Poste: {emp.get('poste', 'N/A')}, Département: {emp.get('departement', 'N/A')}"
    
    try:
        raw = await call_groq(system, user, temperature=0.5, json_mode=True)
        result = json.loads(raw)
        return result.get("tasks", [])
    except Exception as e:
        logger.error(f"Erreur plan onboarding IA: {e}")
        return []

async def init_employee_onboarding(employee_id: str, tenant_id: str):
    """Initialise les tâches d'onboarding en DB."""
    tasks = await generate_onboarding_plan(employee_id, tenant_id)
    
    if not tasks:
        # Fallback tasks if AI fails
        tasks = [
            {"title": "Accueil et présentation équipe", "category": "RH", "due_days": 1},
            {"title": "Configuration poste de travail", "category": "IT", "due_days": 1},
            {"title": "Signature contrat et documents", "category": "RH", "due_days": 2}
        ]

    from datetime import datetime, timedelta
    for t in tasks:
        due_date = (datetime.utcnow() + timedelta(days=t.get("due_days", 7))).date().isoformat()
        supabase_admin.table("onboarding_tasks").insert({
            "employee_id": employee_id,
            "tenant_id": tenant_id,
            "title": t["title"],
            "category": t["category"],
            "status": "PENDING",
            "due_date": due_date
        }).execute()
    
    logger.info(f"Onboarding initialisé pour l'employé {employee_id}")

async def provision_employee_access(employee_id: str, tenant_id: str):
    """Génère un compte SaaS pour le nouvel employé et envoie les accès."""
    import secrets
    import string
    from backend.modules.notifications.service import send_welcome_email

    # 1. Récupérer les infos de l'employé
    res = supabase_admin.table("employees").select("*, tenants(name)").eq("id", employee_id).execute()
    data = get_data(res) or []
    if not data:
        logger.error(f"Employé {employee_id} non trouvé pour provisionning")
        return
    emp = data[0]
    
    # 2. Générer mot de passe temporaire
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    temp_password = ''.join(secrets.choice(alphabet) for i in range(12))
    
    try:
        # 3. Créer le compte Auth via Admin API
        auth_res = supabase_admin.auth.admin.create_user({
            "email": emp["email"],
            "password": temp_password,
            "email_confirm": True
        })
        user_id = str(auth_res.user.id)
        
        # 4. Créer le profil dans la table users
        supabase_admin.table("users").insert({
            "id": user_id,
            "tenant_id": tenant_id,
            "email": emp["email"],
            "role": "employe",
            "first_name": emp["full_name"].split(' ')[0],
            "last_name": ' '.join(emp["full_name"].split(' ')[1:]),
            "is_active": True
        }).execute()
        
        # 5. Mettre à jour la tâche d'onboarding IT
        supabase_admin.table("onboarding_tasks").update({
            "status": "COMPLETED"
        }).eq("employee_id", employee_id).ilike("title", "%Accès%").execute()
        
        # 6. Envoyer l'email
        tenant_name = emp.get("tenants", {}).get("name", "Votre Entreprise")
        await send_welcome_email(emp["email"], temp_password, emp["full_name"], tenant_name)
        
        logger.info(f"Accès provisionnés pour {emp['full_name']} ({emp['email']})")
        return True
        
    except Exception as e:
        logger.error(f"Erreur provisionning accès pour {employee_id}: {e}")
        return False
