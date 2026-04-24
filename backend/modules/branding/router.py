"""
branding/router.py — Gestion de l'identité visuelle de l'instance
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from backend.auth.dependencies import require_roles
from backend.config import supabase_admin, get_data
import uuid

router = APIRouter(prefix="/branding", tags=["Branding"])

@router.get("/")
async def get_branding():
    """Récupère la configuration visuelle de l'entreprise unique."""
    try:
        # On récupère le premier tenant (modèle une seule entreprise)
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
    app_name: str = Form(None),
    primary_color: str = Form(None),
    secondary_color: str = Form(None),
    hero_title: str = Form(None),
    hero_subtitle: str = Form(None),
    footer_text: str = Form(None),
    logo: UploadFile = File(None),
    user=Depends(require_roles(["super_admin"]))
):
    """Met à jour les réglages visuels (Super Admin uniquement)."""
    try:
        # Trouver le premier tenant
        res = supabase_admin.table("tenants").select("id").limit(1).execute()
        tenant_id = res.data[0]["id"]

        update_data = {}
        if app_name: update_data["name"] = app_name
        if primary_color: update_data["primary_color"] = primary_color
        if secondary_color: update_data["secondary_color"] = secondary_color
        if hero_title: update_data["hero_title"] = hero_title
        if hero_subtitle: update_data["hero_subtitle"] = hero_subtitle
        if footer_text: update_data["footer_text"] = footer_text

        if logo:
            file_ext = logo.filename.split(".")[-1]
            file_name = f"logo_{uuid.uuid4()}.{file_ext}"
            file_content = await logo.read()
            
            # Upload vers Supabase Storage
            storage_res = supabase_admin.storage.from_("branding").upload(
                file_name, file_content, {"content-type": logo.content_type}
            )
            
            # URL publique
            logo_url = supabase_admin.storage.from_("branding").get_public_url(file_name)
            update_data["logo_url"] = logo_url

        # Mise à jour en base
        supabase_admin.table("tenants").update(update_data).eq("id", tenant_id).execute()
        
        return {"status": "success", "message": "Branding mis à jour"}
    except Exception as e:
        raise HTTPException(400, f"Erreur branding: {str(e)}")
