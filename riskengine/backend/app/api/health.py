from fastapi import APIRouter

from app.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "version": s.version,
        "live_data": s.use_live_data,
        "sentiment_backend": s.sentiment_backend,
    }
