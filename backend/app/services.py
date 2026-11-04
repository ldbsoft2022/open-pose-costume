import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import CreditAccount, CreditTransaction, GenerationJob, CreditReservation

async def change_credits(db: AsyncSession, user_id: uuid.UUID, amount: int, kind: str, key: str, reference_id: str | None = None) -> int:
    if amount == 0:
        raise ValueError("Credit change cannot be zero")
    # Lock the account first, then re-check idempotency under that lock. This serializes
    # concurrent operations for one account and closes the check-then-insert race.
    account = await db.scalar(
        select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update()
    )
    if account is None:
        raise HTTPException(404, "Credit account not found")
    existing = await db.scalar(
        select(CreditTransaction).where(CreditTransaction.idempotency_key == key)
    )
    if existing:
        if existing.user_id != user_id or existing.amount != amount or existing.kind != kind:
            raise HTTPException(409, "Idempotency key already used for a different operation")
        return existing.balance_after
    new_balance = account.balance + amount
    if new_balance < 0:
        raise HTTPException(402, "Insufficient credits")
    account.balance = new_balance
    db.add(CreditTransaction(
        user_id=user_id, amount=amount, balance_after=new_balance, kind=kind,
        idempotency_key=key, reference_id=reference_id
    ))
    await db.flush()
    return new_balance

async def fail_job_and_refund(db: AsyncSession, job_id: uuid.UUID, error_code: str) -> GenerationJob:
    job = await db.scalar(select(GenerationJob).where(GenerationJob.id == job_id).with_for_update())
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status in {"succeeded", "failed", "cancelled"}:
        return job
    reservation = await db.scalar(
        select(CreditReservation).where(CreditReservation.job_id == job.id).with_for_update()
    )
    if reservation is not None and reservation.status == "reserved":
        await change_credits(
            db, job.user_id, reservation.reserved_amount, "refund",
            f"job-refund:{job.id}", str(job.id)
        )
        reservation.status = "refunded"
        reservation.settled_amount = 0
    job.status = "failed"
    job.error_code = error_code[:64]
    await db.flush()
    return job

async def cancel_job_and_refund(db: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID) -> GenerationJob:
    job = await db.scalar(
        select(GenerationJob).where(
            GenerationJob.id == job_id, GenerationJob.user_id == user_id
        ).with_for_update()
    )
    if job is None:
        raise HTTPException(404, "Job not found")
    if job.status in {"succeeded", "failed", "cancelled"}:
        return job
    if job.status == "running":
        raise HTTPException(409, "A running job cannot be cancelled until provider cancellation is supported")
    reservation = await db.scalar(
        select(CreditReservation).where(CreditReservation.job_id == job.id).with_for_update()
    )
    if reservation is not None and reservation.status == "reserved":
        await change_credits(
            db, user_id, reservation.reserved_amount, "refund",
            f"job-refund:{job.id}", str(job.id)
        )
        reservation.status = "refunded"
        reservation.settled_amount = 0
    job.status = "cancelled"
    await db.flush()
    return job
