import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..db import get_db
from ..deps import coach_student, require_coach
from ..models import PlanItem, User
from ..schemas import ItemIn, ItemPatch, StudentCreate, valid_hhmm
from ..security import hash_password

router = APIRouter(prefix="/coach", tags=["coach"])


@router.post("/students", status_code=201)
def create_student(body: StudentCreate, coach: User = Depends(require_coach), db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(409, "Email already registered")
    s = User(email=email, name=body.name.strip(), password_hash=hash_password(body.password),
             role="student", coach_id=coach.id)
    db.add(s)
    db.commit()
    return {"id": s.id, "name": s.name, "email": s.email}


@router.get("/students")
def list_students(coach: User = Depends(require_coach), db: Session = Depends(get_db)):
    rows = db.scalars(select(User).where(User.coach_id == coach.id, User.role == "student").order_by(User.name))
    day = services.today()
    return [{"id": s.id, "name": s.name, "email": s.email, "today": services.adherence(db, s.id, day)} for s in rows]


@router.get("/students/{student_id}/plan")
def get_plan(student: User = Depends(coach_student), db: Session = Depends(get_db)):
    return [services.item_dict(i) for i in services.plan_items(db, student.id, include_inactive=True)]


def _check_slot(kind: str, slot: str):
    if kind in services.TRACKED and slot and not valid_hhmm(slot):
        raise HTTPException(422, "slot must be HH:MM for meals and supplements")


@router.post("/students/{student_id}/plan/items", status_code=201)
def add_item(body: ItemIn, student: User = Depends(coach_student), db: Session = Depends(get_db)):
    _check_slot(body.kind, body.slot)
    last = db.scalars(select(PlanItem.position).where(PlanItem.student_id == student.id)).all()
    i = PlanItem(student_id=student.id, kind=body.kind, slot=body.slot, title=body.title.strip(),
                 details=json.dumps(body.details, ensure_ascii=False), position=(max(last) + 1) if last else 0)
    db.add(i)
    db.commit()
    return services.item_dict(i)


@router.patch("/plan/items/{item_id}")
def patch_item(item_id: str, body: ItemPatch, coach: User = Depends(require_coach), db: Session = Depends(get_db)):
    i = db.get(PlanItem, item_id)
    owner = db.get(User, i.student_id) if i else None
    if not i or owner.coach_id != coach.id:
        raise HTTPException(404, "Item not found")
    data = body.model_dump(exclude_unset=True)
    if "slot" in data:
        _check_slot(i.kind, data["slot"])
    if "details" in data:
        data["details"] = json.dumps(data["details"], ensure_ascii=False)
    for k, v in data.items():
        setattr(i, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return services.item_dict(i)


@router.delete("/plan/items/{item_id}", status_code=204)
def delete_item(item_id: str, coach: User = Depends(require_coach), db: Session = Depends(get_db)):
    """Soft delete (active=false) so past check-ins keep their meaning."""
    i = db.get(PlanItem, item_id)
    owner = db.get(User, i.student_id) if i else None
    if not i or owner.coach_id != coach.id:
        raise HTTPException(404, "Item not found")
    i.active = False
    db.commit()


@router.get("/students/{student_id}/summary")
def summary(days: int = 7, student: User = Depends(coach_student), db: Session = Depends(get_db)):
    return {"student": {"id": student.id, "name": student.name},
            "history": services.history(db, student.id, max(1, min(days, 90)))}
