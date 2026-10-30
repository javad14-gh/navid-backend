"""Create (or reset) a coach account without the invite code.
Usage: python -m app.create_coach --email navid@example.com --name Navid [--force]
The password is asked interactively (never stored in shell history)."""
import argparse
import getpass
import sys

from sqlalchemy import select

from .db import Base, SessionLocal, engine
from .models import User
from .security import hash_password


def create_coach(db, email: str, name: str, password: str, force: bool = False) -> str:
    email = email.strip().lower()
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    u = db.scalar(select(User).where(User.email == email))
    if u and not force:
        raise ValueError("this email already exists; use --force to reset its password and make it a coach")
    if u:
        u.password_hash, u.role, u.name, u.coach_id = hash_password(password), "coach", name, None
    else:
        db.add(User(email=email, name=name, password_hash=hash_password(password), role="coach"))
    db.commit()
    return email


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    pw = getpass.getpass("Password (min 8 chars): ")
    if pw != getpass.getpass("Repeat: "):
        sys.exit("Passwords differ")
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        try:
            print("Coach ready:", create_coach(db, a.email, a.name, pw, a.force))
        except ValueError as e:
            sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
