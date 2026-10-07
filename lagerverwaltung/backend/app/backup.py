"""Tägliche Datensicherung der Datenbank."""
import asyncio
import logging
import os
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from .config import BACKUP_DIR, DATA_DIR
from .database import SessionLocal
from .security import get_setting

log = logging.getLogger("lager.backup")
PREFIX, SUFFIX = "lager-", ".db"
CHECK_EVERY_SECONDS = 3600


def _file_for(day: date) -> Path:
    return BACKUP_DIR / f"{PREFIX}{day.isoformat()}{SUFFIX}"


def _private(path: Path):
    """Nur der Dienst-Benutzer darf die Datei lesen (enthält Passwort-Hashes). Unter Windows ohne Wirkung."""
    try:
        os.chmod(path, 0o700 if path.is_dir() else 0o600)
    except OSError:
        pass


def list_backups() -> list[dict]:
    files = sorted(BACKUP_DIR.glob(f"{PREFIX}*{SUFFIX}"), reverse=True) if BACKUP_DIR.exists() else []
    return [{"name": f.name, "size": f.stat().st_size, "created": f.stat().st_mtime} for f in files]


def run_backup() -> Path:
    """Sichert die laufende Datenbank in eine Tagesdatei und löscht zu alte Sicherungen."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    _private(BACKUP_DIR)
    target = _file_for(date.today())
    temp = target.with_suffix(".tmp")
    source = sqlite3.connect(DATA_DIR / "lager.db")
    copy = sqlite3.connect(temp)
    try:
        source.backup(copy)  # sicher auch während das Programm benutzt wird
    finally:
        copy.close()
        source.close()
    os.replace(temp, target)
    _private(target)

    with SessionLocal() as db:
        keep_days = get_setting(db, "backup_keep_days")
    oldest = date.today() - timedelta(days=keep_days)
    for file in BACKUP_DIR.glob(f"{PREFIX}*{SUFFIX}"):
        try:
            day = datetime.strptime(file.name[len(PREFIX):-len(SUFFIX)], "%Y-%m-%d").date()
        except ValueError:
            continue  # fremde Datei: nicht anfassen
        if day < oldest:
            file.unlink()
    return target


async def backup_loop():
    """Läuft im Hintergrund: einmal täglich sichern (auch direkt nach dem Start, falls heute noch nicht)."""
    while True:
        try:
            if not _file_for(date.today()).exists():
                await asyncio.to_thread(run_backup)
                log.info("Datensicherung erstellt.")
        except Exception:
            log.exception("Datensicherung fehlgeschlagen.")
        await asyncio.sleep(CHECK_EVERY_SECONDS)
