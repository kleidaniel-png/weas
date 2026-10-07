"""Schnelltest aller Grundfunktionen:  python tests/test_api.py  (im Ordner backend)
Nutzt eine eigene, leere Testdatenbank – die echten Daten bleiben unberührt."""
import os, sys, tempfile, time
os.environ["LAGER_DATA_DIR"] = tempfile.mkdtemp()
os.environ["LAGER_KEYBOARD_COMMAND"] = ""
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from app import security
from app.main import app

with TestClient(app) as c:
    assert c.get("/api/auth/status").json()["needs_setup"]
    assert c.get("/api/users").status_code == 401
    assert c.post("/api/auth/setup", json={"username": "Chef", "password": "kurz"}).status_code == 400
    # Ersteinrichtung von einem anderen Rechner nur mit dem Code aus dem Datenordner
    from app.config import SETUP_CODE_FILE
    assert c.get("/api/auth/status").json()["setup_code_required"] is True
    assert c.post("/api/auth/setup", json={"username": "Dieb", "password": "geheim123"}).status_code == 403
    assert c.post("/api/auth/setup", json={"username": "Dieb", "password": "geheim123", "code": "0000-0000"}).status_code == 403
    code = SETUP_CODE_FILE.read_text().strip()
    r = c.post("/api/auth/setup", json={"username": "Chef", "full_name": "Der Chef", "password": "geheim123", "code": code.lower()})
    assert not SETUP_CODE_FILE.exists()
    assert r.status_code == 200, r.text
    assert r.json()["idle_timeout_seconds"] is None and "users.manage" in r.json()["permissions"]
    assert c.post("/api/auth/setup", json={"username": "x2", "password": "geheim123"}).status_code == 403
    roles = c.get("/api/roles").json()
    ma = next(x for x in roles if x["name"] == "Mitarbeiter")
    adm = next(x for x in roles if x["is_system"])
    r = c.post("/api/users", json={"username": "max", "role_id": ma["id"], "password": "geheim123"})
    assert r.status_code == 200, r.text
    assert c.post("/api/users", json={"username": "MAX", "role_id": ma["id"], "password": "geheim123"}).status_code == 400
    admin_id = c.get("/api/auth/me").json()["id"]
    # letzter Administrator darf nicht herabgestuft, Systemrolle nicht geändert werden
    assert c.put(f"/api/users/{admin_id}", json={"username": "chef", "role_id": ma["id"]}).status_code == 400
    assert c.put(f"/api/roles/{adm['id']}", json={"name": "Andere", "permissions": []}).status_code == 400
    assert c.delete(f"/api/roles/{ma['id']}").status_code == 400
    assert c.put("/api/settings", json={"idle_timeout_minutes": 0}).status_code == 400
    assert c.put("/api/settings", json={"idle_timeout_minutes": 2, "company_name": "Bau GmbH"}).status_code == 200
    assert c.get("/api/gibtsnicht").status_code == 404
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/login", json={"username": "max", "password": "falsch"}).status_code == 401
    r = c.post("/api/auth/login", json={"username": "Max", "password": "geheim123"})
    assert r.json()["idle_timeout_seconds"] == 120
    assert c.get("/api/users").status_code == 403 and c.get("/api/settings").status_code == 403
    # Leerlauf: nach Ablauf der Zeit ist die Sitzung serverseitig beendet
    real = time.time
    security.time.time = lambda: real() + 121
    assert c.get("/api/auth/me").status_code == 401
    security.time.time = real
    assert c.get("/api/auth/me").status_code == 401
print("ALLE TESTS OK")

