import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import services
from ..config import settings
from ..db import get_db
from ..deps import current_user, require_student
from ..models import ItemCheck, PlanItem, User
from ..schemas import GymIn, MoodIn

router = APIRouter(tags=["student"])


@router.get("/student/today")
def today_view(s: User = Depends(require_student), db: Session = Depends(get_db)):
    return services.day_view(db, s.id, services.today())


@router.get("/student/history")
def my_history(days: int = 7, s: User = Depends(require_student), db: Session = Depends(get_db)):
    return services.history(db, s.id, max(1, min(days, 90)))


@router.put("/student/today/checks/{item_id}")
async def check_item(item_id: str, photo: UploadFile | None = File(default=None),
                     s: User = Depends(require_student), db: Session = Depends(get_db)):
    item = db.get(PlanItem, item_id)
    if not item or item.student_id != s.id or not item.active or item.kind == "training":
        raise HTTPException(404, "Item not found")
    path = None
    if photo is not None:
        if not (photo.content_type or "").startswith("image/"):
            raise HTTPException(422, "photo must be an image")
        data = await photo.read()
        if len(data) > settings.max_photo_bytes:
            raise HTTPException(413, "photo too large")
        folder = os.path.join(settings.upload_dir, s.id)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, uuid.uuid4().hex + ".jpg")
        with open(path, "wb") as f:
            f.write(data)
    elif item.kind == "meal":
        raise HTTPException(422, "meals need a photo")
    day = services.today()
    c = db.scalar(select(ItemCheck).where(ItemCheck.student_id == s.id, ItemCheck.item_id == item_id, ItemCheck.day == day))
    if c is None:
        c = ItemCheck(student_id=s.id, item_id=item_id, day=day, done_at=services.hhmm(), photo_path=path)
        db.add(c)
    elif path:
        c.photo_path = path
    db.commit()
    return services.day_view(db, s.id, day)


@router.delete("/student/today/checks/{item_id}")
def uncheck_item(item_id: str, s: User = Depends(require_student), db: Session = Depends(get_db)):
    day = services.today()
    c = db.scalar(select(ItemCheck).where(ItemCheck.student_id == s.id, ItemCheck.item_id == item_id, ItemCheck.day == day))
    if c:
        db.delete(c)
        db.commit()
    return services.day_view(db, s.id, day)


@router.put("/student/today/mood")
def set_mood(body: MoodIn, s: User = Depends(require_student), db: Session = Depends(get_db)):
    day = services.today()
    log = services.get_log(db, s.id, day, create=True)
    log.mood, log.mood_note = body.mood, body.note
    db.commit()
    return services.day_view(db, s.id, day)


@router.post("/student/today/gym")
def gym(body: GymIn, s: User = Depends(require_student), db: Session = Depends(get_db)):
    day = services.today()
    log = services.get_log(db, s.id, day, create=True)
    setattr(log, "gym_" + body.action, services.hhmm())
    db.commit()
    return services.day_view(db, s.id, day)


@router.get("/photos/{check_id}")
def photo(check_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    c = db.get(ItemCheck, check_id)
    if not c or not c.photo_path or not os.path.exists(c.photo_path):
        raise HTTPException(404, "No photo")
    owner = db.get(User, c.student_id)
    if user.id != owner.id and user.id != owner.coach_id:
        raise HTTPException(404, "No photo")
    return FileResponse(c.photo_path, media_type="image/jpeg")
