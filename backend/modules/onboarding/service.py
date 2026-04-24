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
