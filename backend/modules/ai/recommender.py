"""
modules/ai/recommender.py — Recommandations IA (mixtral) pour approbation/talent/turnover
"""
import json
import logging
from backend.modules.ai.groq_client import call_groq_analysis

logger = logging.getLogger(__name__)


async def recommend_approval_decision(evaluation_data: dict, salary_data: dict) -> dict:
    """Recommande une décision d'approbation avant validation DG (mixtral)."""
    system = """Tu es un DRH expérimenté. Analyse les données et recommande une décision.
    Retourne UNIQUEMENT un JSON valide:
    {
      "decision": "APPROVE ou REJECT",
      "confidence": 0,
      "justification": "explication",
      "conditions": ["conditions éventuelles"],
      "risques": ["risques identifiés"],
      "biais_detectes": ["biais potentiels à surveiller"]
    }"""
    user = (
        f"Évaluation candidat:\n{json.dumps(evaluation_data, ensure_ascii=False, default=str)}\n\n"
        f"Données salariales:\n{json.dumps(salary_data, ensure_ascii=False, default=str)}"
    )
    try:
        raw = await call_groq_analysis(system, user)
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur recommend_approval: {e}")
        return {"decision": "REVIEW", "confidence": 0, "justification": str(e),
                "conditions": [], "risques": [], "biais_detectes": []}


async def predict_turnover_risk(employee_data: dict) -> dict:
    """Prédit le risque de départ d'un employé (mixtral)."""
    system = """Tu es un expert en rétention des talents. Analyse les données de l'employé.
    Retourne UNIQUEMENT un JSON valide:
    {
      "risk_score": 0,
      "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
      "factors": ["facteurs de risque"],
      "recommendations": ["actions recommandées"],
      "retention_probability": 0
    }"""
    try:
        raw = await call_groq_analysis(system, json.dumps(employee_data, ensure_ascii=False, default=str))
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur predict_turnover: {e}")
        return {"risk_score": 0, "risk_level": "LOW",
                "factors": [], "recommendations": [], "retention_probability": 100}


async def analyze_nine_box(employee_data: dict, performance: float, potential: float, label: str) -> dict:
    """Analyse la position 9-Box d'un employé (mixtral)."""
    system = """Tu es un expert RH en gestion des talents. Analyse la position 9-Box.
    Retourne UNIQUEMENT un JSON valide:
    {
      "analysis": "synthèse 3-4 phrases",
      "strengths": ["points forts"],
      "development_areas": ["axes de développement"],
      "action_plan": ["actions recommandées"]
    }"""
    user = (
        f"Employé: {json.dumps(employee_data, ensure_ascii=False, default=str)}\n"
        f"Performance: {performance}/3 | Potentiel: {potential}/3 | Case: {label}"
    )
    try:
        raw = await call_groq_analysis(system, user)
        return json.loads(raw)
    except Exception as e:
        logger.error(f"Erreur nine_box: {e}")
        return {"analysis": str(e), "strengths": [], "development_areas": [], "action_plan": []}
