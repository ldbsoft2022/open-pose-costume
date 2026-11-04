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
class CreditOut(BaseModel): balance: int
