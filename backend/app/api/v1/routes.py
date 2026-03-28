import sys
import os
import math
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.models.college import College
from app.models.cutoff import Cutoff
from app.schemas.college import (
    CollegeCreate,
    CollegeResponse,
    PredictResult,
    PredictResponse,
)

router = APIRouter()


# ── ML Model Import Setup ───────────────────────────────────────────────
ml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../ML"))
if ml_path not in sys.path:
    sys.path.append(ml_path)

try:
    from percentile_model import predict_rank as predict_rank_from_percentile
except ImportError:
    print("Warning: Could not import percentile_model.")
    def predict_rank_from_percentile(percentile, year):
        return 999999


# ── JEE Marks → Rank Logic ───────────────────────────────────────────────
OFFICIAL_STUDENT_DATA = {
    2022: 905000,
    2023: 1113000,
    2024: 1170000,
    2025: 1200000,
}
GROWTH_RATE = 0.04

def get_student_count(year: int) -> int:
    if year in OFFICIAL_STUDENT_DATA:
        return OFFICIAL_STUDENT_DATA[year]
    last_year = max(OFFICIAL_STUDENT_DATA.keys())
    last_count = OFFICIAL_STUDENT_DATA[last_year]
    return int(last_count * ((1 + GROWTH_RATE) ** (year - last_year)))


def predict_rank_from_marks(marks: float, year: int) -> int:
    if marks < 0 or marks > 300:
        raise ValueError("Marks must be between 0 and 300 for JEE Mains.")
    base_total = OFFICIAL_STUDENT_DATA[2024]
    A = base_total
    B = math.log(A) / 300
    base_rank = A * math.exp(-B * marks)
    year_total = get_student_count(year)
    scaled_rank = base_rank * (year_total / base_total)
    return max(1, math.ceil(scaled_rank))


# ── Response Schemas ─────────────────────────────────────────────────────

class RankPredictionResponse(BaseModel):
    exam: str
    marks: float
    year: int
    predicted_rank: int
    total_students: int


# ── Helper ───────────────────────────────────────────────────────────────

def to_predict_result(college: College, cutoff: Cutoff, rank: int) -> PredictResult:
    opening = cutoff.opening_rank  # can be None
    closing = cutoff.closing_rank or 0

    if closing == 0:
        chance = "Risky"
    elif opening is None:
        # No opening rank data — if rank beats closing, Safe (can't be Moderate without opening)
        chance = "Safe" if rank <= closing else "Risky"
    elif rank <= opening:
        chance = "Safe"
    elif rank <= closing:
        chance = "Moderate"
    else:
        chance = "Risky"

    course_display = college.course
    if cutoff.special and str(cutoff.special).strip().lower() not in ["", "nan", "none", "null"]:
        course_display = f"{college.course} ({cutoff.special})"

    return PredictResult(
        college      = college.name,
        state        = college.state,
        type         = college.type,
        course       = course_display,
        naac_grade   = college.naac_grade,
        fees_lpa     = college.fees_lpa,
        seats        = college.seats,
        quota        = cutoff.quota,
        category     = cutoff.category,
        gender       = cutoff.gender,
        opening_rank = cutoff.opening_rank,
        closing_rank = cutoff.closing_rank,
        chance       = chance,
    )


# ── College Routes ───────────────────────────────────────────────────────

@router.get("/colleges", response_model=list[CollegeResponse])
def get_colleges(
    exam_type: Optional[str] = None, state: Optional[str] = None,
    course: Optional[str] = None, limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(College)
    if exam_type: query = query.filter(College.exam_type == exam_type.upper())
    if state:     query = query.filter(College.state == state)
    if course:    query = query.filter(College.course == course)
    return query.order_by(College.name.asc()).limit(limit).all()


@router.post("/colleges", response_model=CollegeResponse)
def create_college(payload: CollegeCreate, db: Session = Depends(get_db)):
    college = College(**payload.model_dump())
    db.add(college)
    db.commit()
    db.refresh(college)
    return college


# ── Predict Routes ───────────────────────────────────────────────────────

@router.get("/predict/neet", response_model=PredictResponse)
def predict_neet(
    rank: int = Query(...), quota: Optional[str] = Query(None),
    state: Optional[str] = Query(None), col_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(College, Cutoff).join(Cutoff, Cutoff.college_id == College.id)\
              .filter(College.exam_type == "NEET").filter(Cutoff.closing_rank >= rank)
    if quota:    query = query.filter(Cutoff.quota == quota)
    if state:    query = query.filter(College.state == state)
    if col_type: query = query.filter(College.type == col_type)

    rows = query.order_by(Cutoff.closing_rank.asc()).all()
    results = [to_predict_result(c, co, rank) for c, co in rows]

    return PredictResponse(
        count    = len(results),
        safe     = [r for r in results if r.chance == "Safe"],
        moderate = [r for r in results if r.chance == "Moderate"],
        risky    = [r for r in results if r.chance == "Risky"],
    )


@router.get("/predict/btech", response_model=PredictResponse)
def predict_btech(
    rank:     int           = Query(..., description="Your JEE rank"),
    category: str           = Query("GEN", description="GEN / OBC / SC / ST / EWS"),
    gender:   str           = Query("Male", description="Male or Female"),
    special:  Optional[str] = Query(None, description="PwD, Sports, or CW"),
    branch:   Optional[str] = Query(None, description="CSE, ECE, Mechanical etc."),
    db:       Session       = Depends(get_db),
):
    query = (
        db.query(College, Cutoff)
        .join(Cutoff, Cutoff.college_id == College.id)
        .filter(College.exam_type == "BTECH")
        .filter(Cutoff.closing_rank >= rank)
        .filter(Cutoff.category == category.upper())
    )

    allowed_genders = [gender.upper(), "ANY", "GENDER-NEUTRAL", "NEUTRAL", ""]
    query = query.filter(Cutoff.gender.in_(allowed_genders))

    if special and special.upper() != "NONE":
        query = query.filter(
            or_(
                Cutoff.special.ilike(f"%{special}%"),
                Cutoff.special.is_(None),
                Cutoff.special == "",
                Cutoff.special.ilike("nan"),
                Cutoff.special.ilike("none")
            )
        )
    else:
        query = query.filter(
            or_(
                Cutoff.special.is_(None),
                Cutoff.special == "",
                Cutoff.special.ilike("nan"),
                Cutoff.special.ilike("none")
            )
        )

    if branch:
        query = query.filter(College.course.ilike(f"%{branch}%"))

    rows = query.order_by(Cutoff.closing_rank.asc()).all()
    results = [to_predict_result(c, co, rank) for c, co in rows]

    return PredictResponse(
        count    = len(results),
        safe     = [r for r in results if r.chance == "Safe"],
        moderate = [r for r in results if r.chance == "Moderate"],
        risky    = [r for r in results if r.chance == "Risky"],
    )


# ── GET /predict-rank/jee ────────────────────────────────────────────────

@router.get("/predict-rank/jee", response_model=RankPredictionResponse)
def get_jee_rank_prediction(
    marks: float = Query(..., description="Your JEE Mains marks (0–300)"),
    year:  int   = Query(2025, description="Target year for admission"),
):
    try:
        rank  = predict_rank_from_marks(marks, year)
        total = get_student_count(year)
        return RankPredictionResponse(
            exam           = "JEE Mains",
            marks          = marks,
            year           = year,
            predicted_rank = rank,
            total_students = total,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction Error: {str(e)}")