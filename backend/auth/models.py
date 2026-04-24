"""
auth/models.py — Pydantic schemas pour l'authentification
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    tenant_slug: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class UserProfile(BaseModel):
    id: str
    tenant_id: Optional[str]
    email: Optional[str]
    role: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
