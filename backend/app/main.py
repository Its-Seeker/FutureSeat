from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.db.session import engine
from app.admin import setup_admin 

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.ADMIN_SESSION_SECRET,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_admin(app, engine)

app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

