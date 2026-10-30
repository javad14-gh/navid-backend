import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .db import Base, engine
from .routers import auth, coach, student

Base.metadata.create_all(engine)  # MVP only; switch to Alembic migrations before real users

app = FastAPI(title="Navid API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
app.include_router(coach.router)
app.include_router(student.router)


@app.get("/health")
def health():
    return {"ok": True}


_web = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.isdir(_web):  # serves the PWA at / (registered last so API routes win)
    app.mount("/", StaticFiles(directory=_web, html=True), name="web")
