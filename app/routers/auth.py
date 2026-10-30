import hmac

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import current_user
from ..models import User
from ..schemas import Login, RegisterCoach
from ..security import create_token, hash_password, verify_password

router = APIRouter(tags=["auth"])


def _out(u: User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "coach_id": u.coach_id}


@router.post("/auth/register-coach", status_code=201)
def register_coach(body: RegisterCoach, db: Session = Depends(get_db)):
    if not settings.coach_invite_code:
        raise HTTPException(403, "COACH_INVITE_CODE is not set on the server (see .env)")
    if not hmac.compare_digest(body.invite_code, settings.coach_invite_code):
        raise HTTPException(403, "Invalid invite code")
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    u = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password), role="coach")
    db.add(u)
    db.commit()
    return {"token": create_token(u.id, u.role), "user": _out(u)}


@router.post("/auth/login")
def login(body: Login, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Wrong email or password")
    return {"token": create_token(u.id, u.role), "user": _out(u)}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return _out(user)
