"""
modules/candidate/router.py — API Portail Candidat Self-Service
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends, Form, File, UploadFile, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import Optional
from backend.config import supabase_admin, get_data
from backend.auth.dependencies import get_current_user
from backend.modules.recruitment.service import process_cv_and_score
from backend.modules.candidate.service import (
    parse_cv_for_profile,
    get_candidate_by_user,
    get_candidate_applications,
    register_candidate_account,
    update_candidate_profile,
    calculate_profile_completion
)
from backend.modules.ai.cv_parser import extract_text_from_pdf

router = APIRouter(prefix="/candidate", tags=["Candidate Portal"])
logger = logging.getLogger(__name__)


# ── MODÈLES ───────────────────────────────────────────────────
class CandidateRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str


class CandidateProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    ville: Optional[str] = None
    linkedin_url: Optional[str] = None
    diplome: Optional[str] = None
    etablissement: Optional[str] = None
    dernier_poste: Optional[str] = None
    annees_experience: Optional[str] = None
    birth_date: Optional[str] = None
    pretentions_salariales: Optional[float] = None
    situation_familiale: Optional[str] = None
    personnes_a_charge: Optional[int] = None
    disponibilite: Optional[str] = None
    motivation: Optional[str] = None
    ai_skills: Optional[list[str]] = None
    ai_summary: Optional[str] = None


# ── ENDPOINTS ─────────────────────────────────────────────────

@router.post("/register-with-cv")
async def register_with_cv(
    email: EmailStr = Form(...),
    password: str = Form(...),
    tenant_slug: str = Form(...),
    file: UploadFile = File(...)
):
    """
    INSCRIPTION TOUT-EN-UN (Logique demandée) :
    1. Crée le compte Auth & profil User
    2. Extrait et Parse le CV via IA
    3. Crée le profil candidat avec les données extraites
    """
    try:
        # 1. Création du compte
        acc = await register_candidate_account(email, password, tenant_slug)
        user_id = acc["user_id"]
        tenant_id = acc["tenant_id"]

        # 2. Traitement du CV
        cv_bytes = await file.read()
        cv_text = await extract_text_from_pdf(cv_bytes)
        extracted_data = await parse_cv_for_profile(cv_text)

        # 3. Upload Storage (bucket privé)
        file_path = f"cvs/{user_id}/{file.filename}"
        supabase_admin.storage.from_("documents").upload(
            file_path, cv_bytes, {"content-type": "application/pdf", "upsert": "true"}
        )

        # 4. Création profil candidat avec TOUTES les données IA
        profile_payload = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "cv_url": file_path,
            "cv_text": cv_text,
            "ai_extracted_data": extracted_data,
            "first_name": extracted_data.get("first_name"),
            "last_name": extracted_data.get("last_name"),
            "phone": extracted_data.get("phone"),
            "ville": extracted_data.get("ville"),
            "birth_date": extracted_data.get("date_naissance"),
            "linkedin_url": extracted_data.get("linkedin_url"),
            "situation_familiale": extracted_data.get("situation_familiale"),
            "personnes_a_charge": extracted_data.get("personnes_a_charge", 0),
            "diplome": extracted_data.get("diplome"),
            "etablissement": extracted_data.get("etablissement"),
            "dernier_poste": extracted_data.get("dernier_poste"),
            "annees_experience": str(extracted_data.get("annees_experience", "0")),
            "pretentions_salariales": extracted_data.get("pretentions_salariales"),
            "disponibilite": extracted_data.get("disponibilite"),
            "motivation": extracted_data.get("motivation"),
            "ai_skills": extracted_data.get("competences", []),
            "ai_summary": extracted_data.get("resume")
        }
        
        # Calcul complétion
        profile_payload["profile_completion"] = calculate_profile_completion(profile_payload)
        
        supabase_admin.table("candidates").insert(profile_payload).execute()

        # 6. Générer un token d'accès pour connexion immédiate
        login_resp = supabase_admin.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        return {
            "status": "success",
            "message": "Compte créé et profil généré par l'IA",
            "access_token": login_resp.session.access_token,
            "user": acc,
            "extracted_data": extracted_data
        }

    except Exception as e:
        logger.error(f"Erreur inscription combinée: {e}")
        raise HTTPException(400, str(e))


@router.post("/upload-cv")
async def upload_and_parse_cv(
    file: UploadFile = File(...),
    user=Depends(get_current_user)
):
    """
    Upload CV PDF → Extraction texte → Parsing IA → Retourne données structurées.
    Le frontend affiche le résultat pour validation avant sauvegarde.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Seuls les fichiers PDF sont acceptés")

    try:
        cv_bytes = await file.read()

        # 1. Extraire le texte du PDF
        cv_text = await extract_text_from_pdf(cv_bytes)

        # 2. Parser avec l'IA
        extracted_data = await parse_cv_for_profile(cv_text)

        # 3. Uploader le CV dans le storage Supabase (bucket privé)
        file_path = f"cvs/{user['id']}/{file.filename}"
        supabase_admin.storage.from_("documents").upload(
            file_path, cv_bytes, {"content-type": "application/pdf", "upsert": "true"}
        )

        # 4. Stocker le chemin relatif du CV + texte brut + mapping des colonnes
        existing = supabase_admin.table("candidates").select("id").eq("user_id", user["id"]).limit(1).execute()
        update_payload = {
            "cv_text": cv_text, 
            "cv_url": file_path, 
            "ai_extracted_data": extracted_data,
            "first_name": extracted_data.get("first_name"),
            "last_name": extracted_data.get("last_name"),
            "phone": extracted_data.get("phone"),
            "ville": extracted_data.get("ville"),
            "birth_date": extracted_data.get("date_naissance"),
            "linkedin_url": extracted_data.get("linkedin_url"),
            "diplome": extracted_data.get("diplome"),
            "etablissement": extracted_data.get("etablissement"),
            "dernier_poste": extracted_data.get("dernier_poste"),
            "annees_experience": str(extracted_data.get("annees_experience", "0")),
            "ai_skills": extracted_data.get("competences", []),
            "ai_summary": extracted_data.get("resume")
        }

        if existing.data:
            supabase_admin.table("candidates").update(update_payload).eq("user_id", user["id"]).execute()
        else:
            supabase_admin.table("candidates").insert({
                **update_payload,
                "user_id": user["id"],
                "tenant_id": user["tenant_id"],
                "email": user["email"],
                "pipeline_stage": "profile_created"
            }).execute()

        return {
            "status": "success",
            "extracted_data": extracted_data,
            "cv_url": cv_url,
            "message": "CV analysé avec succès par l'IA"
        }

    except Exception as e:
        logger.error(f"Erreur upload CV: {e}")
        raise HTTPException(500, f"Erreur traitement CV: {str(e)}")


