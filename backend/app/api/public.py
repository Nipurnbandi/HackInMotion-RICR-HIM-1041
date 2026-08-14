from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.public import TransparencyResponse
from app.services.transparency import build_transparency_report

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/transparency", response_model=TransparencyResponse)
def public_transparency(db: Session = Depends(get_db)):
    """Public report card — no authentication required, computed live."""
    return build_transparency_report(db)
