import io


def H(token):
    return {"Authorization": f"Bearer {token}"}


def register_coach(c, email):
    r = c.post("/auth/register-coach", json={"name": "Navid", "email": email, "password": "password123", "invite_code": "test-invite"})
    assert r.status_code == 201, r.text
    return r.json()["token"]


def test_full_flow(client):
    c = client
    assert c.post("/auth/register-coach", json={"name": "x", "email": "x@x.com", "password": "password123", "invite_code": "bad"}).status_code == 403
    coach = register_coach(c, "navid@example.com")

    r = c.post("/coach/students", json={"name": "Ali", "email": "ali@example.com", "password": "password123"}, headers=H(coach))
    assert r.status_code == 201
    sid = r.json()["id"]

    def add(kind, slot, title):
        r = c.post(f"/coach/students/{sid}/plan/items", json={"kind": kind, "slot": slot, "title": title}, headers=H(coach))
        assert r.status_code == 201, r.text
        return r.json()["id"]

    meal = add("meal", "08:00", "breakfast")
    supp = add("supplement", "09:00", "multivitamin")
    train = add("training", "Sat", "upper body")
    assert c.post(f"/coach/students/{sid}/plan/items", json={"kind": "meal", "slot": "8am", "title": "bad"}, headers=H(coach)).status_code == 422

    tok = c.post("/auth/login", json={"email": "ALI@example.com", "password": "password123"}).json()["token"]
    today = c.get("/student/today", headers=H(tok)).json()
    assert len(today["items"]) == 3 and today["adherence"] == {"done": 0, "total": 2, "percent": 0}

    assert c.put(f"/student/today/checks/{meal}", headers=H(tok)).status_code == 422  # meal needs photo
    assert c.put(f"/student/today/checks/{train}", headers=H(tok)).status_code == 404  # training not checkable
    r = c.put(f"/student/today/checks/{supp}", headers=H(tok))
    assert r.json()["adherence"]["percent"] == 50
    r = c.put(f"/student/today/checks/{meal}", headers=H(tok), files={"photo": ("a.jpg", io.BytesIO(b"\xff\xd8fake"), "image/jpeg")})
    assert r.json()["adherence"]["percent"] == 100
    check_id = next(i["check_id"] for i in r.json()["items"] if i["id"] == meal)
    assert c.get(f"/photos/{check_id}", headers=H(tok)).status_code == 200
    assert c.get(f"/photos/{check_id}", headers=H(coach)).status_code == 200

    assert c.delete(f"/student/today/checks/{supp}", headers=H(tok)).json()["adherence"]["percent"] == 50
    r = c.put("/student/today/mood", json={"mood": "tired", "note": "weak"}, headers=H(tok)).json()
    assert r["mood"] == "tired"
    r = c.post("/student/today/gym", json={"action": "in"}, headers=H(tok)).json()
    assert r["gym_in"] and not r["gym_out"]

    s = c.get(f"/coach/students/{sid}/summary?days=3", headers=H(coach)).json()
    assert len(s["history"]) == 3 and s["history"][0]["mood"] == "tired"
    assert c.get("/coach/students", headers=H(coach)).json()[0]["today"]["percent"] == 50

    # editing keeps the id (check-ins keep their meaning); delete is soft
    r = c.patch(f"/coach/plan/items/{meal}", json={"title": "big breakfast"}, headers=H(coach))
    assert r.json()["id"] == meal and r.json()["title"] == "big breakfast"
    assert c.delete(f"/coach/plan/items/{supp}", headers=H(coach)).status_code == 204
    assert len(c.get("/student/today", headers=H(tok)).json()["items"]) == 2


def test_permissions(client):
    c = client
    coach1 = register_coach(c, "c1@example.com")
    coach2 = register_coach(c, "c2@example.com")
    sid = c.post("/coach/students", json={"name": "Sara", "email": "sara@example.com", "password": "password123"}, headers=H(coach1)).json()["id"]
    stok = c.post("/auth/login", json={"email": "sara@example.com", "password": "password123"}).json()["token"]

    assert c.get(f"/coach/students/{sid}/plan", headers=H(coach2)).status_code == 404  # other coach
    assert c.get(f"/coach/students/{sid}/plan", headers=H(stok)).status_code == 403    # student
    assert c.get("/student/today", headers=H(coach1)).status_code == 403
    assert c.get("/student/today").status_code == 401
    assert c.post("/auth/login", json={"email": "sara@example.com", "password": "wrong-pass"}).status_code == 401


def test_bad_hash_is_401_and_cli_creates_coach(client):
    from app.create_coach import create_coach
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        db.add(User(email="hand@example.com", name="Hand", password_hash="plain-text", role="coach"))
        db.add(User(email="hand2@example.com", name="Hand2", password_hash="zz$yy", role="coach"))
        db.commit()
        create_coach(db, "cli@example.com", "Cli", "password123")
    for e in ("hand@example.com", "hand2@example.com"):
        assert client.post("/auth/login", json={"email": e, "password": "whatever1"}).status_code == 401
    r = client.post("/auth/login", json={"email": "cli@example.com", "password": "password123"})
    assert r.status_code == 200 and r.json()["user"]["role"] == "coach"
