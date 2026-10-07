import hmac
import secrets
import threading
import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as Db

from .. import keyboard
from ..config import (LOGIN_LOCK_SECONDS, LOGIN_MAX_ATTEMPTS, LOGIN_MAX_ATTEMPTS_PER_ADDRESS,
                      MAX_PASSWORD_LENGTH, SESSION_COOKIE, SETUP_CODE_FILE)
from ..database import get_db
from ..models import Role, Session, User
from ..registry import DEFAULT_LANGUAGE, LANGUAGES, PRODUCT_LONG_NAME, PRODUCT_NAME
from ..security import (_hash_token, check_password_rules, create_session, current_user, delete_session,
                        fake_verify, get_setting, hash_password, idle_timeout_seconds, needs_rehash,
                        verify_password)

router = APIRouter(prefix="/api/auth", tags=["Anmeldung"])

_setup_lock = threading.Lock()


class LoginLimiter:
    """Bremst das Durchprobieren von Passwörtern.

    Gezählt wird je (Rechner, Benutzername) und zusätzlich je Rechner. So kann
    niemand einen Kollegen aussperren, indem er dessen Namen falsch eingibt.
    """

    def __init__(self):
        self.failures: dict[tuple, list[float]] = {}

    def _recent(self, key: tuple, window: float, now: float) -> list[float]:
        return [t for t in self.failures.get(key, []) if now - t < window]

    def blocked(self, address: str, username: str) -> bool:
        now = time.time()
        return (len(self._recent((address, username), LOGIN_LOCK_SECONDS, now)) >= LOGIN_MAX_ATTEMPTS
                or len(self._recent((address,), 600, now)) >= LOGIN_MAX_ATTEMPTS_PER_ADDRESS)

    def failed(self, address: str, username: str):
        now = time.time()
        if len(self.failures) > 5000:  # Speicher begrenzen: Abgelaufenes verwerfen
            self.failures = {k: v for k, v in self.failures.items() if now - v[-1] < 600}
        for key, window in (((address, username), LOGIN_LOCK_SECONDS), ((address,), 600)):
            self.failures[key] = self._recent(key, window, now) + [now]

    def succeeded(self, address: str, username: str):
        self.failures.pop((address, username), None)


limiter = LoginLimiter()


class Credentials(BaseModel):
    username: str = Field(max_length=50)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class SetupIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    full_name: str = Field(default="", max_length=100)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    language: str = DEFAULT_LANGUAGE
    code: str = Field(default="", max_length=20)  # Einrichtungscode (nur von anderen Rechnern nötig)


class LanguageChange(BaseModel):
    language: str


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=MAX_PASSWORD_LENGTH)
    new_password: str = Field(max_length=MAX_PASSWORD_LENGTH)


def me_out(db: Db, user: User) -> dict:
    return {
        "id": user.id, "username": user.username, "full_name": user.full_name,
        "role": user.role.name, "permissions": sorted(user.role.permission_set),
        "idle_timeout_seconds": idle_timeout_seconds(db, user),
        "language": user.language, "is_terminal": user.is_terminal,
        "features": {"scanner": get_setting(db, "scanner_enabled")},  # ein-/ausschaltbare Programmteile
    }


def _has_session(request: Request, db: Db) -> bool:
    token = request.cookies.get(SESSION_COOKIE)
    return bool(token) and db.query(Session).filter_by(token_hash=_hash_token(token)).first() is not None


def _set_cookie(request: Request, response: Response, token: str):
    # HttpOnly: für Skripte unsichtbar. SameSite=Strict: fremde Seiten können es nicht mitschicken.
    # Secure: bei HTTPS nur verschlüsselt übertragen.
    response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https")


def ensure_setup_code():
    """Solange kein Benutzer existiert, liegt ein Einrichtungscode im Datenordner.

    Ohne ihn könnte der Erste im Netzwerk, der die Seite öffnet, sich zum
    Administrator machen. Direkt am Server (localhost) ist kein Code nötig.
    """
    from ..database import SessionLocal
    with SessionLocal() as db:
        if db.query(User).count() > 0:
            SETUP_CODE_FILE.unlink(missing_ok=True)
            return
    if not SETUP_CODE_FILE.exists():
        raw = secrets.token_hex(4).upper()
        SETUP_CODE_FILE.write_text(f"{raw[:4]}-{raw[4:]}\n", encoding="utf-8")
    print(f"\n  Ersteinrichtung: Einrichtungscode {SETUP_CODE_FILE.read_text(encoding='utf-8').strip()}"
          f"  (nur nötig, wenn die Einrichtung nicht am Server selbst erfolgt)\n", flush=True)


