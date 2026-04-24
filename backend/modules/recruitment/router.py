"""
modules/recruitment/router.py — Endpoints recrutement
"""
import asyncio
import logging
from fastapi import APIRouter, Request, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from typing import Optional
from backend.auth.dependencies import require_roles, get_current_user, HR_ROLES, DIRECTOR_ROLES
from backend.modules.recruitment.models import JobOfferCreate, StageUpdate
from backend.modules.recruitment.service import process_cv_and_score, get_dashboard_kpis
from backend.config import supabase_admin, get_data
from backend.workflow.engine import workflow_engine
from backend.modules.error_tracker.service import log_error
from backend.utils.pdf_generator import generate_interview_report
from backend.modules.documents.service import document_service

router = APIRouter(tags=["Recruitment"])
logger = logging.getLogger(__name__)


# ── OFFRES D'EMPLOI ────────────────────────────────────────

@router.get("/jobs/public/{tenant_slug}")
async def public_jobs(tenant_slug: str):
    """Offres publiées — PUBLIC, pas d'authentification."""
    tenant_res = supabase_admin.table("tenants").select("id,name,primary_color").eq(
        "slug", tenant_slug).eq("is_active", True).execute()
    tenants = get_data(tenant_res) or []
    if not tenants:
        raise HTTPException(404, f"Entreprise '{tenant_slug}' non trouvée")

    tenant = tenants[0]
    jobs_res = supabase_admin.table("job_offers").select("*").eq(
        "tenant_id", tenant["id"]).eq("is_published", True).order("created_at", desc=True).execute()

    return {"tenant": tenant, "jobs": get_data(jobs_res) or []}


@router.get("/jobs/public/{tenant_slug}/{job_id}")
async def public_job_detail(tenant_slug: str, job_id: str):
    """Détail d'une offre publique."""
    job_res = supabase_admin.table("job_offers").select("*").eq(
        "id", job_id).eq("is_published", True).execute()
    jobs = get_data(job_res) or []
    if not jobs:
        raise HTTPException(404, "Offre non trouvée")
    return {"job": jobs[0]}


@router.post("/jobs")
async def create_job(job: JobOfferCreate, request: Request,
                     user=Depends(require_roles(HR_ROLES))):
    """Créer une offre d'emploi (directeur_rh)."""
    # Filtrer les champs qui n'existent pas en base de données pour éviter l'erreur PGRST204
    job_data = job.model_dump()
    db_fields = [
        "title", "reference", "entity_organisationnelle", "site", "fonction",
        "type_remuneration", "grade", "salaire_base", "indemnite_panier",
        "indemnite_transport", "prime_loyer", "prime_aid", "taux_cimr",
        "description", "requirements", "is_budgeted"
    ]
    payload = {k: v for k, v in job_data.items() if k in db_fields}
    
    result = supabase_admin.table("job_offers").insert({
        "tenant_id": user["tenant_id"],
        "created_by": user["id"],
        **payload
    }).execute()
    data = get_data(result)
    return {"status": "created", "job": data[0] if data else None}


@router.get("/jobs")
async def list_jobs(request: Request, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Lister les offres du tenant."""
    res = supabase_admin.table("job_offers").select("*, candidates(id)").eq(
        "tenant_id", user["tenant_id"]).order("created_at", desc=True).execute()
    jobs = get_data(res) or []
    for j in jobs:
        j["candidate_count"] = len(j.get("candidates", []))
    return {"jobs": jobs}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Détail d'une offre."""
    res = supabase_admin.table("job_offers").select("*").eq(
        "id", job_id).eq("tenant_id", user["tenant_id"]).execute()
    jobs = get_data(res) or []
    if not jobs:
        raise HTTPException(404, "Offre non trouvée")
    return {"job": jobs[0]}


@router.patch("/jobs/{job_id}/publish")
async def publish_job(job_id: str, user=Depends(require_roles(HR_ROLES))):
    """Publier une offre."""
    from datetime import datetime
    supabase_admin.table("job_offers").update({
        "is_published": True,
        "status": "published",
        "published_at": datetime.utcnow().isoformat()
    }).eq("id", job_id).eq("tenant_id", user["tenant_id"]).execute()
    return {"status": "published"}


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: str, user=Depends(require_roles(HR_ROLES))):
    """Supprimer une offre."""
    supabase_admin.table("job_offers").delete().eq(
        "id", job_id).eq("tenant_id", user["tenant_id"]).execute()
    return {"status": "deleted"}


# ── CANDIDATURES ───────────────────────────────────────────

