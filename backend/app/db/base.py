from sqlalchemy.orm import DeclarativeBase
from app.db.base_class import Base

import app.models.college
import app.models.cutoff

class Base(DeclarativeBase):
    pass