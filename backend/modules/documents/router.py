"""
modules/documents/router.py — Endpoints pour récupérer les documents (5.1 & 5.2)
"""
from fastapi import APIRouter, Depends, Request
from backend.auth.dependencies import require_roles
from backend.config import supabase_admin, get_data

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/")
async def list_documents(request: Request, user=Depends(require_roles(["directeur_rh", "directeur_general", "super_admin"]))):
    """Liste tous les documents du tenant."""
    res = supabase_admin.table("documents").select("*").eq("tenant_id", user["tenant_id"]).execute()
    return {"documents": get_data(res) or []}

@router.get("/candidate/{candidate_id}")
async def get_candidate_documents(candidate_id: str, user=Depends(require_roles(["directeur_rh", "super_admin"]))):
    """Liste les documents d'un candidat spécifique."""
    res = supabase_admin.table("documents").select("*").eq("candidate_id", candidate_id).execute()
    return {"documents": get_data(res) or []}
