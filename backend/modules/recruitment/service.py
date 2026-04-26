"""
modules/recruitment/service.py — Logique métier recrutement
"""
import logging
from datetime import datetime
from backend.config import supabase_admin, get_data
from backend.modules.ai.cv_parser import parse_cv, extract_text_from_pdf
from backend.modules.ai.scorer import score_candidate
from backend.events.bus import event_bus
from backend.modules.error_tracker.service import log_error

logger = logging.getLogger(__name__)


async def process_cv_and_score(
    candidate_id: str,
    tenant_id: str,
    cv_bytes: bytes,
    job_requirements: str
) -> dict:
    """Pipeline complet: extract → parse → score → update DB."""
    try:
        # 1. Extraire texte
        cv_text = await extract_text_from_pdf(cv_bytes)

        # 2. Parser CV via GROQ
        cv_data = await parse_cv(cv_text, job_requirements)

        # 3. Scorer la correspondance candidat/poste
        score_data = await score_candidate(cv_data, job_requirements)
        ai_score = score_data.get("score", 0)

        # 4. Mettre à jour le candidat en DB
        supabase_admin.table("candidates").update({
            "cv_text": cv_text,
            "ai_score": ai_score,
            "ai_skills": cv_data.get("competences", []),
            "ai_summary": cv_data.get("resume", ""),
        }).eq("id", candidate_id).execute()

        # 5. Publier événement
        await event_bus.publish("candidate_created", {
            "candidate_id": candidate_id,
            "ai_score": ai_score,
            "auto_invite_chatbot": ai_score >= 60  # Seuil de déclenchement auto
        }, tenant_id)

        logger.info(f"CV traité — candidat {candidate_id} | score: {ai_score}/100")
        return {"ai_score": ai_score, "cv_data": cv_data, "score_data": score_data}

    except Exception as e:
        await log_error(
            module="recruitment",
            message=f"Erreur traitement CV candidat {candidate_id}: {e}",
            tenant_id=tenant_id
        )
        raise


def get_dashboard_kpis(tenant_id: str) -> dict:
    """Retourne les KPIs recrutement complets."""
    pipeline_stages = ["applied", "chatbot", "interview", "evaluation", "approved", "rejected", "hired"]
    distribution = {}
    for stage in pipeline_stages:
        res = supabase_admin.table("candidates").select("id", count="exact").eq(
            "tenant_id", tenant_id).eq("pipeline_stage", stage).execute()
        distribution[stage] = res.count or 0

    total = sum(distribution.values())

    scores_res = supabase_admin.table("candidates").select("ai_score").eq(
        "tenant_id", tenant_id).not_.is_("ai_score", "null").execute()
    scores = [c["ai_score"] for c in (scores_res.data or []) if c.get("ai_score")]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0

    jobs_res = supabase_admin.table("job_offers").select("id", count="exact").eq(
        "tenant_id", tenant_id).eq("is_published", True).execute()

    pending_res = supabase_admin.table("approval_requests").select("id", count="exact").eq(
        "tenant_id", tenant_id).not_.in_("status", ["approved", "rejected"]).execute()

    return {
        "total_candidates": total,
        "avg_ai_score": avg_score,
        "conversion_rate": round(distribution.get("hired", 0) / max(total, 1), 2),
        "pending_approvals": pending_res.count or 0,
        "active_jobs": jobs_res.count or 0,
        "pipeline_distribution": distribution,
    }
