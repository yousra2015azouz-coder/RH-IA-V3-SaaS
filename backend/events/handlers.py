"""
events/handlers.py — Handlers des événements métier
Abonnements définis ici, appelés depuis bus.publish()
"""
import logging
from backend.events.bus import event_bus
from backend.config import supabase_admin, get_data
from backend.modules.approval.service import calculate_moroccan_salary

logger = logging.getLogger(__name__)


# ── candidate_created ─────────────────────────────────────
async def on_candidate_created(payload: dict):
    """Déclenche parsing CV + notifie le DRH."""
    candidate_id = payload.get("candidate_id")
    tenant_id = payload.get("tenant_id")
    logger.info(f"[Handler] candidate_created: {candidate_id}")

    # Notification DRH
    drh_res = supabase_admin.table("users").select("id").eq(
        "tenant_id", tenant_id).eq("role", "directeur_rh").execute()
    for drh in (drh_res.data or []):
        supabase_admin.table("notifications").insert({
            "user_id": drh["id"],
            "tenant_id": tenant_id,
            "title": "Nouvelle candidature",
            "message": f"Un nouveau candidat vient de postuler. CV en cours d'analyse IA.",
            "type": "candidate"
        }).execute()


# ── chatbot_completed ──────────────────────────────────────
async def on_chatbot_completed(payload: dict):
    """Met à jour le stage pipeline → interview."""
    candidate_id = payload.get("candidate_id")
    tenant_id = payload.get("tenant_id")
    logger.info(f"[Handler] chatbot_completed: {candidate_id}")

    supabase_admin.table("candidates").update(
        {"pipeline_stage": "chatbot_completed"}
    ).eq("id", candidate_id).execute()


# ── evaluation_submitted ───────────────────────────────────
async def on_evaluation_submitted(payload: dict):
    """Crée une demande d'approbation si score >= 70, rejette si < 50."""
    candidate_id = payload.get("candidate_id")
    tenant_id = payload.get("tenant_id")
    ai_score = payload.get("ai_score", 0)
    logger.info(f"[Handler] evaluation_submitted: score={ai_score}")

    if ai_score >= 70:
        # 1. Marquer le candidat comme approuvé
        supabase_admin.table("candidates").update(
            {"pipeline_stage": "approved"}
        ).eq("id", candidate_id).execute()
        
        cand_res = supabase_admin.table("candidates").select("*, job_offers(*)").eq("id", candidate_id).execute()
        if cand_res.data:
            cand = cand_res.data[0]
            job = cand.get("job_offers")
            
            # 2.5. Générer Recommandation IA
            from backend.modules.ai.groq_client import call_groq_analysis
            import json
            
            ai_prompt = """
            Tu es un DRH expert. Analyse ce candidat et donne une décision finale de recrutement (APPROVE/REJECT).
            Retourne UNIQUEMENT un objet JSON avec la structure exacte suivante, rien d'autre :
            {"decision": "APPROVE" ou "REJECT", "confidence": <int entre 0 et 100>, "justification": "<string>", "risques": ["<string>"]}
            """
            ai_content = f"Candidat: {cand.get('first_name')} {cand.get('last_name')}\nScore: {ai_score}/100"
            
            groq_rec = None
            try:
                rec_str = await call_groq_analysis(ai_prompt, ai_content)
                groq_rec = json.loads(rec_str)
            except Exception as e:
                logger.error(f"Erreur IA Recommandation: {e}")
                groq_rec = {
                    "decision": "APPROVE", 
                    "confidence": 85, 
                    "justification": "Validation automatique suite au score élevé.",
                    "risques": ["Analyse IA indisponible"]
                }
            
            if job:
                # 3. Calculer les salaires réels
                sal_base = job.get("salaire_base", 0) or 10000
                sal_data = calculate_moroccan_salary(
                    salaire_brut=sal_base,
                    taux_cimr=job.get("taux_cimr", 6.0),
                    nb_enfants=cand.get("personnes_a_charge", 0) or 0
                )

                # 4. Création automatique de la demande d'approbation (Doc 5.2)
                supabase_admin.table("approval_requests").insert({
                    "tenant_id": tenant_id,
                    "candidate_id": candidate_id,
                    "nom_collaborateur": f"{cand.get('first_name')} {cand.get('last_name')}",
                    "job_offer_id": cand.get("job_offer_id"),
                    "salaire_base": sal_data["salaire_brut"],
                    "salaire_mensuel_brut": sal_data["salaire_brut"],
                    "salaire_mensuel_net": sal_data["salaire_net"],
                    "salaire_annuel_garanti": sal_data["salaire_annuel_garanti"],
                    "status": "pending_hierarchique",
                    "groq_recommendation": groq_rec
                }).execute()

                # 5. Générer automatiquement le Compte Rendu d'Entretien (Doc 5.1)
                from backend.modules.documents.service import document_service
                await document_service.generate_and_store_interview_report(candidate_id, payload, tenant_id)
        
        logger.info(f"[Handler] Score >= 70 → Approbation automatique créée")
    elif ai_score < 50:
        supabase_admin.table("candidates").update(
            {"pipeline_stage": "rejected"}
        ).eq("id", candidate_id).execute()
        logger.info(f"[Handler] Score < 50 → rejet automatique")
    else:
        supabase_admin.table("candidates").update(
            {"pipeline_stage": "interview_scheduled"}
        ).eq("id", candidate_id).execute()


