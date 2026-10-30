# Navid API (MVP)

بک‌اند نسخه اول پروژه نوید: FastAPI + SQLAlchemy (SQLite برای توسعه، Postgres بعداً) + JWT.

## اجرا
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # JWT_SECRET و COACH_INVITE_CODE رو عوض کن (خودکار خونده میشه)
python -m app.create_coach --email you@example.com --name Navid   # ساخت اولین مربی، بدون کد دعوت
uvicorn app.main:app --reload --port 8000
```
مستندات تعاملی: http://localhost:8000/docs · فرانت فعلی (web/index.html) روی / سرو میشه.

اگه دیتابیس رو دستی دستکاری کردی و لاگین نمیشه: ردیف دستی رو پاک کن یا با `--force` دوباره بساز (هش پسورد باید با همین برنامه ساخته بشه، نه متن ساده).

## تست
```bash
pytest -q
```

## ساختار
```
app/
  config.py      تنظیمات از env
  db.py          engine و session
  models.py      User, PlanItem, ItemCheck, DayLog
  security.py    هش پسورد و JWT
  deps.py        احراز هویت و نقش‌ها (coach / student)
  services.py    پایبندی، نمای روز، تاریخچه
  schemas.py     ورودی‌های API
  routers/       auth.py · coach.py · student.py
tests/           جریان کامل + دسترسی‌ها
web/             فرانت MVP (PWA ساده، به API وصل است؛ باید از همین سرور باز شود)
```

## API
| نقش | مسیر | کار |
|---|---|---|
| - | POST /auth/register-coach | ثبت مربی با کد دعوت |
| - | POST /auth/login | ورود، برمی‌گردونه token |
| هر دو | GET /me | کاربر فعلی |
| مربی | POST/GET /coach/students | ساخت و لیست شاگردها (با درصد امروز) |
| مربی | GET /coach/students/{id}/plan | برنامه شاگرد |
| مربی | POST /coach/students/{id}/plan/items | آیتم جدید (kind: meal / supplement / training) |
| مربی | PATCH / DELETE /coach/plan/items/{id} | ویرایش و حذف نرم |
| مربی | GET /coach/students/{id}/summary?days=7 | پایبندی، حال و باشگاه |
| شاگرد | GET /student/today | آیتم‌ها، پایبندی، حال، باشگاه |
| شاگرد | PUT/DELETE /student/today/checks/{item_id} | ثبت یا لغو (وعده بدون عکس رد میشه) |
| شاگرد | PUT /student/today/mood · POST /student/today/gym | حال امروز و ورود/خروج |
| هر دو | GET /photos/{check_id} | عکس وعده (فقط خود شاگرد و مربی‌اش) |

## تصمیم‌های طراحی
- هر آیتم برنامه یه ردیف با id ثابته؛ ویرایش عنوان و ساعت سابقه ثبت‌ها رو حفظ می‌کنه، و حذف فقط `active=false` می‌کنه.
- `details` یه JSON آزاده برای جزئیات بعدی آیتم‌ها (دوز، ماکرو، ست و تکرار، ویدیو) بدون migration.
- درصد پایبندی = وعده‌ها و مکمل‌های انجام‌شده ÷ برنامه فعلی. تمرین فعلاً حساب نمیشه. برای تاریخچه دقیق بعد از تغییر برنامه، نسخه‌بندی برنامه لازمه.
- ساعت‌ها با `TIMEZONE` (پیش‌فرض Asia/Tehran) حساب میشن.

## قبل از کاربر واقعی
- Alembic به‌جای `create_all`، و Postgres.
- ذخیره عکس روی object storage (الان دیسک محلی)، و ریسایز سمت سرور.
- محدودیت تعداد درخواست لاگین، ریست پسورد، HTTPS، و تصمیم درباره نگهداری داده سلامت (حریم خصوصی و قوانین کشور هدف).