# --- Lager: Artikel, Projekte, Bewegungen ------------------------------------
with TestClient(app) as c:
    assert c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).status_code == 200
    cats = {x["kind"]: x["id"] for x in c.get("/api/categories").json()}
    assert set(cats) == {"material", "werkzeug"}
    r = c.post("/api/articles", json={"name": "Zement 25 kg", "category_id": cats["material"], "unit": "Sack",
                                      "price": 4.5, "min_stock": 10, "initial_stock": 20})
    assert r.status_code == 200, r.text
    zement = r.json(); assert zement["number"] == "A-0001" and zement["stock"] == 20 and not zement["low"]
    bohr = c.post("/api/articles", json={"number": "W-1", "name": "Bohrhammer", "category_id": cats["werkzeug"],
                                         "unit": "Stück", "price": 300, "initial_stock": 2}).json()
    assert c.post("/api/articles", json={"number": "W-1", "name": "Doppelt", "category_id": cats["werkzeug"], "unit": "Stück"}).status_code == 400
    proj = c.post("/api/projects", json={"name": "Bad Müller", "customer": "Fam. Müller"}).json()
    assert proj["number"] == "P-0001"
    mv = lambda **k: c.post("/api/movements", json=k)
    assert mv(type="out", article_id=zement["id"], quantity=12, project_id=proj["id"]).status_code == 200
    assert mv(type="out", article_id=zement["id"], quantity=9).status_code == 400  # nicht genug Bestand
    assert mv(type="out", article_id=zement["id"], quantity=0).status_code == 400
    assert mv(type="return", article_id=zement["id"], quantity=2, project_id=proj["id"]).status_code == 200
    assert mv(type="out", article_id=bohr["id"], quantity=1, project_id=proj["id"]).status_code == 200
    assert mv(type="in", article_id=zement["id"], quantity=5).status_code == 200
    assert mv(type="correction", article_id=zement["id"], quantity=14).status_code == 200
    arts = {a["id"]: a for a in c.get("/api/articles").json()}
    assert arts[zement["id"]]["stock"] == 14 and arts[bohr["id"]]["stock"] == 1
    s = c.get(f"/api/projects/{proj['id']}/summary").json()
    assert s["material_cost"] == 45.0, s  # (12 - 2) Sack x 4,50 – Werkzeug zählt nicht
    assert next(i for i in s["items"] if i["kind"] == "werkzeug")["open"] == 1
    assert len(c.get(f"/api/movements?project_id={proj['id']}").json()) == 3
    assert len(c.get(f"/api/movements?article_id={zement['id']}").json()) == 5  # inkl. Anfangsbestand
    assert c.delete(f"/api/articles/{zement['id']}").status_code == 400
    assert c.delete(f"/api/projects/{proj['id']}").status_code == 400
    assert c.delete(f"/api/categories/{cats['material']}").status_code == 400
    assert c.put(f"/api/projects/{proj['id']}", json={"name": "Bad Müller", "status": "abgeschlossen"}).status_code == 200
    assert mv(type="out", article_id=zement["id"], quantity=1, project_id=proj["id"]).status_code == 400
    # Mitarbeiter: darf Ausgang buchen, aber weder Eingang noch Artikel ändern
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"username": "max", "password": "geheim123"})
    assert mv(type="out", article_id=zement["id"], quantity=1).status_code == 200
    assert mv(type="in", article_id=zement["id"], quantity=1).status_code == 403
    assert mv(type="correction", article_id=zement["id"], quantity=1).status_code == 403
    assert c.post("/api/articles", json={"name": "x", "category_id": 1, "unit": "m"}).status_code == 403
    # Benutzer mit Buchungen löschen: Buchungen bleiben mit Namen erhalten
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    max_id = next(u["id"] for u in c.get("/api/users").json() if u["username"] == "max")
    assert c.delete(f"/api/users/{max_id}").status_code == 204
    assert c.get("/api/movements?limit=1").json()[0]["user"] == "max"
print("LAGER-TESTS OK")

