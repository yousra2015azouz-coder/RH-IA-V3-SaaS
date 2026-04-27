"""
modules/ai/cv_parser.py — Parsing CV avec GROQ
Input  : texte brut du CV (extrait via PyMuPDF)
Output : JSON {nom, email, telephone, competences, experience_years,
               education, langues, score_pertinence, resume}
"""
import io
import json
import logging
try:
    from pypdf import PdfReader  # Vercel-compatible (pure Python)
except ImportError:
    try:
        import fitz  # PyMuPDF fallback (local dev)
        PdfReader = None
    except ImportError:
        PdfReader = None
        fitz = None

from typing import Optional
from backend.modules.ai.groq_client import call_groq

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Tu es un expert RH spécialisé dans l'analyse de CV pour des entreprises marocaines.
Extrais les informations du CV et retourne UNIQUEMENT un JSON valide avec cette structure exacte :
{
  "first_name": "Prénom du candidat",
  "last_name": "NOM en majuscules",
  "email": "string",
  "phone": "string",
  "ville": "string",
  "date_naissance": "YYYY-MM-DD",
  "linkedin_url": "URL LinkedIn complète",
  "situation_familiale": "Célibataire | Marié(e) | Divorcé(e)",
  "personnes_a_charge": 0,
  "diplome": "Le nom du plus haut diplôme obtenu",
  "etablissement": "Nom de l'école ou université du dernier diplôme",
  "dernier_poste": "Intitulé du poste le plus récent",
  "annees_experience": 0,
  "pretentions_salariales": 0,
  "disponibilite": "Immédiate | 1 mois | 3 mois",
  "competences": ["liste de compétences"],
  "langues": [{"langue": "string", "niveau": "string"}],
  "experiences": [{"poste": "string", "entreprise": "string", "duree": "string"}],
  "motivation": "Génère un court paragraphe de motivation (2-3 phrases) basé sur le profil du candidat",
  "score_pertinence": 0,
  "resume": "résumé exécutif professionnel de 3 sentences"
}
Règles :
1. Si une information est absente, mets une chaîne vide "" ou 0 pour les chiffres.
2. Pour les prétentions salariales, si absent, estime-les en fonction du marché marocain pour ce profil (en MAD Net).
3. Le score_pertinence est entre 0-100."""


async def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extrait le texte brut d'un PDF (pypdf ou PyMuPDF selon l'environnement)."""
    try:
        if PdfReader:
            # Mode Vercel : pypdf (pure Python)
            reader = PdfReader(io.BytesIO(file_bytes))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif fitz:
            # Mode local : PyMuPDF
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text = "".join(page.get_text() for page in doc)
            doc.close()
        else:
            return "Impossible d'extraire le texte PDF — aucun parser disponible."
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
