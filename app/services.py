import json
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import DayLog, ItemCheck, PlanItem

TRACKED = ("meal", "supplement")  # kinds that count toward adherence


def local_now() -> datetime:
    return datetime.now(ZoneInfo(settings.timezone))


def today() -> date:
    return local_now().date()


def hhmm() -> str:
    return local_now().strftime("%H:%M")


def item_dict(i: PlanItem) -> dict:
    return {"id": i.id, "kind": i.kind, "slot": i.slot, "title": i.title,
            "details": json.loads(i.details or "{}"), "position": i.position, "active": i.active}


def plan_items(db: Session, student_id: str, include_inactive: bool = False) -> list[PlanItem]:
    q = select(PlanItem).where(PlanItem.student_id == student_id)
    if not include_inactive:
        q = q.where(PlanItem.active.is_(True))
    return list(db.scalars(q.order_by(PlanItem.kind, PlanItem.slot, PlanItem.position)))


def adherence(db: Session, student_id: str, day: date) -> dict:
    """done / planned for meal+supplement items. Uses the current plan (history is approximate
    if the plan changed; a versioned plan is a later step)."""
    planned = [i for i in plan_items(db, student_id) if i.kind in TRACKED and i.title]
    ids = {i.id for i in planned}
    done = db.scalars(select(ItemCheck.item_id).where(ItemCheck.student_id == student_id, ItemCheck.day == day))
    n = len(ids.intersection(done))
    return {"done": n, "total": len(planned), "percent": round(100 * n / len(planned)) if planned else 0}


def get_log(db: Session, student_id: str, day: date, create: bool = False) -> DayLog | None:
    log = db.scalar(select(DayLog).where(DayLog.student_id == student_id, DayLog.day == day))
    if log is None and create:
        log = DayLog(student_id=student_id, day=day)
        db.add(log)
        db.flush()
    return log


def day_view(db: Session, student_id: str, day: date) -> dict:
    checks = {c.item_id: c for c in db.scalars(
        select(ItemCheck).where(ItemCheck.student_id == student_id, ItemCheck.day == day))}
    log = get_log(db, student_id, day)
    items = []
    for i in plan_items(db, student_id):
        d = item_dict(i)
        c = checks.get(i.id)
        d.update(done=c is not None, done_at=c.done_at if c else None,
                 check_id=c.id if c else None, has_photo=bool(c and c.photo_path))
        items.append(d)
    return {"day": day.isoformat(), "items": items, "adherence": adherence(db, student_id, day),
            "mood": log.mood if log else "", "mood_note": log.mood_note if log else "",
            "gym_in": log.gym_in if log else "", "gym_out": log.gym_out if log else ""}


def history(db: Session, student_id: str, days: int) -> list[dict]:
    out = []
    for n in range(days):
        d = today() - timedelta(days=n)
        log = get_log(db, student_id, d)
        out.append({"day": d.isoformat(), "adherence": adherence(db, student_id, d),
                    "mood": log.mood if log else "", "gym_in": log.gym_in if log else "",
                    "gym_out": log.gym_out if log else ""})
    return out
