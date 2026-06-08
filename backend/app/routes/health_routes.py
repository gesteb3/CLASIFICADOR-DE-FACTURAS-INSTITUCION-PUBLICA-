import httpx
from fastapi import APIRouter
from sqlalchemy import text
from app.core.config import get_settings
from app.database import SessionLocal
from app.queues.redis_queue import get_redis_connection

router = APIRouter(prefix="/health", tags=["Health"])
settings = get_settings()


@router.get("")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@router.get("/postgres")
def postgres_health():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "postgres"}
    finally:
        db.close()


@router.get("/redis")
def redis_health():
    redis_conn = get_redis_connection()
    redis_conn.ping()
    return {"status": "ok", "redis": "connected"}


@router.get("/ollama")
def ollama_health():
    response = httpx.get(f"{settings.ollama_host}/api/tags", timeout=10)
    response.raise_for_status()
    return {
        "status": "ok",
        "ollama": "connected",
        "model": settings.ollama_model,
        "available_models": response.json().get("models", []),
    }
