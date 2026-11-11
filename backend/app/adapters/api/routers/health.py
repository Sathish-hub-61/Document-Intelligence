"""
Health check endpoint reporting database, Chroma, and LLM status.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.adapters.api.schemas.common import HealthResponse
from app.adapters.persistence.database import get_db
from app.composition.settings import get_settings

router = APIRouter(prefix="/api", tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    settings = get_settings()

    # Check Database
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unreachable: {str(e)}"

    # Check Chroma
    chroma_status = "ok"
    # Placeholder or directory check for Phase 0
    import os
    if not os.path.exists(settings.chroma_path):
        os.makedirs(settings.chroma_path, exist_ok=True)

    # Check LLM
    llm_status = f"configured ({settings.llm_provider})"

    overall = "ok" if db_status == "ok" else "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        chroma=chroma_status,
        llm=llm_status,
    )
