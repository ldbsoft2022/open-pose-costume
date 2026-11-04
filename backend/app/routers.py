import uuid
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.db import get_db
from app.deps import current_user
from app.models import User, CreditAccount, GenerationJob, CreditReservation, Project, Character, Asset
from app.schemas import (
    RegisterRequest, LoginRequest, TokenOut, UserOut, CreditOut,
    JobCreate, JobOut, ProjectCreate, ProjectOut, CharacterCreate, CharacterOut
)
from app.security import hash_password, verify_password, create_access_token
from app.services import change_credits, cancel_job_and_refund
from app.config import settings

router = APIRouter()

@router.post("/auth/register", response_model=TokenOut, status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    user = User(email=email, password_hash=hash_password(body.password))
    db.add(user)
    try:
        await db.flush()
        db.add(CreditAccount(user_id=user.id, balance=0))
        await db.flush()
        await change_credits(db, user.id, settings.starter_credits, "grant", f"signup:{user.id}")
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Email already registered")
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut(id=user.id, email=user.email))

@router.post("/auth/login", response_model=TokenOut)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not user.is_active or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return TokenOut(access_token=create_access_token(str(user.id)), user=UserOut(id=user.id, email=user.email))

@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return UserOut(id=user.id, email=user.email)

@router.get("/credits", response_model=CreditOut)
async def credits(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    account = await db.get(CreditAccount, user.id)
    return CreditOut(balance=account.balance if account else 0)

@router.post("/jobs", response_model=JobOut, status_code=202)
async def create_job(
    body: JobCreate,
    user: User = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key")
):
    # Fail closed until a server-side provider adapter and durable queue are configured.
    if settings.model_provider == "disabled" or not settings.model_api_base or not settings.model_api_key:
        raise HTTPException(503, "Image generation is not enabled on this deployment")
    if not idempotency_key or len(idempotency_key) > 128:
        raise HTTPException(400, "A valid Idempotency-Key header is required")
    # Stable user-scoped request lookup prevents duplicate jobs on client retries.
    existing = await db.scalar(select(GenerationJob).where(
        GenerationJob.user_id == user.id,
        GenerationJob.request_key == idempotency_key
    ))
    if existing:
        return JobOut(id=existing.id, status=existing.status, model=existing.model,
                      created_at=existing.created_at, error_code=existing.error_code)
    job = GenerationJob(user_id=user.id, model=body.model, prompt=body.prompt,
                        parameters=body.parameters, status="queued", request_key=idempotency_key)
    db.add(job)
    try:
        await db.flush()
        cost = settings.generation_credit_cost
        await change_credits(db, user.id, -cost, "reserve", f"job-reserve:{job.id}", str(job.id))
        db.add(CreditReservation(user_id=user.id, job_id=job.id, reserved_amount=cost, status="reserved"))
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await db.scalar(select(GenerationJob).where(
            GenerationJob.user_id == user.id, GenerationJob.request_key == idempotency_key
        ))
        if existing is None:
            raise HTTPException(409, "Unable to create idempotent job")
        return JobOut(id=existing.id, status=existing.status, model=existing.model,
                      created_at=existing.created_at, error_code=existing.error_code)
    return JobOut(id=job.id, status=job.status, model=job.model, created_at=job.created_at)

@router.get("/jobs", response_model=list[JobOut])
async def list_jobs(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    jobs = (await db.scalars(select(GenerationJob).where(
        GenerationJob.user_id == user.id
    ).order_by(GenerationJob.created_at.desc()).limit(100))).all()
    return [JobOut(id=j.id, status=j.status, model=j.model, created_at=j.created_at, error_code=j.error_code) for j in jobs]

@router.get("/jobs/{job_id}", response_model=JobOut)
async def get_job(job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await db.scalar(select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.user_id == user.id))
    if job is None:
        raise HTTPException(404, "Job not found")
    return JobOut(id=job.id, status=job.status, model=job.model, created_at=job.created_at, error_code=job.error_code)

@router.post("/jobs/{job_id}/cancel", response_model=JobOut)
async def cancel_job(job_id: uuid.UUID, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    job = await cancel_job_and_refund(db, user.id, job_id)
    await db.commit()
    return JobOut(id=job.id, status=job.status, model=job.model, created_at=job.created_at, error_code=job.error_code)

@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc()))).all()
    return [ProjectOut(id=x.id, name=x.name, created_at=x.created_at) for x in rows]

@router.post("/projects", response_model=ProjectOut, status_code=201)
async def create_project(body: ProjectCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    item = Project(user_id=user.id, name=body.name.strip())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ProjectOut(id=item.id, name=item.name, created_at=item.created_at)

@router.get("/characters", response_model=list[CharacterOut])
async def list_characters(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.scalars(select(Character).where(Character.user_id == user.id).order_by(Character.created_at.desc()))).all()
    return [CharacterOut(id=x.id, name=x.name, description=x.description,
                         reference_asset_ids=[uuid.UUID(v) for v in x.reference_asset_ids],
                         identity_version=x.identity_version, created_at=x.created_at) for x in rows]

@router.post("/characters", response_model=CharacterOut, status_code=201)
async def create_character(body: CharacterCreate, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    asset_ids = [str(x) for x in body.reference_asset_ids]
    if asset_ids:
        owned = (await db.scalars(select(Asset.id).where(
            Asset.user_id == user.id, Asset.id.in_(body.reference_asset_ids)
        ))).all()
        if len(owned) != len(set(body.reference_asset_ids)):
            raise HTTPException(400, "One or more reference assets are not owned by this account")
    item = Character(user_id=user.id, name=body.name.strip(), description=body.description,
                     reference_asset_ids=asset_ids)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return CharacterOut(id=item.id, name=item.name, description=item.description,
                        reference_asset_ids=body.reference_asset_ids,
                        identity_version=item.identity_version, created_at=item.created_at)