def _setup_code_ok(request: Request, code: str) -> bool:
    if keyboard.is_terminal(request):  # Anfrage vom Server selbst
        return True
    try:
        expected = SETUP_CODE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    return hmac.compare_digest(code.strip().upper().encode(), expected.encode())


@router.get("/status")
def status(request: Request, db: Db = Depends(get_db)):
    if not _has_session(request, db):  # Anmeldeseite am Terminal: Tastatur zurückstellen
        keyboard.reset(request, db)
    needs_setup = db.query(User).count() == 0
    return {"needs_setup": needs_setup,
            "setup_code_required": needs_setup and not keyboard.is_terminal(request),
            "product": {"name": PRODUCT_NAME, "long_name": PRODUCT_LONG_NAME},
            "company_name": get_setting(db, "company_name"),
            "languages": {code: lang["label"] for code, lang in LANGUAGES.items()}}


@router.post("/setup")
def setup(data: SetupIn, request: Request, response: Response, db: Db = Depends(get_db)):
    """Erster Start: legt das Administrator-Konto an. Danach gesperrt."""
    address = request.client.host if request.client else ""
    if limiter.blocked(address, "#setup"):
        raise HTTPException(429, "Zu viele Fehlversuche. Bitte eine Minute warten.")
    check_password_rules(data.password)
    with _setup_lock:  # zwei gleichzeitige Einrichtungen ausschließen
        if db.query(User).count() > 0:
            raise HTTPException(403, "Die Einrichtung ist bereits abgeschlossen.")
        if not _setup_code_ok(request, data.code):
            limiter.failed(address, "#setup")
            raise HTTPException(403, "Der Einrichtungscode ist falsch.")
        admin_role = db.query(Role).filter_by(is_system=True).one()
        user = User(username=data.username.strip().lower(), full_name=data.full_name.strip(),
                    password_hash=hash_password(data.password), role_id=admin_role.id,
                    language=data.language if data.language in LANGUAGES else DEFAULT_LANGUAGE)
        db.add(user)
        db.commit()
    SETUP_CODE_FILE.unlink(missing_ok=True)
    _set_cookie(request, response, create_session(db, user))
    return me_out(db, user)


@router.post("/login")
def login(data: Credentials, request: Request, response: Response, db: Db = Depends(get_db)):
    name = data.username.strip().lower()
    address = request.client.host if request.client else ""
    if limiter.blocked(address, name):
        raise HTTPException(429, "Zu viele Fehlversuche. Bitte eine Minute warten.")
    user = db.query(User).filter_by(username=name).first()
    if user is None or not user.active:
        fake_verify(data.password)
        valid = False
    else:
        valid = verify_password(data.password, user.password_hash)
    if not valid:  # bewusst dieselbe Meldung für „unbekannt“, „gesperrt“ und „falsches Passwort“
        limiter.failed(address, name)
        raise HTTPException(401, "Benutzername oder Passwort ist falsch.")
    limiter.succeeded(address, name)
    if needs_rehash(user.password_hash):  # ältere Hashes auf den aktuellen Stand bringen
        user.password_hash = hash_password(data.password)
        db.commit()
    keyboard.for_user(request, user)
    _set_cookie(request, response, create_session(db, user))
    return me_out(db, user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Db = Depends(get_db)):
    delete_session(db, request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE)
    keyboard.reset(request, db)


@router.get("/me")
def me(user: User = Depends(current_user), db: Db = Depends(get_db)):
    return me_out(db, user)


@router.put("/language")
def change_language(data: LanguageChange, request: Request,
                    user: User = Depends(current_user), db: Db = Depends(get_db)):
    """Jeder Benutzer darf seine eigene Sprache wählen."""
    if data.language not in LANGUAGES:
        raise HTTPException(400, "Unbekannte Sprache.")
    user.language = data.language
    db.commit()
    keyboard.for_user(request, user)
    return me_out(db, user)


@router.post("/password", status_code=204)
def change_password(data: PasswordChange, request: Request,
                    user: User = Depends(current_user), db: Db = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Das aktuelle Passwort ist falsch.")
    check_password_rules(data.new_password)
    user.password_hash = hash_password(data.new_password)
    db.commit()
    # andere Sitzungen dieses Benutzers beenden
    keep = request.cookies.get(SESSION_COOKIE)
    db.query(Session).filter(Session.user_id == user.id,
                             Session.token_hash != _hash_token(keep)).delete()
    db.commit()
