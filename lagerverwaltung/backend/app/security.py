"""Passwörter, Sitzungen und Rechteprüfung."""
import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as Db

from urllib.parse import urlsplit

from .config import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, SESSION_COOKIE, SESSION_MAX_DAYS
from .database import get_db
from .models import Session, Setting, User
from .registry import SETTINGS


# --- Passwörter --------------------------------------------------------------
# scrypt mit eigenem Salt je Passwort. SCRYPT_LOG_N erhöhen macht das Erraten
# teurer; ältere Hashes bleiben gültig und werden bei der nächsten Anmeldung erneuert.
SCRYPT_LOG_N = 16
_LEGACY_LOG_N = 14  # Format der ersten Programmversionen: scrypt$salt$hash


def _scrypt(password: str, salt: bytes, log_n: int) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2 ** log_n, r=8, p=1,
                          maxmem=2 ** (log_n + 11)).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return f"scrypt${SCRYPT_LOG_N}${salt.hex()}${_scrypt(password, salt, SCRYPT_LOG_N)}"


def _parse(stored: str) -> tuple[int, bytes, str]:
    parts = stored.split("$")
    if len(parts) == 3:
        return _LEGACY_LOG_N, bytes.fromhex(parts[1]), parts[2]
    _, log_n, salt, digest = parts
    return int(log_n), bytes.fromhex(salt), digest


def verify_password(password: str, stored: str) -> bool:
    if len(password) > MAX_PASSWORD_LENGTH:
        return False
    try:
        log_n, salt, digest = _parse(stored)
        return hmac.compare_digest(_scrypt(password, salt, log_n), digest)
    except ValueError:
        return False


def needs_rehash(stored: str) -> bool:
    try:
        return _parse(stored)[0] < SCRYPT_LOG_N
    except ValueError:
        return True


_DUMMY_HASH = hash_password(secrets.token_hex(16))


def fake_verify(password: str):
    """Gleicher Rechenaufwand wie eine echte Prüfung – verrät nicht, ob es den Benutzer gibt."""
    verify_password(password, _DUMMY_HASH)


def check_password_rules(password: str):
    if len(password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(400, f"Das Passwort muss mindestens {MIN_PASSWORD_LENGTH} Zeichen haben.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise HTTPException(400, f"Das Passwort darf höchstens {MAX_PASSWORD_LENGTH} Zeichen haben.")


# --- Einstellungen -----------------------------------------------------------
def get_setting(db: Db, key: str):
    spec = SETTINGS[key]
    row = db.get(Setting, key)
    if row is None:
        return spec["default"]
    if spec["type"] == "number":
        return int(row.value)
    if spec["type"] == "bool":
        return row.value == "1"
    return row.value


# --- Sitzungen ---------------------------------------------------------------
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(db: Db, user: User) -> str:
    now = time.time()
    # Aufräumen: abgelaufene Sitzungen aller Benutzer entfernen
    db.query(Session).filter(Session.last_seen < now - SESSION_MAX_DAYS * 86400).delete()
    token = secrets.token_urlsafe(32)  # 256 Bit Zufall; gespeichert wird nur der Hash
    db.add(Session(token_hash=_hash_token(token), user_id=user.id, last_seen=now, created_at=now))
    db.commit()
    return token


def delete_session(db: Db, token: str | None):
    if token:
        db.query(Session).filter_by(token_hash=_hash_token(token)).delete()
        db.commit()


def idle_timeout_seconds(db: Db, user: User) -> int | None:
    """None = Benutzer darf angemeldet bleiben."""
    if user.can("session.stay_logged_in"):
        return None
    return get_setting(db, "idle_timeout_minutes") * 60


def current_user(request: Request, db: Db = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    session = db.query(Session).filter_by(token_hash=_hash_token(token)).first() if token else None
    if session is None or not session.user.active:
        raise HTTPException(401, "Nicht angemeldet.")
    timeout = idle_timeout_seconds(db, session.user)
    now = time.time()
    too_old = now - (session.created_at or session.last_seen) > SESSION_MAX_DAYS * 86400
    if too_old or (timeout is not None and now - session.last_seen > timeout):
        db.delete(session)
        db.commit()
        raise HTTPException(401, "Sitzung abgelaufen.")
    # Automatische Live-Aktualisierungen zählen nicht als Benutzeraktivität
    if not request.headers.get("x-background"):
        session.last_seen = now
        db.commit()
    return session.user


def require(permission: str):
    """Abhängigkeit für Routen: `user = Depends(require("users.manage"))`."""
    def checker(user: User = Depends(current_user)) -> User:
        if not user.can(permission):
            raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")
        return user
    return checker


def require_any(*permissions: str):
    """Wie `require`, aber eines der genannten Rechte genügt."""
    def checker(user: User = Depends(current_user)) -> User:
        if not any(user.can(p) for p in permissions):
            raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")
        return user
    return checker


# --- Schutz vor fremden Webseiten (CSRF) -------------------------------------
def same_origin(headers) -> bool:
    """Browser nennen bei ändernden Anfragen ihre Herkunft. Sie muss dieser Server sein.

    Das Sitzungs-Cookie ist zusätzlich „SameSite=Strict“; diese Prüfung schützt auch
    vor anderen Programmen auf demselben Rechner (anderer Port).
    """
    origin = headers.get("origin")
    if origin is None:
        return True  # kein Browser (z. B. Skript) oder einfache Seitenabrufe
    return urlsplit(origin).netloc == headers.get("host")