@router.get("/profile")
async def get_profile(user=Depends(get_current_user)):
    """Retourne le profil complet du candidat connecté."""
    candidate = await get_candidate_by_user(user["id"])
    if not candidate:
        # Profil vide — le candidat n'a pas encore uploadé son CV
        return {
            "profile": None,
            "user": {
                "id": user["id"],
                "email": user["email"],
                "role": user.get("role", "candidat")
            },
            "profile_completion": 0
        }

    # Génération d'une Signed URL sécurisée si un CV existe
    if candidate.get("cv_url"):
        cv_path = candidate["cv_url"]
        # Retro-compatibilité si l'URL a été sauvegardée en format public
        if "public/documents/" in cv_path:
            cv_path = cv_path.split("public/documents/")[1]
            
        try:
            signed = supabase_admin.storage.from_("documents").create_signed_url(cv_path, 3600)
            if signed and "signedURL" in signed:
                candidate["cv_url"] = signed["signedURL"]
        except Exception as e:
            logger.error(f"Erreur génération URL signée: {e}")

    completion = calculate_profile_completion(candidate)
    return {
        "profile": candidate,
        "user": {"id": user["id"], "email": user["email"], "role": user.get("role")},
        "profile_completion": completion
    }


@router.put("/profile")
async def update_profile(body: CandidateProfileUpdate, user=Depends(get_current_user)):
    """Met à jour les champs du profil candidat (complète ce que l'IA n'a pas extrait)."""
    profile_data = {k: v for k, v in body.dict().items() if v is not None}
    if not profile_data:
        raise HTTPException(400, "Aucune donnée à mettre à jour")

    result = await update_candidate_profile(user["id"], user["tenant_id"], profile_data)
    return {"status": "updated", **result}


@router.get("/applications")
async def get_applications(user=Depends(get_current_user)):
    """Liste toutes les candidatures du candidat avec statut (score IA masqué)."""
    applications = await get_candidate_applications(user["id"])
    
    # Sécurité : masquer le score IA pour le candidat
    for app in applications:
        if "ai_score" in app:
            del app["ai_score"]
            
    return {"applications": applications, "total": len(applications)}


@router.get("/jobs")
async def get_public_jobs(user=Depends(get_current_user)):
    """Liste les offres publiées disponibles pour postuler."""
    res = supabase_admin.table("job_offers")\
        .select("id, title, reference, site, description, requirements, published_at")\
        .eq("tenant_id", user["tenant_id"])\
        .eq("is_published", True)\
        .order("published_at", desc=True)\
        .execute()
    return {"jobs": get_data(res) or []}