@router.post("/jobs/{job_id}/apply")
async def apply_to_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    situation_familiale: str = Form(""),
    personnes_a_charge: int = Form(0),
    cv_file: UploadFile = File(...)
):
    """Candidater à une offre — upload CV → analyse IA en background."""
    # Vérifier l'offre
    job_res = supabase_admin.table("job_offers").select("*").eq(
        "id", job_id).eq("is_published", True).execute()
    jobs = get_data(job_res) or []
    if not jobs:
        raise HTTPException(404, "Offre non trouvée ou non publiée")
    job = jobs[0]

    # Lire les bytes du CV
    cv_bytes = await cv_file.read()

    # Créer le candidat en DB
    cand_res = supabase_admin.table("candidates").insert({
        "tenant_id": job["tenant_id"],
        "job_offer_id": job_id,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone[:20],
        "situation_familiale": situation_familiale,
        "personnes_a_charge": personnes_a_charge,
        "pipeline_stage": "applied"
    }).execute()
    cand_data = get_data(cand_res)
    candidate = cand_data[0] if cand_data else None
    if not candidate:
        raise HTTPException(500, "Erreur création candidat")

    # Traitement CV en arrière-plan
    background_tasks.add_task(
        process_cv_and_score,
        candidate["id"],
        job["tenant_id"],
        cv_bytes,
        job.get("requirements", "")
    )

    return {
        "status": "submitted",
        "candidate_id": candidate["id"],
        "message": "Candidature reçue. Analyse CV en cours."
    }


@router.get("/candidates")
async def list_candidates(
    request: Request,
    stage: Optional[str] = None,
    user=Depends(require_roles(DIRECTOR_ROLES))
):
    """Pipeline candidats avec scores IA."""
    q = supabase_admin.table("candidates").select(
        "*, job_offers(title, reference)"
    ).eq("tenant_id", user["tenant_id"])
    if stage:
        q = q.eq("pipeline_stage", stage)
    result = q.order("created_at", desc=True).execute()
    data = get_data(result) or []
    return {"candidates": data, "total": len(data)}


@router.get("/candidates/{candidate_id}")
async def get_candidate(candidate_id: str, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Profil complet d'un candidat."""
    res = supabase_admin.table("candidates").select(
        "*, job_offers(*)"
    ).eq("id", candidate_id).eq("tenant_id", user["tenant_id"]).execute()
    cands = get_data(res) or []
    if not cands:
        raise HTTPException(404, "Candidat non trouvé")
    cand = cands[0]
    history = await workflow_engine.get_history(candidate_id, user["tenant_id"])
    return {"candidate": cand, "workflow_history": history}


@router.patch("/candidates/{candidate_id}/stage")
async def update_stage(
    candidate_id: str,
    body: StageUpdate,
    user=Depends(require_roles(HR_ROLES))
):
    """Avancer un candidat dans le pipeline."""
    try:
        result = await workflow_engine.transition(
            candidate_id=candidate_id,
            tenant_id=user["tenant_id"],
            new_stage=body.stage,
            triggered_by=user["id"],
            reason=body.reason
        )
        return {"status": "transitioned", "transition": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── DASHBOARD KPIs ─────────────────────────────────────────

@router.get("/dashboard/rh")
async def dashboard_rh(user=Depends(require_roles(DIRECTOR_ROLES))):
    """KPIs complets pour le dashboard RH."""
    try:
        kpis = get_dashboard_kpis(user["tenant_id"])
        return kpis
    except Exception as e:
        await log_error(module="recruitment", endpoint="/api/v1/dashboard/rh", message=str(e))
        raise HTTPException(500, f"Erreur KPIs: {str(e)}")


@router.post("/candidates/{candidate_id}/evaluate")
async def evaluate_candidate(candidate_id: str, body: dict, user=Depends(get_current_user)):
    """Saisie de l'évaluation post-entretien et génération du PDF 5.1."""
    try:
        # 1. Récupérer candidat et offre
        res = supabase_admin.table("candidates").select("*, job_offers(*)").eq("id", candidate_id).execute()
        candidate = res.data[0]
        
        # 2. Préparer données PDF
        pdf_data = {
            "candidate_name": f"{candidate['first_name']} {candidate['last_name']}",
            "job_title": candidate["job_offers"]["title"],
            "date": body.get("date"),
            "criteria": body.get("criteria"), # Dict { "Skill": {"score": 4, "comment": "..."} }
            "global_score": body.get("global_score"),
            "final_opinion": body.get("final_opinion"),
            "comments": body.get("comments")
        }
        
        # 3. Générer PDF
        pdf_bytes = generate_interview_report(pdf_data)
        
        # 4. Sauvegarder document
        doc_url = await document_service.upload_document(
            pdf_bytes, 
            f"entretien_{candidate_id}.pdf", 
            "application/pdf"
        )
        
        # 5. Mettre à jour candidat (score et lien doc)
        supabase_admin.table("candidates").update({
            "evaluation_score_global": body.get("global_score"),
            "pipeline_stage": "evaluation_completed"
        }).eq("id", candidate_id).execute()
        
        # 6. Créer entrée Document
        supabase_admin.table("documents").insert({
            "tenant_id": candidate["tenant_id"],
            "candidate_id": candidate_id,
            "type": "interview_report",
            "file_url": doc_url,
            "generated_by": user["id"]
        }).execute()
        
        return {"status": "success", "pdf_url": doc_url}
    except Exception as e:
        raise HTTPException(400, f"Erreur évaluation: {str(e)}")
