"""
modules/documents/router.py — Endpoints pour récupérer les documents (5.1 & 5.2)
"""
from fastapi import APIRouter, Depends, Request
from backend.auth.dependencies import require_roles
from backend.config import supabase_admin, get_data

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/")
async def list_documents(request: Request, user=Depends(require_roles(["directeur_rh", "directeur_general", "super_admin"]))):
    """Liste tous les documents du tenant."""
    res = supabase_admin.table("documents").select("*").eq("tenant_id", user["tenant_id"]).execute()
    return {"documents": get_data(res) or []}

@router.get("/candidate/{candidate_id}")
async def get_candidate_documents(candidate_id: str, user=Depends(require_roles(["directeur_rh", "super_admin"]))):
    """Liste les documents d'un candidat spécifique."""
    res = supabase_admin.table("documents").select("*").eq("candidate_id", candidate_id).execute()
    return {"documents": get_data(res) or []}

from fastapi.responses import Response
from backend.utils.pdf_generator import generate_interview_report

@router.get("/interview-report/{evaluation_id}")
async def get_interview_report_pdf(evaluation_id: str, user=Depends(require_roles(["directeur_rh", "super_admin", "directeur_general", "directeur_hierarchique", "directeur_fonctionnel"]))):
    """Génère et renvoie le PDF du Compte Rendu d'Entretien (5.1)."""
    
    # 1. Récupérer l'évaluation avec le candidat
    res_eval = supabase_admin.table("evaluations").select("*, candidates(*)").eq("id", evaluation_id).eq("tenant_id", user["tenant_id"]).execute()
    evals = get_data(res_eval) or []
    if not evals:
        from fastapi import HTTPException
        raise HTTPException(404, "Évaluation non trouvée")
    
    evaluation = evals[0]
    candidate = evaluation.get("candidates", {})
    
    # 2. Récupérer l'offre d'emploi
    job_title = "N/A"
    if candidate and candidate.get("job_offer_id"):
        res_job = supabase_admin.table("job_offers").select("title").eq("id", candidate["job_offer_id"]).execute()
        jobs = get_data(res_job) or []
        if jobs:
            job_title = jobs[0].get("title", "N/A")
            
    # 3. Récupérer les infos du tenant (pour le logo et nom)
    res_tenant = supabase_admin.table("tenants").select("name, primary_color, secondary_color, logo_url").eq("id", user["tenant_id"]).execute()
    tenant = get_data(res_tenant)[0] if get_data(res_tenant) else {}

    # 4. Récupérer le nom de l'évaluateur (Directeur RH)
    res_evaluator = supabase_admin.table("users").select("first_name, last_name").eq("id", evaluation.get("evaluator_id")).execute()
    evaluator_data = get_data(res_evaluator)
    evaluator_name = f"{evaluator_data[0].get('first_name', '')} {evaluator_data[0].get('last_name', '')}".strip() if evaluator_data else "Équipe RH"

    # 5. Préparer les données pour le générateur PDF
    pdf_data = {
        "candidate_name": f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip() or "N/A",
        "job_title": job_title,
        "interviewer_name": evaluator_name,
        "date": evaluation.get("created_at", "").split("T")[0],
        "criteria": evaluation.get("criteria", {}),
        "global_score": evaluation.get("global_score", 0),
        "final_opinion": evaluation.get("final_opinion", "Avis réservé"),
        "comments": evaluation.get("comments", "-"),
        "ai_summary": evaluation.get("groq_suggestion", ""),
        "app_name": tenant.get("name", "RH-IA Platform"),
        "logo_url": tenant.get("logo_url", ""),
        "primary_color": tenant.get("primary_color"),
        "secondary_color": tenant.get("secondary_color")
    }

    # 6. Générer le PDF
    try:
        pdf_bytes = generate_interview_report(pdf_data)
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        import logging
        logging.error(f"Erreur lors de la génération du PDF 5.1 : {e}")
        from fastapi import HTTPException
        raise HTTPException(500, f"Erreur lors de la génération du document: {str(e)}")
