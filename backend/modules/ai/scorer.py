"""
modules/ai/scorer.py — Scoring candidat/poste via GROQ
"""
import json
import logging
from backend.modules.ai.groq_client import call_groq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert recruteur RH. Évalue la compatibilité entre le profil candidat
et les exigences du poste. Retourne UNIQUEMENT un JSON valide :
{
  "score": 0,
  "points_forts": ["liste"],
  "points_faibles": ["liste"],
  "recommandation": "conseil détaillé",
  "decision": "PROCEED ou REJECT",
  "justification": "explication détaillée"
}
Score entre 0-100. PROCEED si score >= 60."""


async def score_candidate(cv_data: dict, job_requirements: str) -> dict:
    """Évalue la compatibilité candidat/poste. Retourne score + décision."""
    import json as _json
    user_content = (
        f"Profil candidat:\n{_json.dumps(cv_data, ensure_ascii=False, indent=2)}\n\n"
        f"Exigences du poste:\n{job_requirements}"
    )
    try:
        raw = await call_groq(
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.2,
            max_tokens=1500,
            json_mode=True
        )
        result = json.loads(raw)
        logger.info(f"Score candidat: {result.get('score')}/100 — {result.get('decision')}")
        return result
    except Exception as e:
        logger.error(f"Erreur scorer: {e}")
        return {"score": 0, "decision": "REJECT", "justification": str(e),
                "points_forts": [], "points_faibles": [], "recommandation": ""}
