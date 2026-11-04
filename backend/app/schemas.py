from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from typing import Any
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
class UserOut(BaseModel):
    id: UUID
    email: EmailStr
class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
class JobCreate(BaseModel):
    model: str = Field(min_length=1, max_length=120)
    prompt: str = Field(min_length=1, max_length=12000)
    parameters: dict[str, Any] = Field(default_factory=dict)
class JobOut(BaseModel):
    id: UUID
    status: str
    model: str
    created_at: Any
    error_code: str | None = None
class CreditOut(BaseModel):
    balance: int
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
class ProjectOut(BaseModel):
    id: UUID
    name: str
    created_at: Any
class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    reference_asset_ids: list[UUID] = Field(default_factory=list, max_length=8)
class CharacterOut(BaseModel):
    id: UUID
    name: str
    description: str
    reference_asset_ids: list[UUID]
    identity_version: int
    created_at: Any
