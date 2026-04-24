"""
modules/evaluation/service.py — Évaluation + suggestion score GROQ
"""
import json
import logging
from backend.modules.ai.groq_client import call_groq
from backend.events.bus import event_bus

logger = logging.getLogger(__name__)


async def suggest_score_from_comments(comments: str, criteria: dict = None) -> dict:
    """GROQ suggère un score basé sur les commentaires de l'évaluateur."""
    system = """Tu es un expert en évaluation RH. Analyse les commentaires de l'évaluateur.
    Retourne UNIQUEMENT un JSON:
    {
      "suggested_score": 0,
      "criteria_scores": {"technique": 0, "communication": 0, "motivation": 0, "culture_fit": 0, "leadership": 0},
      "analysis": "justification courte",
      "final_opinion": "FAVORABLE ou DEFAVORABLE"
    }
    Chaque critère est sur 5. Score global sur 100."""
    user = f"Commentaires: {comments}\nCritères fournis: {json.dumps(criteria or {}, ensure_ascii=False)}"
    try:
        raw = await call_groq(system, user, temperature=0.3, max_tokens=600, json_mode=True)
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur suggest_score: {e}")
        return {"suggested_score": 0, "analysis": str(e), "final_opinion": "DEFAVORABLE"}


async def generate_evaluation_summary(evaluation_data: dict) -> str:
    """Génère un résumé textuel de l'évaluation."""
    system = "Tu es un DRH expert. Génère un résumé professionnel concis (5-6 phrases) de cette évaluation candidat."
    user = json.dumps(evaluation_data, ensure_ascii=False, default=str)
    try:
        return await call_groq(system, user, temperature=0.3, max_tokens=400)
    except Exception:
        return "Résumé non disponible"
