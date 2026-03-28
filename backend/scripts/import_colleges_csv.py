import argparse
import csv
import sys
from app.db.session import SessionLocal
from app.models.college import College
from app.models.cutoff import Cutoff

parser = argparse.ArgumentParser()
parser.add_argument("--csv", required=True)
parser.add_argument("--exam-type", required=True)
args = parser.parse_args()
exam_type = args.exam_type.upper()

db = SessionLocal()
loaded_colleges = 0
loaded_cutoffs  = 0

try:
    existing = db.query(College).filter(College.exam_type == exam_type).all()
    for col in existing:
        db.query(Cutoff).filter(Cutoff.college_id == col.id).delete()
    db.query(College).filter(College.exam_type == exam_type).delete()
    db.commit()
    print(f"Cleared old {exam_type} data")

    with open(args.csv, newline='', encoding='utf-8-sig') as f:
        sample = f.read(1024)
        f.seek(0)
        delim = '\t' if '\t' in sample else ','
        
        reader = csv.DictReader(f, delimiter=delim)
        
        for i, row in enumerate(reader):
            try:
                lower_row = {k.lower().strip() if k else '': v for k, v in row.items()}
                
                name = (lower_row.get("college") or lower_row.get("institute") or "").strip()
                if not name:
                    continue

                course = (lower_row.get("branch") or lower_row.get("course") or "").strip()
                
                raw_category = (lower_row.get("category") or "GEN").upper().strip()
                raw_gender   = (lower_row.get("gender") or "ANY").upper().strip()
                raw_special  = (lower_row.get("special") or "").strip()

                quota = None
                category = "GEN"
                gender = "MALE"
                special = None

                # ---------------------------------------------------------
                # SMART ALIGNMENT: Fix NSUT/IIITD shifted columns
                # ---------------------------------------------------------
                if raw_category in ["HS", "OS", "AI"]:
                    quota = raw_category
                    
                    # Extract Category and Special (PwD/CW) from the shifted gender column
                    if "(PWD)" in raw_gender:
                        special = "PwD"
                        category = raw_gender.replace("(PWD)", "").strip()
                    elif "CW" in raw_gender:
                        special = "CW"
                        category = raw_gender.replace("CW", "").strip()
                    else:
                        special = None
                        category = raw_gender

                    # Extract actual Gender from the shifted special column
                    if "FEMALE" in raw_special.upper():
                        gender = "FEMALE"
                    else:
                        gender = "MALE" # Gender-Neutral maps to Male for standard prediction
                else:
                    # Standard DTU format
                    category = raw_category
                    if "FEMALE" in raw_gender:
                        gender = "FEMALE"
                    else:
                        gender = "MALE"

                    if raw_special.lower() not in ["nan", "none", ""]:
                        special = raw_special

                # ---------------------------------------------------------
                # STANDARDIZE CATEGORIES (OPEN -> GEN, OBC-NCL -> OBC)
                # ---------------------------------------------------------
                if "OPEN" in category or "GEN" in category:
                    category = "GEN"
                elif "OBC" in category:
                    category = "OBC"
                elif "EWS" in category:
                    category = "EWS"
                elif "SC" in category:
                    category = "SC"
                elif "ST" in category:
                    category = "ST"

                # Force IGDTUW to Female
                if "IGDTUW" in name.upper() or "WOMEN" in name.upper():
                    gender = "FEMALE"

                # Parse Ranks Safely
                opening_raw = (lower_row.get("opening rank") or lower_row.get("opening_rank") or "").strip()
                closing_raw = (lower_row.get("closing rank") or lower_row.get("closing_rank") or "").strip()
                
                opening = int(float(opening_raw.replace(",", ""))) if opening_raw and opening_raw.lower() != "nan" else None
                closing = int(float(closing_raw.replace(",", ""))) if closing_raw and closing_raw.lower() != "nan" else None

                if not closing:
                    continue 

                # DB Insert
                college = College(
                    name=name, state=lower_row.get("state"), type=lower_row.get("type"),
                    exam_type=exam_type, course=course,
                )
                db.add(college)
                db.flush()
                loaded_colleges += 1

                cutoff = Cutoff(
                    college_id=college.id, quota=quota, category=category, 
                    gender=gender, special=special, 
                    opening_rank=opening, closing_rank=closing,
                )
                db.add(cutoff)
                db.flush()
                loaded_cutoffs += 1

            except Exception as row_err:
                # CRITICAL POSTGRES FIX: Rollback transaction so next row can proceed
                db.rollback()
                print(f"  Row {i+1} skipped due to error: {row_err}")
                continue

    db.commit()
    print(f"\nSUCCESS! Loaded {loaded_colleges} Colleges and {loaded_cutoffs} Cutoffs.")

except Exception as e:
    db.rollback()
    print(f"Fatal error: {e}")
finally:
    db.close()