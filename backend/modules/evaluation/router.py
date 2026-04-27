"""
modules/evaluation/router.py — Endpoints évaluation candidat
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from backend.auth.dependencies import require_roles, DIRECTOR_ROLES, HR_ROLES
from backend.config import supabase_admin, get_data
from backend.modules.evaluation.service import suggest_score_from_comments, generate_evaluation_summary
from backend.events.bus import event_bus
from backend.utils.pdf_generator import generate_interview_report
import logging
import os
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class EvaluationCreate(BaseModel):
    candidate_id: str
    criteria: dict
    global_score: float
    final_opinion: str
    comments: Optional[str] = ""


class SuggestScoreRequest(BaseModel):
    comments: str
    criteria: Optional[dict] = None


@router.post("/suggest-score")
async def suggest_score(body: SuggestScoreRequest, _=Depends(require_roles(DIRECTOR_ROLES))):
    """GROQ suggère un score basé sur les commentaires."""
    result = await suggest_score_from_comments(body.comments, body.criteria)
    return result


@router.post("/")
async def create_evaluation(body: EvaluationCreate, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Soumettre une évaluation candidat."""
    # Vérifier le candidat
    cand_res = supabase_admin.table("candidates").select("tenant_id,ai_score").eq(
        "id", body.candidate_id).execute()
    cands = get_data(cand_res) or []
    if not cands:
        raise HTTPException(404, "Candidat non trouvé")

    # Générer résumé GROQ (optionnel, ne doit pas bloquer)
    summary = "Résumé en attente de génération..."
    try:
        logger.info("🤖 Appel GROQ pour le résumé d'évaluation...")
        summary = await generate_evaluation_summary({
            "criteria": body.criteria,
            "score": body.global_score,
            "opinion": body.final_opinion,
            "comments": body.comments
        })
    except Exception as e:
        logger.warning(f"⚠️ Échec résumé GROQ : {e}")

    # Créer l'évaluation
    logger.info(f"💾 Enregistrement de l'évaluation pour {body.candidate_id}")
    ev_res = supabase_admin.table("evaluations").insert({
        "tenant_id": user["tenant_id"],
        "candidate_id": body.candidate_id,
        "evaluator_id": user["id"],
        "criteria": body.criteria,
        "global_score": body.global_score,
        "final_opinion": body.final_opinion,
        "comments": body.comments,
        "groq_suggestion": summary
    }).execute()

    # Récupérer les informations complètes pour le PDF
    cand_info = supabase_admin.table("candidates").select("first_name, last_name, email, phone, job_offer_id, job_offers(title)").eq("id", body.candidate_id).execute()
    cand_data = get_data(cand_info)
    
    candidate_name = "Candidat Inconnu"
    candidate_email = "N/A"
    candidate_phone = "N/A"
    job_title = "Poste non spécifié"
    
    if cand_data and len(cand_data) > 0:
        c = cand_data[0]
        candidate_name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or "Candidat"
        candidate_email = c.get('email', 'N/A')
        candidate_phone = c.get('phone', 'N/A')
        if c.get('job_offers'):
            job_title = c['job_offers'].get('title', 'Poste')

    # Récupérer branding
    brand_res = supabase_admin.table("tenants").select("*").eq("id", user["tenant_id"]).execute()
    brand_data = get_data(brand_res)
    branding = brand_data[0] if brand_data else {}

    # Publier événement
    await event_bus.publish("evaluation_submitted", {
        "candidate_id": body.candidate_id,
        "ai_score": body.global_score,
        "opinion": body.final_opinion
    }, user["tenant_id"])

    ev_data = get_data(ev_res)
    evaluation_id = ev_data[0]["id"] if ev_data else None
    
    return {
        "status": "created", 
        "evaluation": ev_data[0] if ev_data else None,
        "pdf_url": f"/api/v1/documents/interview-report/{evaluation_id}" if evaluation_id else None
    }


@router.get("/candidate/{candidate_id}")
async def get_evaluations(candidate_id: str, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Évaluations d'un candidat."""
    res = supabase_admin.table("evaluations").select("*").eq(
        "candidate_id", candidate_id).eq("tenant_id", user["tenant_id"]).execute()
    return {"evaluations": get_data(res) or []}
