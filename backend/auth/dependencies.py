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


async def get_current_user(request: Request) -> dict:
    """Retourne l'utilisateur courant (via middleware ou résolution directe)."""
    # DEBUG TOTAL
    print(f"--- DEPENDENCY CHECK: {request.method} {request.url.path} ---")
    
    user = getattr(request.state, "user", None)
    if user:
        print(f"User trouvé dans state: {user.get('email')}")
        return user

    # Fail-safe: on cherche dans le header OU dans les query params
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        print("Token trouvé dans Header")
    else:
        token = request.query_params.get("token")
        if token: 
            print("Token trouvé dans URL")
        else:
            # On cherche dans le corps du formulaire (multipart)
            try:
                # Note: request.form() peut être lent car il attend le stream
                form_data = await request.form()
                token = form_data.get("token")
                if token: print("Token trouvé dans Form Data")
            except Exception:
                pass

    if token:
        try:
            from jose import jwt
            from backend.config import supabase_admin
            # Décodage local pour obtenir l'ID sans dépendre du réseau
            payload = jwt.get_unverified_claims(token)
            user_id = payload.get("sub")
            
            if user_id:
                res = supabase_admin.table("users").select("*").eq("id", user_id).execute()
                if res.data:
                    user = res.data[0]
                    request.state.user = user
                    print(f"User identifié localement: {user.get('email')}")
                    return user
        except Exception as e:
            print(f"Erreur décodage local: {e}")

    print("ÉCHEC TOTAL: Aucun utilisateur trouvé")
    raise HTTPException(status_code=401, detail="Non authentifié")


async def resolve_user_from_token(token: str) -> dict:
    """Décode le JWT Supabase localement et retourne le profil depuis la DB."""
    try:
        from jose import jwt
        payload = jwt.get_unverified_claims(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Token malformé")

        profile_res = supabase_admin.table("users").select("*").eq("id", user_id).execute()
        profiles = get_data(profile_res)

        if not profiles:
            raise HTTPException(status_code=401, detail="Profil utilisateur introuvable")

        return profiles[0]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur resolve_user_from_token: {e}")
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


def require_roles(allowed_roles: list[str]):
    """Décorateur FastAPI — vérifie le rôle depuis request.state.user."""
    async def dependency(request: Request):
        user = await get_current_user(request)
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
