import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from .config import DATA_DIR, MAX_BODY_BYTES, STATIC_DIR
from .backup import _private, backup_loop
from .database import Base, SessionLocal, engine, migrate
from .live import hub, router as live_router
from .models import Category, Role
from .registry import PRODUCT_NAME, ADMIN_ROLE, DEFAULT_CATEGORIES, DEFAULT_ROLES
from .routers.auth import ensure_setup_code
from .security import same_origin
from .routers import analysis, articles, auth, backups, movements, projects, roles, settings, users, wishes, delivery

# Neue Module: Router-Datei anlegen und hier eintragen.
ROUTERS = [auth.router, users.router, roles.router, settings.router,
           articles.router, projects.router, movements.router, analysis.router, backups.router, wishes.router, delivery.router, live_router]


def seed():
    with SessionLocal() as db:
        if db.query(Role).count() == 0:
            db.add(Role(name=ADMIN_ROLE, is_system=True, permissions=[]))
            for name, perms in DEFAULT_ROLES.items():
                db.add(Role(name=name, permissions=perms))
            db.commit()
        if db.query(Category).count() == 0:
            db.add_all(Category(name=n, kind=k) for n, k in DEFAULT_CATEGORIES)
            db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)  # neue Tabellen
    migrate()                         # neue Spalten
    seed()
    for path in (DATA_DIR, DATA_DIR / "lager.db"):  # Datenbank nur für den Dienst lesbar
        _private(path)
    ensure_setup_code()
    task = asyncio.create_task(backup_loop())  # tägliche Datensicherung
    yield
    task.cancel()


# Die automatische API-Dokumentation bleibt aus: Sie wäre ohne Anmeldung für jeden im Netz lesbar.
app = FastAPI(title=PRODUCT_NAME, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
for router in ROUTERS:
    app.include_router(router)


@app.exception_handler(RequestValidationError)
async def invalid_input(_: Request, __: RequestValidationError):
    """Ungültige Eingaben: knappe Meldung, ohne die Eingabe zurückzugeben."""
    return _refuse(422, "Bitte die Eingaben prüfen.")


def _refuse(status: int, message: str) -> JSONResponse:
    return JSONResponse({"detail": message}, status_code=status)


@app.middleware("http")
async def guard(request: Request, call_next):
    """Läuft bei jeder Anfrage: Schutzprüfungen, Live-Abgleich, Sicherheits-Header."""
    path = request.url.path
    is_api = path.startswith("/api/")
    changing = request.method not in ("GET", "HEAD", "OPTIONS")

    if is_api and changing:
        if not same_origin(request.headers):
            return _refuse(403, "Anfrage von fremder Seite abgelehnt.")
        length = request.headers.get("content-length", "0")
        if "transfer-encoding" in request.headers or not length.isdigit():
            return _refuse(411, "Die Anfrage ist ungültig.")
        if int(length) > MAX_BODY_BYTES:
            return _refuse(413, "Die Anfrage ist zu groß.")

    response = await call_next(request)

    # Nach jeder erfolgreichen Änderung alle offenen Fenster benachrichtigen (Live-Abgleich)
    parts = path.split("/")
    if is_api and changing and response.status_code < 400 and len(parts) > 2 and parts[2] != "auth":
        await hub.broadcast(parts[2])

    host = request.headers.get("host", "")
    headers = response.headers
    headers.setdefault("X-Content-Type-Options", "nosniff")          # Dateityp nicht erraten
    headers.setdefault("X-Frame-Options", "DENY")                    # nicht in fremde Seiten einbettbar
    headers.setdefault("Referrer-Policy", "no-referrer")
    headers.setdefault("Permissions-Policy", "geolocation=(), microphone=()")
    headers.setdefault("Content-Security-Policy",                    # nur eigene Skripte und Daten
                       "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
                       f"connect-src 'self' ws://{host} wss://{host}; object-src 'none'; base-uri 'self'; "
                       "frame-ancestors 'none'; form-action 'self'")
    # Antworten mit Daten nicht im Browser aufbewahren (wichtig am gemeinsam genutzten Terminal)
    headers.setdefault("Cache-Control", "no-store" if is_api else
                       "public, max-age=31536000, immutable" if path.startswith("/assets/") else "no-cache")
    return response


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    """Liefert die gebaute Oberfläche aus (alle Nicht-API-Pfade)."""
    if path.startswith("api/"):
        raise HTTPException(404, "Nicht gefunden.")
    file = (STATIC_DIR / path).resolve()
    if path and file.is_file() and file.is_relative_to(STATIC_DIR.resolve()):
        return FileResponse(file)
    index = STATIC_DIR / "index.html"
    if not index.is_file():
        raise HTTPException(503, "Oberfläche nicht gebaut. Bitte im Ordner frontend 'npm run build' ausführen.")
    return FileResponse(index)
