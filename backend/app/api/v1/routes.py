from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.college import College
from app.schemas.college import CollegeCreate, CollegeResponse

router = APIRouter()


@router.get("/colleges", response_model=list[CollegeResponse])
def get_colleges(db: Session = Depends(get_db)):
    return db.query(College).all()


@router.post("/colleges", response_model=CollegeResponse)
def create_college(payload: CollegeCreate, db: Session = Depends(get_db)):
    college = College(**payload.model_dump())
    db.add(college)
    db.commit()
    db.refresh(college)
    return college