# --- Analyse und Live-Abgleich -----------------------------------------------
with TestClient(app) as c:
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    a = c.get("/api/analysis").json()
    assert a["kpis"]["count"] == 8 and a["kpis"]["in_value"] == 22.5, a["kpis"]   # 5 Sack x 4,50
    assert a["kpis"]["out_value"] == 12 * 4.5 + 300 + 4.5, a["kpis"]
    assert a["by_project"][0]["cost"] == 45.0 and a["top_articles"][0]["name"] == "Zement 25 kg"
    assert sum(b["count"] for b in a["series"]) == 8
    zid = next(x["id"] for x in c.get("/api/articles").json() if x["number"] == "A-0001")
    hist = c.get(f"/api/analysis?article_id={zid}").json()["stock_history"]
    assert hist[-1]["stock"] == 13 and len(hist) == 6, hist
    assert c.get(f"/api/analysis?article_id={zid}").json()["kpis"]["slow_count"] == a["kpis"]["slow_count"]
    assert c.get("/api/analysis?from=2000-01-01&to=2000-01-31").json()["kpis"]["count"] == 0
    assert c.get("/api/analysis?from=quatsch").status_code == 400
    csv_text = c.get("/api/analysis/export.csv").text
    assert csv_text.startswith("﻿Datum;Art;") and csv_text.count("\n") == 9 and ";-12;Sack;4,5;-54;" in csv_text
    # Live: Änderung wird an offene Fenster gemeldet; Hintergrundabrufe verlängern die Sitzung nicht
    with c.websocket_connect("/api/ws") as ws:
        c.post("/api/projects", json={"name": "Live-Test"})
        assert ws.receive_json() == {"resource": "projects"}
    from app.database import SessionLocal
    from app.models import Session
    seen = lambda: SessionLocal().query(Session).order_by(Session.id.desc()).first().last_seen
    before = seen(); time.sleep(0.05)
    c.get("/api/articles", headers={"X-Background": "1"}); assert seen() == before
    c.get("/api/articles"); assert seen() > before
    c.post("/api/auth/logout")
    try:
        with c.websocket_connect("/api/ws") as ws:
            ws.receive_json()
        raise SystemExit("WebSocket ohne Anmeldung darf nicht funktionieren")
    except Exception as e:
        assert "4401" in repr(e) or getattr(e, "code", None) == 4401, repr(e)
print("ANALYSE- UND LIVE-TESTS OK")

# --- Sprachen, Terminal, Sicherung, Scanner, Migration -------------------------
from app import keyboard
from app.database import engine, migrate
from sqlalchemy import text

with TestClient(app) as c:
    st = c.get("/api/auth/status").json()
    assert list(st["languages"]) == ["de", "en", "ru", "uk"]
    me = c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).json()
    assert me["language"] == "de" and me["is_terminal"] is False and me["features"]["scanner"] is True
    assert c.put("/api/auth/language", json={"language": "xx"}).status_code == 400
    assert c.put("/api/auth/language", json={"language": "uk"}).json()["language"] == "uk"
    ma = next(x for x in c.get("/api/roles").json() if x["name"] == "Mitarbeiter")
    r = c.post("/api/users", json={"username": "oleg", "role_id": ma["id"], "password": "geheim123",
                                   "language": "ru", "is_terminal": True})
    assert r.status_code == 200 and r.json()["is_terminal"] and r.json()["language"] == "ru", r.text
    # Einstellungen: Scanner abschalten, ungültige Auswahl abweisen
    assert c.put("/api/settings", json={"scanner_enabled": False}).status_code == 200
    assert c.get("/api/auth/me").json()["features"]["scanner"] is False
    assert c.put("/api/settings", json={"terminal_language": "xx"}).status_code == 400
    assert c.put("/api/settings", json={"terminal_language": "en", "scanner_enabled": True}).status_code == 200
    # Datensicherung: Datei entsteht, ist eine lesbare Datenbank, alte werden gelöscht
    from app.config import BACKUP_DIR
    BACKUP_DIR.mkdir(exist_ok=True)
    (BACKUP_DIR / "lager-2020-01-01.db").write_text("alt")
    (BACKUP_DIR / "notizen.txt").write_text("fremd")
    info = c.post("/api/backup").json()
    assert len(info["backups"]) == 1 and info["backups"][0]["size"] > 10000, info
    import sqlite3
    assert sqlite3.connect(BACKUP_DIR / info["backups"][0]["name"]).execute("select count(*) from articles").fetchone()[0] == 2
    assert (BACKUP_DIR / "notizen.txt").exists()
    # Tastatur: nur am Terminal (Anfrage vom Server selbst) und nur für Terminal-Benutzer
    calls = []
    keyboard._apply = calls.append
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"username": "oleg", "password": "geheim123"})
    assert calls == []                                   # Anfrage kommt nicht vom Terminal
    keyboard.is_terminal = lambda request: True
    c.post("/api/auth/logout"); assert calls == ["us"]    # zurück auf Einstellung (en)
    c.post("/api/auth/login", json={"username": "oleg", "password": "geheim123"}); assert calls[-1] == "ru,us"
    c.put("/api/auth/language", json={"language": "uk"}); assert calls[-1] == "ua,us"
    c.post("/api/auth/logout"); assert calls[-1] == "us"
    n = len(calls)
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}); assert len(calls) == n  # kein Terminal-Benutzer
    # Migration: fehlende Spalte wird ergänzt, vorhandene Zeilen bekommen den Standardwert
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users DROP COLUMN language"))
    migrate()
    with engine.begin() as conn:
        assert {row[0] for row in conn.execute(text("SELECT language FROM users"))} == {"de"}
