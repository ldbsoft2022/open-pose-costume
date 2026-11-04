import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.models import CreditAccount, CreditTransaction
async def change_credits(db: AsyncSession, user_id: uuid.UUID, amount: int, kind: str, key: str, reference_id: str | None = None) -> int:
    if amount == 0: raise ValueError("Credit change cannot be zero")
    existing = await db.scalar(select(CreditTransaction).where(CreditTransaction.idempotency_key == key))
    if existing:
        if existing.user_id != user_id or existing.amount != amount: raise HTTPException(409, "Idempotency key already used for a different operation")
        return existing.balance_after
    account = await db.scalar(select(CreditAccount).where(CreditAccount.user_id == user_id).with_for_update())
    if account is None: raise HTTPException(404, "Credit account not found")
    new_balance = account.balance + amount
    if new_balance < 0: raise HTTPException(402, "Insufficient credits")
    account.balance = new_balance
    db.add(CreditTransaction(user_id=user_id, amount=amount, balance_after=new_balance, kind=kind, idempotency_key=key, reference_id=reference_id))
    await db.flush()
    return new_balance
