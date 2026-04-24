"""
auth/dependencies.py — Middleware JWT + RBAC
"""
import logging
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM, supabase_admin, get_data

logger = logging.getLogger(__name__)
bearer = HTTPBearer(auto_error=False)


def get_current_user(request: Request) -> dict:
    """Retourne l'utilisateur courant depuis request.state (injecté par le middleware)."""
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Non authentifié")
    return user


async def resolve_user_from_token(token: str) -> dict:
    """Décode le JWT Supabase et retourne le profil complet depuis la DB."""
    try:
        # Supabase tokens — on utilise le service key pour vérifier
        # On peut aussi appeler supabase_admin.auth.get_user(token)
        user_resp = supabase_admin.auth.get_user(token)
        if not user_resp or not user_resp.user:
            raise HTTPException(status_code=401, detail="Token invalide")

        user_id = str(user_resp.user.id)
        profile_res = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        profiles = get_data(profile_res)

        if not profiles:
            raise HTTPException(status_code=401, detail="Profil utilisateur introuvable")

        profile = profiles[0]
        profile["auth_email"] = user_resp.user.email
        return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur resolve_user_from_token: {e}")
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def require_roles(allowed_roles: list[str]):
    """Décorateur FastAPI — vérifie le rôle depuis request.state.user."""
    def dependency(request: Request):
        user = get_current_user(request)
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé. Rôles autorisés: {allowed_roles}"
            )
        return user
    return dependency


# Rôles helpers
ALL_STAFF = ["super_admin", "directeur_rh", "directeur_hierarchique",
             "directeur_fonctionnel", "directeur_general"]
HR_ROLES = ["super_admin", "directeur_rh"]
DIRECTOR_ROLES = ["super_admin", "directeur_rh", "directeur_hierarchique",
                  "directeur_fonctionnel", "directeur_general"]
SUPER_ADMIN_ONLY = ["super_admin"]
