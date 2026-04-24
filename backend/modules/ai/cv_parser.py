"""
modules/ai/cv_parser.py — Parsing CV avec GROQ
Input  : texte brut du CV (extrait via PyMuPDF)
Output : JSON {nom, email, telephone, competences, experience_years,
               education, langues, score_pertinence, resume}
"""
import json
import logging
import fitz  # PyMuPDF
from typing import Optional
from backend.modules.ai.groq_client import call_groq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert RH spécialisé dans l'analyse de CV pour des entreprises marocaines.
Extrais les informations du CV et retourne UNIQUEMENT un JSON valide avec ces champs :
{
  "nom": "string",
  "email": "string",
  "telephone": "string",
  "competences": ["liste de compétences"],
  "experience_years": 0,
  "education": [{"diplome": "string", "etablissement": "string", "annee": "string"}],
  "langues": [{"langue": "string", "niveau": "string"}],
  "experiences": [{"poste": "string", "entreprise": "string", "duree": "string"}],
  "score_pertinence": 0,
  "resume": "résumé exécutif en 3-4 phrases"
}
Le score_pertinence est entre 0-100 et évalue la qualité globale du profil."""


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte brut d'un PDF via PyMuPDF."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"Erreur extraction PDF: {e}")
        raise


async def parse_cv(cv_text: str, job_requirements: Optional[str] = None) -> dict:
    """Parse un CV et compare avec les exigences du poste."""
    user_content = f"CV à analyser:\n\n{cv_text}"
    if job_requirements:
        user_content += f"\n\nExigences du poste:\n{job_requirements}"
        user_content += "\n\nAjuste le score_pertinence en fonction de la correspondance avec le poste."

    try:
        raw = await call_groq(
            system_prompt=SYSTEM_PROMPT,
            user_content=user_content,
            temperature=0.2,
            max_tokens=2000,
            json_mode=True
        )
        result = json.loads(raw)
        logger.info(f"CV parsé — Score: {result.get('score_pertinence', 'N/A')}/100")
        return result
    except json.JSONDecodeError as e:
        logger.error(f"JSON invalide du CV parser: {e}")
        return {"score_pertinence": 0, "resume": "Parsing échoué", "competences": []}
    except Exception as e:
        logger.error(f"Erreur CV parser: {e}")
        raise