# ── approval_completed ─────────────────────────────────────
async def on_approval_completed(payload: dict):
    """Crée l'employé et déclenche l'onboarding."""
    candidate_id = payload.get("candidate_id")
    approval_id = payload.get("approval_id")
    tenant_id = payload.get("tenant_id")
    logger.info(f"[Handler] approval_completed: {approval_id}")

    # Récupérer infos candidat
    cand_res = supabase_admin.table("candidates").select("*").eq(
        "id", candidate_id).execute()
    candidates = cand_res.data or []
    if not candidates:
        return
    cand = candidates[0]

    # Générer le document PDF d'approbation
    from backend.modules.documents.service import document_service
    await document_service.generate_and_store_approval_pdf(approval_id, tenant_id)

    # Créer l'employé
    emp_res = supabase_admin.table("employees").insert({
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "approval_request_id": approval_id,
        "full_name": f"{cand.get('first_name', '')} {cand.get('last_name', '')}".strip(),
        "email": cand.get("email"),
        "onboarding_status": "in_progress",
        "status": "ACTIVE"
    }).execute()

    if emp_res.data:
        await event_bus.publish("employee_created", {
            "employee_id": emp_res.data[0]["id"],
            "candidate_id": candidate_id
        }, tenant_id)


# ── employee_created ───────────────────────────────────────
async def on_employee_created(payload: dict):
    """Initialise les étapes d'onboarding."""
    employee_id = payload.get("employee_id")
    tenant_id = payload.get("tenant_id")
    logger.info(f"[Handler] employee_created: {employee_id}")

    default_tasks = [
        {"title": "Remise du matériel informatique", "category": "Logistique"},
        {"title": "Accès aux systèmes", "category": "IT"},
        {"title": "Présentation à l'équipe", "category": "RH"},
        {"title": "Lecture du règlement intérieur", "category": "RH"},
        {"title": "Formation sécurité", "category": "Formation"},
        {"title": "Entretien de suivi J+30", "category": "RH"},
    ]
    for task in default_tasks:
        supabase_admin.table("onboarding_tasks").insert({
            "employee_id": employee_id,
            "tenant_id": tenant_id,
            "title": task["title"],
            "category": task["category"],
            "status": "PENDING"
        }).execute()


# ── risk_detected ──────────────────────────────────────────
async def on_risk_detected(payload: dict):
    """Alerte le DRH si risque turnover CRITICAL."""
    tenant_id = payload.get("tenant_id")
    employee_id = payload.get("employee_id")
    risk_level = payload.get("risk_level", "MEDIUM")
    logger.info(f"[Handler] risk_detected: {risk_level} — employee {employee_id}")

    if risk_level in ["HIGH", "CRITICAL"]:
        drh_res = supabase_admin.table("users").select("id").eq(
            "tenant_id", tenant_id).eq("role", "directeur_rh").execute()
        for drh in (drh_res.data or []):
            supabase_admin.table("notifications").insert({
                "user_id": drh["id"],
                "tenant_id": tenant_id,
                "title": f"⚠️ Risque Turnover {risk_level}",
                "message": f"Un employé présente un risque de départ {risk_level}. Action requise.",
                "type": "turnover_alert"
            }).execute()


def register_all_handlers():
    """Enregistre tous les handlers sur le bus d'événements."""
    event_bus.subscribe("candidate_created", on_candidate_created)
    event_bus.subscribe("chatbot_completed", on_chatbot_completed)
    event_bus.subscribe("evaluation_submitted", on_evaluation_submitted)
    event_bus.subscribe("approval_completed", on_approval_completed)
    event_bus.subscribe("employee_created", on_employee_created)
    event_bus.subscribe("risk_detected", on_risk_detected)
    logger.info("[EventBus] Tous les handlers enregistrés")
