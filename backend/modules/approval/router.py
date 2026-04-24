"""
modules/approval/router.py — Endpoints approbation workflow
"""
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from backend.auth.dependencies import require_roles, DIRECTOR_ROLES, HR_ROLES
from backend.config import supabase_admin, get_data
from backend.modules.approval.service import (
    calculate_moroccan_salary,
    get_next_approval_status, 
    notify_next_approver
)
from backend.utils.pdf_generator import generate_approval_pdf
from backend.modules.documents.service import document_service
from backend.modules.ai.recommender import recommend_approval_decision
from backend.events.bus import event_bus

router = APIRouter(prefix="/approval", tags=["Approval"])

class ApprovalRequestCreate(BaseModel):
    candidate_id: str
    job_offer_id: str
    salaire_base: float
    primes: float = 0
    avantages: Optional[str] = ""
    taux_cimr: float = 6.0
    nom_collaborateur: str
    date_embauche: str
    situation_familiale: str
    personnes_a_charge: int = 0

class ApprovalSignRequest(BaseModel):
    decision: str  # 'APPROVED' or 'REJECTED'
    comments: Optional[str] = ""

@router.post("/request")
async def create_approval_request(body: ApprovalRequestCreate, user=Depends(require_roles(HR_ROLES))):
    """Initialise une demande d'approbation avec calculs fiscaux."""
    # 1. Calculer le salaire net
    salary_data = calculate_moroccan_salary(
        salaire_brut=body.salaire_base,
        taux_cimr=body.taux_cimr,
        nb_enfants=body.personnes_a_charge
    )

    # 2. Obtenir recommandation IA
    # On récupère les évaluations passées pour l'IA
    eval_res = supabase_admin.table("evaluations").select("*").eq("candidate_id", body.candidate_id).execute()
    eval_data = get_data(eval_res) or []
    
    ai_rec = await recommend_approval_decision(eval_data, salary_data)

    # 3. Créer la demande
    req_res = supabase_admin.table("approval_requests").insert({
        "tenant_id": user["tenant_id"],
        "candidate_id": body.candidate_id,
        "job_offer_id": body.job_offer_id,
        "nom_collaborateur": body.nom_collaborateur,
        "date_embauche": body.date_embauche,
        "situation_familiale": body.situation_familiale,
        "personnes_a_charge": body.personnes_a_charge,
        "salaire_base": body.salaire_base,
        "salaire_mensuel_brut": salary_data["salaire_brut"],
        "salaire_mensuel_net": salary_data["salaire_net"],
        "salaire_annuel_garanti": salary_data["salaire_annuel_garanti"],
        "taux_cimr": body.taux_cimr,
        "primes": body.primes,
        "avantages": body.avantages,
        "status": "pending_hierarchique",
        "groq_recommendation": ai_rec
    }).execute()

    data = get_data(req_res)
    if data:
        # 4. Générer PDF 5.2
        pdf_data = {
            "nom_collaborateur": body.nom_collaborateur,
            "job_title": body.job_offer_id, # Idéalement récupérer le titre
            "date_embauche": body.date_embauche,
            "salaire_base": body.salaire_base,
            "primes": body.primes,
            "avantages": body.avantages,
            "salaire_mensuel_net": salary_data["salaire_net"]
        }
        pdf_bytes = generate_approval_pdf(pdf_data)
        doc_url = await document_service.upload_document(pdf_bytes, f"approbation_{body.candidate_id}.pdf", "application/pdf")
        
        # 5. Créer entrée Document
        supabase_admin.table("documents").insert({
            "tenant_id": user["tenant_id"],
            "candidate_id": body.candidate_id,
            "type": "approval_request",
            "file_url": doc_url,
            "generated_by": user["id"]
        }).execute()

        # Notifier le premier approbateur
        await notify_next_approver(user["tenant_id"], data[0]["id"], "pending_hierarchique")
        return {"status": "created", "approval": data[0]}
    
    raise HTTPException(500, "Erreur création demande")

@router.post("/{approval_id}/sign")
async def sign_approval(approval_id: str, body: ApprovalSignRequest, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Signer une étape du workflow."""
    # 1. Vérifier la demande
    res = supabase_admin.table("approval_requests").select("*").eq("id", approval_id).eq("tenant_id", user["tenant_id"]).execute()
    approvals = get_data(res) or []
    if not approvals:
        raise HTTPException(404, "Demande non trouvée")
    approval = approvals[0]

    # 2. Vérifier si le rôle correspond à l'état actuel
    role = user["role"]
    status = approval["status"]
    
    # Mapping simple pour la démo
    role_per_status = {
        "pending_hierarchique": "directeur_hierarchique",
        "pending_fonctionnel": "directeur_fonctionnel",
        "pending_rh": "directeur_rh",
        "pending_dg": "directeur_general"
    }

    if role != role_per_status.get(status) and role != "super_admin":
        raise HTTPException(403, f"Vous n'êtes pas l'approbateur attendu pour l'état {status}")

    if body.decision == "REJECTED":
        supabase_admin.table("approval_requests").update({
            "status": "rejected",
            "rejected_by": user["id"],
            "rejection_reason": body.comments
        }).eq("id", approval_id).execute()
        return {"status": "rejected"}

    # 3. Avancer le workflow
    next_status = await get_next_approval_status(status)
    update_fields = {
        f"signed_{status.split('_')[1]}_at": datetime.utcnow().isoformat(),
        "status": next_status or "approved"
    }

    supabase_admin.table("approval_requests").update(update_fields).eq("id", approval_id).execute()

    if next_status:
        await notify_next_approver(user["tenant_id"], approval_id, next_status)
    else:
        # Workflow terminé
        await event_bus.publish("approval_completed", {
            "candidate_id": approval["candidate_id"],
            "approval_id": approval_id
        }, user["tenant_id"])

    return {"status": "signed", "next_status": next_status or "approved"}

@router.get("/")
async def list_approvals(request: Request, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Liste les demandes d'approbation du tenant."""
    res = supabase_admin.table("approval_requests").select("*, candidates(first_name, last_name), job_offers(title)").eq("tenant_id", user["tenant_id"]).order("created_at", desc=True).execute()
    return {"approvals": get_data(res) or []}

@router.get("/{approval_id}")
async def get_approval(approval_id: str, user=Depends(require_roles(DIRECTOR_ROLES))):
    """Détail d'une demande d'approbation."""
    res = supabase_admin.table("approval_requests").select("*, candidates(*), job_offers(*)").eq("id", approval_id).eq("tenant_id", user["tenant_id"]).execute()
    data = get_data(res) or []
    if not data:
        raise HTTPException(404, "Demande non trouvée")
    return {"approval": data[0]}
