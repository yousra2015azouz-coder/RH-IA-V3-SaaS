"""
modules/talent/router.py — Endpoints Matrice 9-Box et gestion des talents
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from backend.auth.dependencies import require_roles, HR_ROLES
from backend.config import supabase_admin, get_data
from backend.modules.ai.recommender import analyze_nine_box

router = APIRouter(prefix="/talent", tags=["Talent"])

class TalentEvaluationRequest(BaseModel):
    employee_id: str
    performance_score: float # 1 to 3
    potential_score: float   # 1 to 3

@router.post("/evaluate")
async def evaluate_talent(body: TalentEvaluationRequest, user=Depends(require_roles(HR_ROLES))):
    """Évalue un employé et le positionne dans la matrice 9-Box avec analyse IA."""
    # 1. Déterminer le label 9-Box
    perf = body.performance_score
    pot = body.potential_score
    
    if perf >= 2.5 and pot >= 2.5: label = "Star"
    elif perf >= 2.5 and pot >= 1.5: label = "High Professional"
    elif perf >= 2.5: label = "Core Employee"
    elif perf >= 1.5 and pot >= 2.5: label = "High Potential"
    elif perf >= 1.5 and pot >= 1.5: label = "Core Professional"
    elif perf >= 1.5: label = "Inconsistent Player"
    elif pot >= 2.5: label = "Question Mark"
    elif pot >= 1.5: label = "Dilemma"
    else: label = "Under Performer"

    # 2. Récupérer données employé
    emp_res = supabase_admin.table("employees").select("*").eq("id", body.employee_id).execute()
    employees = get_data(emp_res) or []
    if not employees:
        raise HTTPException(404, "Employé non trouvé")
    emp = employees[0]

    # 3. Analyse IA
    ai_res = await analyze_nine_box(emp, perf, pot, label)

    # 4. Enregistrer dans talent_matrix
    supabase_admin.table("talent_matrix").insert({
        "tenant_id": user["tenant_id"],
        "employee_id": body.employee_id,
        "performance_score": perf,
        "potential_score": pot,
        "nine_box_label": label,
        "ai_analysis": ai_res
    }).execute()

    # 5. Mettre à jour l'employé
    supabase_admin.table("employees").update({
        "performance_score": perf,
        "potential_score": pot,
        "nine_box_position": label
    }).eq("id", body.employee_id).execute()

    return {
        "status": "evaluated",
        "label": label,
        "ai_analysis": ai_res
    }

@router.get("/matrix")
async def get_talent_matrix(request: Request, user=Depends(require_roles(HR_ROLES))):
    """Récupère tous les employés positionnés dans la matrice."""
    res = supabase_admin.table("employees").select("id, full_name, performance_score, potential_score, nine_box_position").eq("tenant_id", user["tenant_id"]).not_.is_("nine_box_position", "null").execute()
    return {"matrix": get_data(res) or []}
