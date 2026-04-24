"""
auth/router.py — Endpoints Login / Signup / Me
"""
import logging
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from backend.auth.models import LoginRequest, SignupRequest
from backend.auth.dependencies import get_current_user, require_roles
from backend.config import supabase_admin, get_data
from backend.modules.error_tracker.service import log_error

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/login")
async def login(body: LoginRequest, request: Request):
    """Login via Supabase Auth → retourne JWT + profil utilisateur."""
    try:
        response = supabase_admin.auth.sign_in_with_password({
            "email": body.email,
            "password": body.password
        })
        user_id = str(response.user.id)

        profile_res = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        profiles = get_data(profile_res)
        profile = profiles[0] if profiles else {}

        return {
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "token_type": "bearer",
            "user": profile,
            "auth": {"id": user_id, "email": response.user.email}
        }
    except Exception as e:
        await log_error(module="auth", endpoint="/api/v1/auth/login",
                        message=str(e), level="ERROR")
        raise HTTPException(status_code=401, detail=f"Identifiants invalides: {str(e)}")


@router.post("/signup")
async def signup(body: SignupRequest, request: Request):
    """Inscription candidat — vérifie le tenant slug."""
    try:
        # Vérifier tenant
        tenant_res = supabase_admin.table("tenants").select("id,name").eq(
            "slug", body.tenant_slug).eq("is_active", True).execute()
        tenants = get_data(tenant_res)
        if not tenants:
            raise HTTPException(404, f"Entreprise '{body.tenant_slug}' non trouvée")
        tenant = tenants[0]

        # Créer compte Supabase Auth
        auth_resp = supabase_admin.auth.sign_up({
            "email": body.email,
            "password": body.password
        })
        user_id = str(auth_resp.user.id)

        # Créer profil dans public.users
        supabase_admin.table("users").insert({
            "id": user_id,
            "tenant_id": tenant["id"],
            "email": body.email,
            "role": "candidat",
            "first_name": body.first_name,
            "last_name": body.last_name,
            "is_active": True
        }).execute()

        return {
            "status": "success",
            "message": "Compte créé avec succès",
            "user_id": user_id,
            "tenant": tenant["name"]
        }
    except HTTPException:
        raise
    except Exception as e:
        await log_error(module="auth", endpoint="/api/v1/auth/signup", message=str(e))
        raise HTTPException(status_code=400, detail=f"Erreur inscription: {str(e)}")


@router.get("/me")
async def get_me(request: Request):
    """Retourne le profil de l'utilisateur courant."""
    user = get_current_user(request)
    return {"user": user}


@router.post("/setup-superadmin")
async def setup_superadmin(body: SignupRequest, secret_key: str):
    """Configuration initiale du Super Admin (nécessite une clé secrète)."""
    # Pour la démo, on utilise une clé simple, en prod ce serait dans .env
    if secret_key != "MASTER_SECRET_2026":
        raise HTTPException(403, "Clé secrète invalide")

    try:
        # Créer tenant principal si inexistant
        tenant_res = supabase_admin.table("tenants").select("id").eq("slug", "master").execute()
        if not tenant_res.data:
            tenant_res = supabase_admin.table("tenants").insert({
                "name": "Platform Administration",
                "slug": "master",
                "is_active": True
            }).execute()
        
        tenant_id = tenant_res.data[0]["id"]

        # Créer Auth
        auth_resp = supabase_admin.auth.sign_up({
            "email": body.email,
            "password": body.password
        })
        user_id = str(auth_resp.user.id)

        # Créer Profil
        supabase_admin.table("users").insert({
            "id": user_id,
            "tenant_id": tenant_id,
            "email": body.email,
            "role": "super_admin",
            "first_name": body.first_name,
            "last_name": body.last_name,
            "is_active": True
        }).execute()

        return {"status": "success", "message": "Super Admin créé avec succès"}
    except Exception as e:
        raise HTTPException(400, f"Erreur setup: {str(e)}")


@router.post("/create-director")
async def create_director(body: SignupRequest, role: str, user=Depends(require_roles(["super_admin"]))):
    """Permet au Super Admin de créer des comptes directeurs pour n'importe quel tenant."""
    if role not in ["directeur_rh", "directeur_hierarchique", "directeur_fonctionnel", "directeur_general"]:
        raise HTTPException(400, "Rôle invalide")

    try:
        # Trouver le tenant par slug
        tenant_res = supabase_admin.table("tenants").select("id").eq("slug", body.tenant_slug).execute()
        if not tenant_res.data:
            raise HTTPException(404, f"Tenant {body.tenant_slug} non trouvé")
        
        tenant_id = tenant_res.data[0]["id"]

        # Créer Auth (via admin API pour ne pas déconnecter le super admin actuel)
        # Note: supabase_admin a les droits service_role
        auth_resp = supabase_admin.auth.admin.create_user({
            "email": body.email,
            "password": body.password,
            "email_confirm": True
        })
        user_id = str(auth_resp.user.id)

        # Créer Profil
        supabase_admin.table("users").insert({
            "id": user_id,
            "tenant_id": tenant_id,
            "email": body.email,
            "role": role,
            "first_name": body.first_name,
            "last_name": body.last_name,
            "is_active": True
        }).execute()

        return {"status": "success", "user_id": user_id}
    except Exception as e:
        raise HTTPException(400, f"Erreur création directeur: {str(e)}")


@router.get("/tenants")
async def list_tenants(user=Depends(require_roles(["super_admin"]))):
    """Liste tous les tenants (entreprises) de la plateforme."""
    res = supabase_admin.table("tenants").select("*").execute()
    return {"tenants": res.data or []}


@router.post("/tenants")
async def create_tenant(name: str, slug: str, user=Depends(require_roles(["super_admin"]))):
    """Crée un nouveau tenant."""
    res = supabase_admin.table("tenants").insert({
        "name": name,
        "slug": slug,
        "is_active": True
    }).execute()
    return {"status": "created", "tenant": res.data[0] if res.data else None}


@router.post("/change-password")
async def change_password(new_password: str, user=Depends(get_current_user)):
    """Permet à l'utilisateur connecté de changer son mot de passe."""
    try:
        supabase_admin.auth.admin.update_user_by_id(
            user["id"], 
            {"password": new_password}
        )
        return {"status": "success", "message": "Mot de passe mis à jour"}
    except Exception as e:
        raise HTTPException(400, f"Erreur: {str(e)}")


@router.get("/users")
async def list_users(user=Depends(require_roles(["super_admin"]))):
    """Liste tous les comptes directeurs créés."""
    try:
        res = supabase_admin.table("users").select("id, email, first_name, last_name, role, is_active").neq("role", "super_admin").execute()
        return {"users": res.data or []}
    except Exception as e:
        raise HTTPException(500, f"Erreur: {str(e)}")
