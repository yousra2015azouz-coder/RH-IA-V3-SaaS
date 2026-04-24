"""
config.py — SaaS RH V3
Centralise tous les settings, clients Supabase et Groq.
"""
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client
from groq import Groq

load_dotenv()
logger = logging.getLogger(__name__)

# ── Supabase ──────────────────────────────────────────────
SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
# Accepte les deux noms (compatibilité Vercel et local)
SUPABASE_SERVICE_KEY: str = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or
    os.environ.get("SUPABASE_SERVICE_KEY") or ""
)
SUPABASE_ANON_KEY: str = os.environ.get("SUPABASE_ANON_KEY", "")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY sont requis dans .env")
    # Ne pas lever d'exception au démarrage pour éviter le crash Vercel
    supabase_admin = None
else:
    supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# ── Groq ──────────────────────────────────────────────────
GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL_MAIN: str = "llama-3.3-70b-versatile"
GROQ_MODEL_ANALYSIS: str = "llama-3.1-8b-instant"

groq_client: Groq | None = None
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    logger.warning("GROQ_API_KEY manquant — fonctions IA désactivées")

# ── JWT ───────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "change-me-in-production-32chars")
JWT_ALGORITHM: str = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# ── App ───────────────────────────────────────────────────
PLATFORM_NAME: str = os.environ.get("PLATFORM_NAME", "RH IA Platform")
CORS_ORIGINS: list[str] = os.environ.get(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
).split(",")


def get_data(result) -> list | None:
    """Extrait les données d'un résultat Supabase."""
    try:
        if hasattr(result, "data"):
            return result.data
        return result
    except Exception:
        return None
