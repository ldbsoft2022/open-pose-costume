import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_db
from app.deps import current_user
from app.models import User, CreditAccount, GenerationJob, CreditReservation
from app.schemas import RegisterRequest, LoginRequest, TokenOut, UserOut, CreditOut, JobCreate, JobOut
from app.security import hash_password, verify_password, create_access_token
from app.services import change_credits
from app.config import settings
router = APIRouter()
@router.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    if await db.scalar(select(User).where(User.email == email)): raise HTTPException(409, "Email already registered")
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user); await db.flush()
    db.add(CreditAccount(user_id=user.id, balance=0)); await db.flush()
    await change_credits(db, user.id, settings.starter_credits, "grant", f"signup:{user.id}")
    await db.commit()
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut(id=user.id, email=user.email))
@router.post("/auth/login", response_model=TokenOut)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash): raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut(id=user.id, email=user.email))
@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)): return UserOut(id=user.id, email=user.email)
@router.get("/credits", response_model=CreditOut)
async def credits(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(CreditAccount, user.id)
    return CreditOut(balance=account.balance if account else 0)
@router.post("/jobs", response_model=JobOut, status_code=202)
async def create_job(body: JobCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = GenerationJob(user_id=user.id, model=body.model, prompt=body.prompt, parameters=body.parameters, status="queued")
    db.add(job); await db.flush()
    cost = settings.generation_credit_cost
    await change_credits(db, user.id, -cost, "reserve", f"job-reserve:{job.id}", str(job.id))
    db.add(CreditReservation(user_id=user.id, job_id=job.id, reserved_amount=cost, status="reserved"))
    await db.commit()
    return JobOut(id=job.id, status=job.status, model=job.model, created_at=job.created_at)
@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.user_id == user.id))
    if job is None: raise HTTPException(404, "Job not found")
    return JobOut(id=job.id, status=job.status, model=job.model, created_at=job.created_at)
