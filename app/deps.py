import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer(auto_error=False)


def current_user(cred: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if cred is None:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(cred.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(401, "User not found")
    return user


def require_coach(user: User = Depends(current_user)) -> User:
    if user.role != "coach":
        raise HTTPException(403, "Coach only")
    return user


def require_student(user: User = Depends(current_user)) -> User:
    if user.role != "student":
        raise HTTPException(403, "Student only")
    return user


def coach_student(student_id: str, coach: User = Depends(require_coach), db: Session = Depends(get_db)) -> User:
    """Resolve {student_id} and make sure it belongs to this coach."""
    s = db.get(User, student_id)
    if s is None or s.role != "student" or s.coach_id != coach.id:
        raise HTTPException(404, "Student not found")
    return s