print("SPRACHE-, TERMINAL- UND SICHERUNGSTESTS OK")

# --- Artikelbilder -----------------------------------------------------------
import base64
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
with TestClient(app) as c:
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    art = c.get("/api/articles").json()[0]
    assert art["image"] is None and c.get(f"/api/articles/{art['id']}/image").status_code == 404
    url = f"/api/articles/{art['id']}/image"
    assert c.put(url, json={"data": "kein base64!"}).status_code == 400
    assert c.put(url, json={"data": base64.b64encode(b"<script>alert(1)</script>").decode()}).status_code == 400
    assert c.put(url, json={"data": base64.b64encode(b"\xff\xd8\xff" + b"0" * 2_100_000).decode()}).status_code == 400
    r = c.put(url, json={"data": "data:image/png;base64," + base64.b64encode(PNG).decode()})
    assert r.status_code == 200 and r.json()["image"].startswith(url + "?v="), r.text
    got = c.get(r.json()["image"])
    assert got.content == PNG and got.headers["content-type"] == "image/png"
    assert next(a for a in c.get("/api/articles").json() if a["id"] == art["id"])["image"] == r.json()["image"]
    assert c.put("/api/articles/99999/image", json={"data": base64.b64encode(PNG).decode()}).status_code == 404
    assert c.delete(url).status_code == 204 and c.get(url).status_code == 404
    # Ohne Recht „Artikel bearbeiten“ kein Hochladen; Bild verschwindet mit dem Artikel
    cat = c.get("/api/categories").json()[0]["id"]
    neu = c.post("/api/articles", json={"name": "Bildtest", "category_id": cat, "unit": "Stück"}).json()
    assert c.put(f"/api/articles/{neu['id']}/image", json={"data": base64.b64encode(PNG).decode()}).status_code == 200
    assert c.delete(f"/api/articles/{neu['id']}").status_code == 204
    with engine.begin() as conn:
        assert conn.execute(text("SELECT count(*) FROM article_images")).scalar() == 0
    c.post("/api/auth/logout")
    c.post("/api/auth/login", json={"username": "oleg", "password": "geheim123"})
    assert c.put(url, json={"data": base64.b64encode(PNG).decode()}).status_code == 403
print("BILD-TESTS OK")

