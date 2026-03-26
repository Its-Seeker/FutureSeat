import argparse
import csv

from app.db.session import SessionLocal
from app.models.college import College
from app.models.cutoff import Cutoff


parser = argparse.ArgumentParser()
parser.add_argument("--csv", required=True, help="Path to CSV file")
parser.add_argument("--exam-type", required=True, help="NEET or BTECH")

args = parser.parse_args()

db = SessionLocal()

with open(args.csv, newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)

    for row in reader:
        # ---------- COLLEGE ----------
        name = row.get("College")
        state = row.get("State")
        college_type = row.get("Type")
        course = row.get("Course")

        fees = row.get("Fees (L/yr)")
        seats = row.get("Seats")
        naac = row.get("NAAC")

        fees = float(fees) if fees else None
        seats = int(seats) if seats else None

        college = College(
            name=name,
            state=state,
            type=college_type,
            exam_type=args.exam_type.upper(),
            course=course,
            fees_lpa=fees,
            seats=seats,
            naac_grade=naac
        )

        db.add(college)
        db.flush()  # IMPORTANT

        # ---------- CUTOFF ----------
        opening = row.get("Opening Rank")
        closing = row.get("Closing Rank")

        if opening:
            opening = int(str(opening).replace(",", ""))
        if closing:
            closing = int(str(closing).replace(",", ""))

        category = (row.get("Category") or "GEN").upper().strip()
        gender = (row.get("Gender") or "ANY").upper().strip()

        cutoff = Cutoff(
            college_id=college.id,
            quota=row.get("Quota"),
            category=category,
            gender=gender,
            opening_rank=opening,
            closing_rank=closing
        )

        db.add(cutoff)

db.commit()
db.close()

print("✅ Import complete!")