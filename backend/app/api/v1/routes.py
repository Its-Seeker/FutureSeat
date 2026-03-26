from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.college import College
from app.schemas.college import (
    CollegeCreate,
    CollegeResponse,
    PredictRequest,
    PredictResponse,
)

router = APIRouter()


@router.get("/colleges", response_model=list[CollegeResponse])
def get_colleges(
    branch: str | None = None,
    max_rank: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(College)
    if branch:
        query = query.filter(College.branch == branch)
    if max_rank is not None:
        query = query.filter(College.cutoff_rank <= max_rank)
    return query.order_by(College.cutoff_rank.asc()).limit(limit).all()


@router.post("/colleges", response_model=CollegeResponse)
def create_college(payload: CollegeCreate, db: Session = Depends(get_db)):
    college = College(**payload.model_dump())
    db.add(college)
    db.commit()
    db.refresh(college)
    return college


@router.post("/predict/colleges", response_model=PredictResponse)
def predict_colleges(payload: PredictRequest, db: Session = Depends(get_db)):
    colleges = (
        db.query(College)
        .filter(College.branch == payload.branch)
        .order_by(College.cutoff_rank.asc())
        .all()
    )

    safe = [c for c in colleges if c.cutoff_rank >= payload.rank + 8000][:10]
    target = [
        c
        for c in colleges
        if payload.rank - 5000 <= c.cutoff_rank < payload.rank + 8000
    ][:10]
    aspirational = [c for c in colleges if c.cutoff_rank < payload.rank - 5000][:10]

    return PredictResponse(safe=safe, target=target, aspirational=aspirational)