from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.config import settings
from app.db import engine
from app.routers import router
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["GET","POST","DELETE"], allow_headers=["Authorization","Content-Type","Idempotency-Key"])
app.include_router(router, prefix=settings.api_prefix)
@app.get("/health/live")
async def live(): return {"status":"ok"}
@app.get("/health/ready")
async def ready():
    async with engine.connect() as connection: await connection.execute(text("SELECT 1"))
    return {"status":"ready"}
