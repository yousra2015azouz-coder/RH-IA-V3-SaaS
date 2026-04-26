"""
modules/recruitment/models.py — Pydantic schemas recrutement
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import date


class JobOfferCreate(BaseModel):
    title: str
    reference: Optional[str] = None
    entity_organisationnelle: Optional[str] = None
    site: Optional[str] = None
    fonction: Optional[str] = None
    type_remuneration: Optional[str] = None
    grade: Optional[str] = None
    salaire_base: Optional[float] = None
    indemnite_panier: float = 0
    indemnite_transport: float = 0
    prime_loyer: float = 0
    prime_aid: float = 0
    taux_cimr: float = 6.00
    description: Optional[str] = None
    requirements: Optional[str] = None
    is_budgeted: bool = False
    recruitment_reason: Optional[str] = "Renforcement de l'équipe"
    expiry_date: Optional[date] = None


class JobOfferUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salaire_base: Optional[float] = None
    is_budgeted: Optional[bool] = None


class CandidateApply(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    birth_date: Optional[date] = None
    situation_familiale: Optional[str] = None
    personnes_a_charge: int = 0
    current_salary: Optional[str] = None


class StageUpdate(BaseModel):
    stage: str
    reason: Optional[str] = ""
