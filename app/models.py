import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)  # "coach" | "student"
    coach_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PlanItem(Base):
    """One row of a student's plan. kind: meal | supplement | training.
    slot = time "HH:MM" for meal/supplement, weekday label for training.
    details = free JSON (dose, macros, sets/reps, video...) filled in later without migrations."""
    __tablename__ = "plan_items"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String)
    slot: Mapped[str] = mapped_column(String, default="")
    title: Mapped[str] = mapped_column(String, default="")
    details: Mapped[str] = mapped_column(Text, default="{}")
    position: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ItemCheck(Base):
    """Student marked a plan item done on a given day (meals carry a photo)."""
    __tablename__ = "item_checks"
    __table_args__ = (UniqueConstraint("student_id", "item_id", "day"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_id)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    item_id: Mapped[str] = mapped_column(String, index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    done_at: Mapped[str] = mapped_column(String)  # "HH:MM" local
    photo_path: Mapped[str | None] = mapped_column(String, nullable=True)


class DayLog(Base):
    __tablename__ = "day_logs"
    __table_args__ = (UniqueConstraint("student_id", "day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    day: Mapped[date] = mapped_column(Date, index=True)
    mood: Mapped[str] = mapped_column(String, default="")
    mood_note: Mapped[str] = mapped_column(String, default="")
    gym_in: Mapped[str] = mapped_column(String, default="")
    gym_out: Mapped[str] = mapped_column(String, default="")