# --- Sicherheit ---------------------------------------------------------------
from app.routers.auth import limiter
from app.security import hash_password, needs_rehash, verify_password
RAW = {"Content-Type": "application/json"}
with TestClient(app, raise_server_exceptions=False) as c:
    # API-Dokumentation ist aus; Schutz-Header sind gesetzt
    assert c.get("/openapi.json").headers["content-type"].startswith("text/html")   # liefert nur die Oberfläche
    assert b"swagger" not in c.get("/docs").content.lower()
    h = c.get("/").headers
    assert h["x-frame-options"] == "DENY" and h["x-content-type-options"] == "nosniff" and "default-src 'self'" in h["content-security-policy"]
    assert c.get("/api/auth/status").headers["cache-control"] == "no-store"
    # Pfade außerhalb des Programmordners werden nicht ausgeliefert
    for path in ("/..%2f..%2f..%2fetc/passwd", "/%2e%2e/%2e%2e/etc/passwd", "//etc/passwd", "/assets/..%2f..%2frun.py"):
        assert b"root:" not in c.get(path).content and b"uvicorn" not in c.get(path).content, path
    # SQL-Einschleusung: Eingaben werden nie als SQL ausgeführt
    assert c.post("/api/auth/login", json={"username": "chef' OR '1'='1' --", "password": "x' OR '1'='1"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).status_code == 200
    n_users = len(c.get("/api/users").json())
    assert c.get("/api/analysis?user=x' OR '1'='1").json()["kpis"]["count"] == 0
    assert c.get("/api/movements?article_id=1 OR 1=1").status_code == 422
    cat = c.get("/api/categories").json()[0]["id"]
    evil = "Robert'); DROP TABLE users;--"
    art = c.post("/api/articles", json={"name": evil, "category_id": cat, "unit": "=1+1"}).json()
    assert art["name"] == evil and len(c.get("/api/users").json()) == n_users
    c.post("/api/articles", json={"name": "=HYPERLINK(1)", "category_id": cat, "unit": "=1+1", "initial_stock": 1})
    assert ";'=HYPERLINK(1);" in c.get("/api/analysis/export.csv").text and ";'=1+1;" in c.get("/api/analysis/export.csv").text  # Excel führt nichts aus
    # Ungültige Zahlen (NaN, unendlich, riesig) werden abgewiesen statt Daten zu beschädigen
    for body in ('{"type":"in","article_id":%d,"quantity":NaN}', '{"type":"in","article_id":%d,"quantity":Infinity}', '{"type":"in","article_id":%d,"quantity":1e300}'):
        assert c.post("/api/movements", content=body % art["id"], headers=RAW).status_code == 422, body
    assert c.post("/api/articles", content='{"name":"Inf","category_id":%d,"unit":"m","price":Infinity}' % cat, headers=RAW).status_code == 422
    assert c.get("/api/articles").status_code == 200
    # Fremde Webseiten können nichts auslösen (auch nicht von einem anderen Port desselben Rechners)
    assert c.post("/api/projects", json={"name": "x"}, headers={"Origin": "http://boese-seite.example"}).status_code == 403
    assert c.post("/api/projects", json={"name": "x"}, headers={"Origin": "http://testserver:9999"}).status_code == 403
    assert c.post("/api/projects", json={"name": "Erlaubt"}, headers={"Origin": "http://testserver"}).status_code == 200
    try:
        with c.websocket_connect("/api/ws", headers={"Origin": "http://boese-seite.example"}) as ws:
            ws.receive_json()
        raise SystemExit("WebSocket von fremder Seite darf nicht funktionieren")
    except Exception as e:
        assert "4401" in repr(e) or getattr(e, "code", None) == 4401, repr(e)
    # Zu große Anfragen
    assert c.post("/api/projects", content=b"x" * 9_000_000, headers=RAW).status_code == 413
    assert c.post("/api/auth/login", json={"username": "chef", "password": "x" * 300}).status_code == 422
    assert c.post("/api/auth/password", json={"current_password": "geheim123", "new_password": "y" * 201}).status_code == 422
    # Keine Rechteausweitung über „Benutzer verwalten“ oder „Rollen verwalten“
    roles = c.get("/api/roles").json()
    admin_role = next(x for x in roles if x["is_system"]); lager = next(x for x in roles if x["name"] == "Lagerist")
    hr = c.post("/api/roles", json={"name": "Personal", "permissions": ["users.manage", "roles.manage", "articles.view"]}).json()
    klein = c.post("/api/roles", json={"name": "Nur lesen", "permissions": ["articles.view"]}).json()
    c.post("/api/users", json={"username": "hr", "role_id": hr["id"], "password": "geheim123"})
    chef_id = c.get("/api/auth/me").json()["id"]
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "hr", "password": "geheim123"})
    hr_id = c.get("/api/auth/me").json()["id"]
    assert c.put(f"/api/users/{hr_id}", json={"username": "hr", "role_id": admin_role["id"]}).status_code == 403          # sich selbst befördern
    assert c.post("/api/users", json={"username": "admin2", "role_id": admin_role["id"], "password": "geheim123"}).status_code == 403
    assert c.post("/api/users", json={"username": "lager2", "role_id": lager["id"], "password": "geheim123"}).status_code == 403  # Rolle mit mehr Rechten
    assert c.put(f"/api/users/{chef_id}", json={"username": "chef", "role_id": admin_role["id"], "password": "gekapert1"}).status_code == 403
    assert c.delete(f"/api/users/{chef_id}").status_code == 403
    assert c.put(f"/api/roles/{hr['id']}", json={"name": "Personal", "permissions": ["users.manage", "settings.manage"]}).status_code == 403
    assert c.put(f"/api/roles/{lager['id']}", json={"name": "Lagerist", "permissions": []}).status_code == 403            # fremde, stärkere Rolle
    assert c.delete(f"/api/roles/{lager['id']}").status_code == 403
    assert c.post("/api/users", json={"username": "leser", "role_id": klein["id"], "password": "geheim123"}).status_code == 200  # erlaubt
    assert c.put(f"/api/roles/{klein['id']}", json={"name": "Nur lesen", "permissions": ["articles.view"]}).status_code == 200
    # Anmeldung: Passwort-Raten wird gebremst, aber niemand kann einen Kollegen aussperren
    c.post("/api/auth/logout"); limiter.failures.clear()
    for _ in range(5):
        assert c.post("/api/auth/login", json={"username": "chef", "password": "falsch123"}).status_code == 401
    assert c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).status_code == 429
    limiter.failures = {("anderer-rechner", "chef"): limiter.failures.pop(("testclient", "chef")), ("anderer-rechner",): limiter.failures.pop(("testclient",))}
    assert c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).status_code == 200
    # Sitzung endet spätestens nach 30 Tagen, auch mit „Angemeldet bleiben“
    real = time.time
    security.time.time = lambda: real() + 31 * 86400
    assert c.get("/api/auth/me").status_code == 401
    security.time.time = real
    # Alte Passwort-Hashes bleiben gültig und werden bei der Anmeldung erneuert
    import hashlib, secrets
    salt = secrets.token_bytes(16)
    old = f"scrypt${salt.hex()}${hashlib.scrypt(b'geheim123', salt=salt, n=2**14, r=8, p=1).hex()}"
    assert verify_password("geheim123", old) and needs_rehash(old) and not needs_rehash(hash_password("x" * 8))
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET password_hash = :h WHERE username = 'chef'"), {"h": old})
    assert c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).status_code == 200
    with engine.begin() as conn:
        assert conn.execute(text("SELECT password_hash FROM users WHERE username = 'chef'")).scalar().startswith("scrypt$16$")
    # Sitzungs-Cookie: für Skripte unsichtbar, nur für diese Seite
    cookie = c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"}).headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
