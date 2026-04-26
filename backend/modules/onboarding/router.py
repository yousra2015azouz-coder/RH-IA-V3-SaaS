"""
modules/onboarding/router.py — Endpoints gestion onboarding
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from backend.auth.dependencies import require_roles, HR_ROLES, ALL_STAFF
from backend.config import supabase_admin, get_data

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

@router.get("/employees")
async def list_onboarding_employees(request: Request, user=Depends(require_roles(HR_ROLES))):
    """Liste les employés en cours d'onboarding."""
    res = supabase_admin.table("employees").select("*").eq("tenant_id", user["tenant_id"]).neq("onboarding_status", "completed").execute()
    return {"employees": get_data(res) or []}

@router.get("/tasks/{employee_id}")
async def list_tasks(employee_id: str, request: Request, user=Depends(require_roles(ALL_STAFF))):
    """Liste les tâches d'onboarding pour un employé."""
    res = supabase_admin.table("onboarding_tasks").select("*").eq("employee_id", employee_id).eq("tenant_id", user["tenant_id"]).execute()
    return {"tasks": get_data(res) or []}

@router.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: str, request: Request, user=Depends(require_roles(ALL_STAFF))):
    """Marquer une tâche comme terminée."""
    from datetime import datetime
    supabase_admin.table("onboarding_tasks").update({
        "status": "COMPLETED",
        "completed_at": datetime.utcnow().isoformat()
    }).eq("id", task_id).eq("tenant_id", user["tenant_id"]).execute()
    
    return {"status": "completed"}

@router.get("/stats")
async def onboarding_stats(request: Request, user=Depends(require_roles(HR_ROLES))):
    """Statistiques onboarding pour le dashboard."""
    tid = user["tenant_id"]
    total = supabase_admin.table("onboarding_tasks").select("id", count="exact").eq("tenant_id", tid).execute()
    done = supabase_admin.table("onboarding_tasks").select("id", count="exact").eq("tenant_id", tid).eq("status", "COMPLETED").execute()
    
    return {
        "total_tasks": total.count or 0,
        "completed_tasks": done.count or 0,
        "progress_rate": round((done.count or 0) / max(total.count or 1, 1) * 100, 1)
    }

@router.get("/my-tasks")
async def get_my_tasks(user=Depends(require_roles(["employe", "candidat"] + ALL_STAFF))):
    """
    Retourne les tâches d'onboarding de l'employé connecté.
    Accessible par l'employé lui-même via son user_id → employee_id.
    """
    # Trouver l'employé lié à ce user via la table candidates → employees
    cand_res = supabase_admin.table("candidates").select("id").eq("user_id", user["id"]).limit(1).execute()
    candidates = get_data(cand_res) or []

    if not candidates:
        return {"tasks": [], "employee": None}

    candidate_id = candidates[0]["id"]

    # Trouver l'employé lié à ce candidat
    emp_res = supabase_admin.table("employees").select("id, full_name, date_embauche, poste, onboarding_status").eq("candidate_id", candidate_id).limit(1).execute()
    employees = get_data(emp_res) or []

    if not employees:
        return {"tasks": [], "employee": None}

    employee_id = employees[0]["id"]

    # Récupérer les tâches
    tasks_res = supabase_admin.table("onboarding_tasks").select("*").eq("employee_id", employee_id).order("created_at").execute()

    return {
        "tasks": get_data(tasks_res) or [],
        "employee": employees[0]
    }
