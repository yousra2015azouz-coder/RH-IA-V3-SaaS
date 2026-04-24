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
import os
import uuid

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

    # Générer résumé GROQ
    summary = await generate_evaluation_summary({
        "criteria": body.criteria,
        "score": body.global_score,
        "opinion": body.final_opinion,
        "comments": body.comments
    })

    # Créer l'évaluation
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

    # Générer PDF 5.1
    cand_info = supabase_admin.table("candidates").select("first_name, last_name, job_offers(title)").eq("id", body.candidate_id).execute()
    cand_data = get_data(cand_info)
    
    pdf_filename = f"evaluation_{body.candidate_id}_{uuid.uuid4().hex[:8]}.pdf"
    pdf_path = os.path.join("backend/static/documents", pdf_filename)
    
    # Préparer données pour le PDF
    pdf_data = {
        "candidate_name": f"{cand_data[0]['first_name']} {cand_data[0]['last_name']}" if cand_data else "Candidat",
        "job_title": cand_data[0]['job_offers']['title'] if cand_data and cand_data[0].get('job_offers') else "Poste",
        "date": body.date if hasattr(body, 'date') else "Aujourd'hui",
        "criteria": body.criteria,
        "global_score": body.global_score / 20, # Retour sur 5 pour le PDF
        "final_opinion": body.final_opinion,
        "comments": body.comments
    }
    
    pdf_bytes = generate_interview_report(pdf_data)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)
        
    pdf_url = f"/generated_docs/{pdf_filename}"

    # Publier événement
    await event_bus.publish("evaluation_submitted", {
        "candidate_id": body.candidate_id,
        "ai_score": body.global_score,
        "opinion": body.final_opinion
    }, user["tenant_id"])

    ev_data = get_data(ev_res)
    return {
        "status": "created", 
        "evaluation": ev_data[0] if ev_data else None,
        "pdf_url": pdf_url
    }


@router.get("/candidate/{candidate_id}")
async def get_evaluations(candidate_id: str, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Évaluations d'un candidat."""
    res = supabase_admin.table("evaluations").select("*").eq(
        "candidate_id", candidate_id).eq("tenant_id", user["tenant_id"]).execute()
    return {"evaluations": get_data(res) or []}