print("SICHERHEITSTESTS OK")

# --- Funktionswünsche ---------------------------------------------------------
with TestClient(app) as c:
    limiter.failures.clear()
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    assert {"wishes.create", "wishes.manage"} <= set(c.get("/api/auth/me").json()["permissions"])
    roles = c.get("/api/roles").json()
    schreiber = c.post("/api/roles", json={"name": "Wünscher", "permissions": ["wishes.create"]}).json()
    stumm = next(x for x in roles if x["name"] == "Nur lesen")
    c.post("/api/users", json={"username": "anna", "full_name": "Anna B.", "role_id": schreiber["id"], "password": "geheim123"})
    c.post("/api/users", json={"username": "bert", "role_id": schreiber["id"], "password": "geheim123"})
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "anna", "password": "geheim123"})
    assert c.post("/api/wishes", json={"text": "  "}).status_code in (400, 422)
    assert c.post("/api/wishes", json={"text": "x" * 2001}).status_code == 422
    w = c.post("/api/wishes", json={"text": "Bitte Etiketten drucken können"}).json()
    assert w["status"] == "neu" and w["user"] == "Anna B."
    assert len(c.get("/api/wishes/mine").json()) == 1
    assert c.get("/api/wishes").status_code == 403                                    # alle Wünsche: nur Verwaltung
    assert c.put(f"/api/wishes/{w['id']}", json={"status": "erledigt"}).status_code == 403
    assert c.delete(f"/api/wishes/{w['id']}").status_code == 403
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "bert", "password": "geheim123"})
    assert c.get("/api/wishes/mine").json() == []                                     # fremde Wünsche unsichtbar
    c.post("/api/wishes", json={"text": "Dunkles Design als Standard"})
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "leser", "password": "geheim123"})
    assert c.post("/api/wishes", json={"text": "Ich darf das nicht"}).status_code == 403   # ohne Recht
    assert c.get("/api/wishes/mine").status_code == 403
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    alle = c.get("/api/wishes").json()
    assert [x["user"] for x in alle] == ["bert", "Anna B."]
    assert c.put(f"/api/wishes/{w['id']}", json={"status": "quatsch"}).status_code == 400
    assert c.put(f"/api/wishes/{w['id']}", json={"status": "geplant"}).json()["status"] == "geplant"
    assert c.delete(f"/api/wishes/{alle[0]['id']}").status_code == 204 and len(c.get("/api/wishes").json()) == 1
    # Wunsch bleibt mit Namen erhalten, wenn der Benutzer gelöscht wird
    anna = next(u["id"] for u in c.get("/api/users").json() if u["username"] == "anna")
    assert c.delete(f"/api/users/{anna}").status_code == 204 and c.get("/api/wishes").json()[0]["user"] == "Anna B."
