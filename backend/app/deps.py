from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import get_db
from app.models import User
from app.security import decode_access_token
bearer = HTTPBearer(auto_error=False)
async def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: AsyncSession = Depends(get_db)) -> User:
    if credentials is None: raise HTTPException(401, "Authentication required")
    try: user_id = decode_access_token(credentials.credentials)
    except ValueError: raise HTTPException(401, "Invalid or expired access token")
    user = await db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None: raise HTTPException(401, "User not found")
    return user
