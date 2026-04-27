"""
modules/candidate/service.py — Logique métier Portail Candidat Self-Service
"""
import json
import logging
import secrets
import string
from backend.config import supabase_admin, get_data
from backend.modules.ai.groq_client import call_groq

logger = logging.getLogger(__name__)


async def parse_cv_for_profile(cv_text: str) -> dict:
    """
    Utilise GROQ pour extraire les données du CV et pré-remplir le profil.
    Retourne un dict avec tous les champs du profil candidat.
    """
    system = """Tu es un expert RH et parseur de CV. 
    Extrait les informations suivantes du CV fourni.
    Retourne UNIQUEMENT un objet JSON valide avec cette structure exacte :
    {
      "first_name": "string",
      "last_name": "string",
      "email": "string ou null",
      "phone": "string ou null",
      "ville": "string ou null",
      "linkedin_url": "string ou null",
      "diplome": "string (ex: Licence, Master, Bac+5, Doctorat) ou null",
      "etablissement": "string ou null",
      "dernier_poste": "string ou null",
      "annees_experience": "string (ex: 0-1, 1-3, 3-5, 5-10, 10+) ou null",
      "date_naissance": "string (format YYYY-MM-DD) ou null",
      "competences": ["liste", "de", "compétences"],
      "resume": "résumé du profil en 2-3 phrases"
    }
    Si une information n'est pas trouvée, mets null. Ne génère rien de fictif."""

    try:
        raw = await call_groq(system, f"CV à analyser :\n\n{cv_text}", temperature=0.1, json_mode=True)
        data = json.loads(raw)
        logger.info(f"CV parsé avec succès: {data.get('first_name')} {data.get('last_name')}")
        return data
    except Exception as e:
        logger.error(f"Erreur parsing CV: {e}")
        return {}


def calculate_profile_completion(candidate: dict) -> int:
    """
    Calcule le pourcentage de complétion du profil candidat (0-100%).
    Chaque champ rempli contribue au score final.
    """
    fields = {
        "first_name": 5,
        "last_name": 5,
        "email": 5,
        "phone": 5,
        "ville": 5,
        "date_naissance": 5,
        "linkedin_url": 5,
        "diplome": 5,
        "etablissement": 5,
        "dernier_poste": 5,
        "annees_experience": 5,
        "competences": 10,
        "resume": 10,
        "pretentions_salariales": 10,
        "disponibilite": 10,
        "motivation": 5,
        "cv_url": 5,
    }
    total_weight = 100 # Somme des poids ci-dessus
    score = 0
    for field, weight in fields.items():
        val = candidate.get(field)
        # Fallback pour les noms de colonnes Supabase
        if field == "competences" and not val: val = candidate.get("ai_skills")
        if field == "resume" and not val: val = candidate.get("ai_summary")
        if field == "date_naissance" and not val: val = candidate.get("birth_date")

        if val is not None and val != "" and val != 0 and val != []:
            score += weight

    return min(100, round((score / total_weight) * 100))


async def get_candidate_by_user(user_id: str) -> dict | None:
    """Récupère le profil candidat lié à un user_id."""
    res = supabase_admin.table("candidates").select("*").eq("user_id", user_id).limit(1).execute()
    data = get_data(res)
    return data[0] if data else None


async def get_candidate_applications(user_id: str) -> list:
    """
    Récupère toutes les candidatures du candidat connecté,
    avec le statut pipeline et les infos de l'offre.
    """
    # 1. Trouver le candidate_id lié au user
    cand_res = supabase_admin.table("candidates").select("id").eq("user_id", user_id).execute()
    candidate_ids = [c["id"] for c in (cand_res.data or [])]

    if not candidate_ids:
        return []

    # 2. Récupérer toutes les candidatures avec leurs offres
    apps_res = supabase_admin.table("candidates")\
        .select("id, first_name, last_name, pipeline_stage, ai_score, created_at, job_offers(id, title, site, is_published, expiry_date)")\
        .in_("id", candidate_ids)\
        .order("created_at", desc=True)\
        .execute()

    return apps_res.data or []


async def register_candidate_account(email: str, password: str, tenant_slug: str) -> dict:
    """
    Crée un compte Auth Supabase pour le candidat + profil dans users.
    Retourne le user_id et le token de connexion.
    """
    # 1. Vérifier le tenant
    tenant_res = supabase_admin.table("tenants").select("id, name").eq("slug", tenant_slug).eq("is_active", True).execute()
    tenants = get_data(tenant_res)
    if not tenants:
        raise ValueError(f"Entreprise '{tenant_slug}' non trouvée")
    tenant = tenants[0]

    # 2. Créer le compte Auth via l'API Admin (pour ne pas muter la session globale)
    auth_resp = supabase_admin.auth.admin.create_user({
        "email": email,
        "password": password,
        "email_confirm": True
    })
    user_id = str(auth_resp.user.id)

    # 3. Créer profil dans public.users
    supabase_admin.table("users").insert({
        "id": user_id,
        "tenant_id": tenant["id"],
        "email": email,
        "role": "candidat",
        "is_active": True
    }).execute()

    return {
        "user_id": user_id,
        "tenant_id": tenant["id"],
        "tenant_name": tenant["name"],
        "email": email
    }


async def update_candidate_profile(user_id: str, tenant_id: str, profile_data: dict) -> dict:
    """
    Met à jour ou crée le profil candidat avec les données fournies.
    Calcule automatiquement le taux de complétion.
    """
    # Chercher si un profil candidat existe déjà pour cet user
    existing_res = supabase_admin.table("candidates").select("*").eq("user_id", user_id).limit(1).execute()
    existing = existing_res.data or []

    if existing:
        # Mise à jour : fusionner les données existantes avec les nouvelles pour le calcul de complétion
        candidate_id = existing[0]["id"]
        full_data = {**existing[0], **profile_data}
        completion = calculate_profile_completion(full_data)
        profile_data["profile_completion"] = completion
        
        supabase_admin.table("candidates").update(profile_data).eq("id", candidate_id).execute()
        return {"candidate_id": candidate_id, "profile_completion": completion}
    else:
        # Création initiale du profil candidat (sans candidature encore)
        profile_data.update({
            "user_id": user_id,
            "tenant_id": tenant_id,
            "pipeline_stage": "profile_created"
        })
        res = supabase_admin.table("candidates").insert(profile_data).execute()
        data = get_data(res)
        return {"candidate_id": data[0]["id"] if data else None, "profile_completion": completion}