print("WUNSCH-TESTS OK")

# --- Lieferscheine -------------------------------------------------------------
PDF = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
b64 = lambda raw: base64.b64encode(raw).decode()
with TestClient(app) as c:
    limiter.failures.clear()
    c.post("/api/auth/login", json={"username": "chef", "password": "geheim123"})
    cat = c.get("/api/categories").json()[0]["id"]
    kabel = c.post("/api/articles", json={"name": "Kabel NYM 3x1,5", "category_id": cat, "unit": "m", "price": 0.8}).json()
    proj = c.post("/api/projects", json={"name": "Neubau Weber", "customer": "Fam. Weber", "address": "Hauptstr. 1, Bonn"}).json()
    year = time.localtime().tm_year
    # Eingang: Beleg des Lieferanten anlegen, PDF anhängen, Ware darauf buchen
    ein = c.post("/api/delivery-notes", json={"kind": "eingang", "partner": "Elektro Großhandel", "number": "L-77812"}).json()
    assert ein["number"] == "L-77812" and ein["file"] is None
    assert c.put(f"/api/delivery-notes/{ein['id']}/file", json={"data": b64(b"MZ\x90\x00 keine erlaubte Datei"), "name": "x.exe"}).status_code == 400
    f = c.put(f"/api/delivery-notes/{ein['id']}/file", json={"data": "data:application/pdf;base64," + b64(PDF), "name": "ls.pdf"}).json()["file"]
    got = c.get(f)
    assert got.content == PDF and got.headers["content-type"] == "application/pdf"
    mv = lambda **k: c.post("/api/movements", json=k)
    r = mv(type="in", article_id=kabel["id"], quantity=500, delivery_note_id=ein["id"])
    assert r.status_code == 200 and r.json()["delivery_note"] == "L-77812", r.text
    # Ausgang: eigener Lieferschein mit fortlaufender Nummer, Empfänger aus dem Projekt
    aus = c.post("/api/delivery-notes", json={"kind": "ausgang", "project_id": proj["id"]}).json()
    assert aus["number"] == f"LS-{year}-0001" and aus["partner"] == "Fam. Weber\nHauptstr. 1, Bonn"
    assert c.post("/api/delivery-notes", json={"kind": "ausgang"}).json()["number"] == f"LS-{year}-0002"
    assert mv(type="out", article_id=kabel["id"], quantity=120, delivery_note_id=aus["id"]).json()["project"] == "Neubau Weber"
    assert mv(type="out", article_id=kabel["id"], quantity=30, delivery_note_id=aus["id"], project_id=proj["id"]).status_code == 200
    # Falsche Zuordnungen werden abgewiesen
    assert mv(type="out", article_id=kabel["id"], quantity=1, delivery_note_id=ein["id"]).status_code == 400     # Eingangs-Beleg am Ausgang
    assert mv(type="return", article_id=kabel["id"], quantity=1, delivery_note_id=aus["id"]).status_code == 400  # Rückgabe hat keinen
    assert mv(type="out", article_id=kabel["id"], quantity=1, delivery_note_id=99999).status_code == 400
    andere = c.post("/api/projects", json={"name": "Anderes Projekt"}).json()
    assert mv(type="out", article_id=kabel["id"], quantity=1, delivery_note_id=aus["id"], project_id=andere["id"]).status_code == 400
    # Anzeige: Positionen bleiben, wie sie gebucht wurden – auch wenn der Artikel später umbenannt wird
    c.put(f"/api/articles/{kabel['id']}", json={"name": "Umbenannt", "category_id": cat, "unit": "Rolle", "price": 9})
    d = c.get(f"/api/delivery-notes/{aus['id']}").json()
    assert [(l["name"], l["quantity"], l["unit"], l["total"]) for l in d["lines"]] == [("Kabel NYM 3x1,5", 120, "m", 96.0), ("Kabel NYM 3x1,5", 30, "m", 24.0)]
    assert d["template"]["title"] == "Lieferschein" and d["template"]["logo"] is None
    liste = c.get("/api/delivery-notes").json()
    assert {n["number"]: n["item_count"] for n in liste} == {"L-77812": 1, f"LS-{year}-0001": 2, f"LS-{year}-0002": 0}
    assert [n["number"] for n in c.get("/api/delivery-notes?kind=eingang&recent=1").json()] == ["L-77812"]
    # Vorlage: Texte, Auswahl, Logo
    tpl = c.put("/api/delivery-template", json={"company_name": "Bau GmbH", "show_prices": True, "logo_position": "right", "number_prefix": "BAU-"}).json()
    assert tpl["company_name"] == "Bau GmbH" and tpl["show_prices"] is True and tpl["title"] == "Lieferschein"
    assert c.put("/api/delivery-template", json={"logo_position": "oben"}).status_code == 400
    assert c.put("/api/delivery-template/logo", json={"data": b64(PDF)}).status_code == 400          # Logo muss ein Bild sein
    logo = c.put("/api/delivery-template/logo", json={"data": b64(PNG), "name": "logo.png"}).json()["logo"]
    assert c.get(logo).content == PNG
    assert c.post("/api/delivery-notes", json={"kind": "ausgang"}).json()["number"] == f"BAU-{year}-0003"
    assert c.delete("/api/delivery-template/logo").json()["logo"] is None and c.get(logo).status_code == 404
    # Löschen entfernt nur den Lieferschein, die Buchungen bleiben
    n_mov = len(c.get(f"/api/movements?article_id={kabel['id']}").json())
    assert c.delete(f"/api/delivery-notes/{aus['id']}").status_code == 204
    rest = c.get(f"/api/movements?article_id={kabel['id']}").json()
    assert len(rest) == n_mov and all(m["delivery_note"] != f"LS-{year}-0001" for m in rest)
    assert c.get(f).status_code == 200 and c.delete(f"/api/delivery-notes/{ein['id']}/file").status_code == 204 and c.get(f).status_code == 404
    # Rechte: „leser“ (nur Artikel ansehen) sieht keine Lieferscheine; Mitarbeiter darf Ausgang anlegen, aber nichts verwalten
    ma = next(x for x in c.get("/api/roles").json() if x["name"] == "Mitarbeiter")
    c.post("/api/users", json={"username": "moni", "role_id": ma["id"], "password": "geheim123"})
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "leser", "password": "geheim123"})
    assert c.get("/api/delivery-notes").status_code == 403 and c.get("/api/delivery-template").status_code == 403
    assert c.get("/api/delivery-files/1").status_code == 403                                     # auch keine Anhänge
    assert c.post("/api/delivery-notes", json={"kind": "ausgang"}).status_code == 403
    c.post("/api/auth/logout"); c.post("/api/auth/login", json={"username": "moni", "password": "geheim123"})
    mine = c.post("/api/delivery-notes", json={"kind": "ausgang"})
    assert mine.status_code == 200 and c.get(f"/api/delivery-notes/{mine.json()['id']}").status_code == 200
    assert c.post("/api/delivery-notes", json={"kind": "eingang"}).status_code == 403               # darf keinen Eingang buchen
    assert c.put(f"/api/delivery-notes/{ein['id']}", json={"partner": "x"}).status_code == 403
    assert c.delete(f"/api/delivery-notes/{mine.json()['id']}").status_code == 403
    assert c.put("/api/delivery-template", json={"title": "Gekapert"}).status_code == 403
print("LIEFERSCHEIN-TESTS OK")
