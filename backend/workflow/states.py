"""
workflow/states.py — États et transitions du pipeline candidat
"""
from enum import Enum
from typing import Dict, List


class CandidateStage(str, Enum):
    APPLIED = "applied"
    CHATBOT_COMPLETED = "chatbot_completed"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    EVALUATION_COMPLETED = "evaluation_completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    HIRED = "hired"


class ApprovalStatus(str, Enum):
    PENDING_HIERARCHIQUE = "pending_hierarchique"
    PENDING_FONCTIONNEL = "pending_fonctionnel"
    PENDING_RH = "pending_rh"
    PENDING_DG = "pending_dg"
    APPROVED = "approved"
    REJECTED = "rejected"


# Transitions autorisées
CANDIDATE_TRANSITIONS: Dict[str, List[str]] = {
    CandidateStage.APPLIED: [CandidateStage.CHATBOT_COMPLETED, CandidateStage.REJECTED],
    CandidateStage.CHATBOT_COMPLETED: [CandidateStage.INTERVIEW_SCHEDULED, CandidateStage.REJECTED],
    CandidateStage.INTERVIEW_SCHEDULED: [CandidateStage.EVALUATION_COMPLETED, CandidateStage.REJECTED],
    CandidateStage.EVALUATION_COMPLETED: [CandidateStage.APPROVED, CandidateStage.REJECTED],
    CandidateStage.APPROVED: [CandidateStage.HIRED],
    CandidateStage.REJECTED: [],
    CandidateStage.HIRED: [],
}

APPROVAL_TRANSITIONS: Dict[str, str] = {
    ApprovalStatus.PENDING_HIERARCHIQUE: ApprovalStatus.PENDING_FONCTIONNEL,
    ApprovalStatus.PENDING_FONCTIONNEL: ApprovalStatus.PENDING_RH,
    ApprovalStatus.PENDING_RH: ApprovalStatus.PENDING_DG,
    ApprovalStatus.PENDING_DG: ApprovalStatus.APPROVED,
}

APPROVAL_ROLE_MAP: Dict[str, str] = {
    ApprovalStatus.PENDING_HIERARCHIQUE: "directeur_hierarchique",
    ApprovalStatus.PENDING_FONCTIONNEL: "directeur_fonctionnel",
    ApprovalStatus.PENDING_RH: "directeur_rh",
    ApprovalStatus.PENDING_DG: "directeur_general",
}

STAGE_LABELS: Dict[str, str] = {
    "applied": "Candidature reçue",
    "chatbot": "Pré-qualification chatbot",
    "interview": "Entretien planifié",
    "evaluation": "En évaluation",
    "approved": "Approuvé",
    "rejected": "Rejeté",
    "hired": "Recruté",
}
