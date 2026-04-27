"""
branding/router.py — Gestion de l'identité visuelle de l'instance
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from backend.config import supabase_admin, get_data
from jose import jwt
import uuid

router = APIRouter(prefix="/branding", tags=["Branding"])


def _verify_super_admin(token: str) -> dict:
    """Vérifie localement que le token appartient à un super_admin."""
    try:
        payload = jwt.get_unverified_claims(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")

        res = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        if not res.data:
            raise HTTPException(status_code=401, detail="Utilisateur introuvable")

        user = res.data[0]
        if user.get("role") != "super_admin":
            raise HTTPException(status_code=403, detail="Accès réservé au Super Admin")

        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token invalide: {str(e)}")


@router.get("/")
async def get_branding():
    """Récupère la configuration visuelle de l'entreprise unique."""
    try:
        res = supabase_admin.table("tenants").select("*").limit(1).execute()
        data = get_data(res)
        if not data:
            return {
                "app_name": "RH-IA Platform",
                "primary_color": "#064E3B",
                "secondary_color": "#EBA023",
                "logo_url": None,
                "hero_title": "Votre Avenir Commence Ici",
                "hero_subtitle": "Découvrez les opportunités de carrière",
                "footer_text": "© 2026 RH-IA Platform"
            }
        return data[0]
    except Exception as e:
        return {"error": str(e)}


@router.post("/")
async def update_branding(
    token: str = Form(...),
    app_name: str = Form(None),
    primary_color: str = Form(None),
    secondary_color: str = Form(None),
    hero_title: str = Form(None),
    hero_subtitle: str = Form(None),
    footer_text: str = Form(None),
    logo: UploadFile = File(None),
):
    """Met à jour les réglages visuels (Super Admin uniquement)."""
    # Vérification du token DIRECTEMENT depuis le Form (stream pas encore épuisé)
    _verify_super_admin(token)

    try:
        res = supabase_admin.table("tenants").select("id").limit(1).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Tenant introuvable")
        tenant_id = res.data[0]["id"]

        update_data = {}
        if app_name: update_data["name"] = app_name
        if primary_color: update_data["primary_color"] = primary_color
        if secondary_color: update_data["secondary_color"] = secondary_color
        if hero_title: update_data["hero_title"] = hero_title
        if hero_subtitle: update_data["hero_subtitle"] = hero_subtitle
        if footer_text: update_data["footer_text"] = footer_text

        if logo and logo.filename:
            file_ext = logo.filename.split(".")[-1]
            file_name = f"logo_{uuid.uuid4()}.{file_ext}"
            file_content = await logo.read()

            supabase_admin.storage.from_("branding").upload(
                file_name, file_content, {"content-type": logo.content_type}
            )

            logo_url = supabase_admin.storage.from_("branding").get_public_url(file_name)
            update_data["logo_url"] = logo_url

        if update_data:
            supabase_admin.table("tenants").update(update_data).eq("id", tenant_id).execute()

        return {"status": "success", "message": "Branding mis à jour avec succès"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erreur branding: {str(e)}")
