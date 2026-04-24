"""
modules/turnover/router.py — Endpoints prédiction turnover
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from backend.auth.dependencies import require_roles, HR_ROLES
from backend.config import supabase_admin, get_data
from backend.modules.ai.recommender import predict_turnover_risk
from backend.events.bus import event_bus

router = APIRouter(prefix="/turnover", tags=["Turnover"])

@router.post("/predict/{employee_id}")
async def predict_employee_turnover(employee_id: str, user=Depends(require_roles(HR_ROLES))):
    """Analyse le risque de départ d'un employé via IA."""
    # 1. Récupérer données employé + historique
    res = supabase_admin.table("employees").select("*, onboarding_tasks(*)").eq("id", employee_id).execute()
    data = get_data(res) or []
    if not data:
        raise HTTPException(404, "Employé non trouvé")
    emp = data[0]

    # 2. Prédiction IA
    risk_data = await predict_turnover_risk(emp)

    # 3. Enregistrer
    supabase_admin.table("turnover_risks").insert({
        "tenant_id": user["tenant_id"],
        "employee_id": employee_id,
        "risk_score": risk_data.get("risk_score", 0),
        "risk_level": risk_data.get("risk_level", "LOW"),
        "factors": risk_data.get("factors", []),
        "recommendations": risk_data.get("recommendations", []),
        "retention_probability": risk_data.get("retention_probability", 100)
    }).execute()

    # 4. Mettre à jour score sur l'employé
    supabase_admin.table("employees").update({
        "turnover_risk_score": risk_data.get("risk_score", 0)
    }).eq("id", employee_id).execute()

    # 5. Déclencher événement si risque élevé
    if risk_data.get("risk_level") in ["HIGH", "CRITICAL"]:
        await event_bus.publish("risk_detected", {
            "employee_id": employee_id,
            "risk_level": risk_data["risk_level"]
        }, user["tenant_id"])

    return risk_data

@router.get("/risks")
async def list_risks(request: Request, user=Depends(require_roles(HR_ROLES))):
    """Liste les derniers risques analysés."""
    res = supabase_admin.table("turnover_risks").select("*, employees(full_name, poste)").eq("tenant_id", user["tenant_id"]).order("analyzed_at", desc=True).limit(50).execute()
    return {"risks": get_data(res) or []}
