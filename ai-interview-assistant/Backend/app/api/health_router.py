from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.database.session import get_engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "database": "unavailable"},
        ) from exc

    return {"status": "healthy", "database": "available"}