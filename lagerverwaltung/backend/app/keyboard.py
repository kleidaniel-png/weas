"""Tastaturlayout am Server-Terminal passend zur Sprache des Benutzers umschalten.

Greift nur, wenn die Anfrage vom Server selbst kommt (Terminal = Browser auf dem
Server) und der Benutzer als Terminal-Benutzer markiert ist. Die Rechner der
Mitarbeiter bleiben unberührt – deren Tastatur kann ein Webprogramm nicht umstellen.
"""
import logging
import shlex
import subprocess

from fastapi import Request
from sqlalchemy.orm import Session as Db

from .config import KEYBOARD_COMMAND
from .models import User
from .registry import LANGUAGES
from .security import get_setting

log = logging.getLogger("lager.keyboard")
_current: str | None = None  # zuletzt gesetztes Layout (vermeidet unnötige Aufrufe)


def is_terminal(request: Request) -> bool:
    return request.client is not None and request.client.host in ("127.0.0.1", "::1")


def _apply(layout: str):
    global _current
    if not KEYBOARD_COMMAND or layout == _current:
        return
    _current = layout
    try:
        subprocess.run(shlex.split(KEYBOARD_COMMAND.format(layout=layout)), timeout=3, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError) as error:  # z. B. kein Bildschirm vorhanden
        log.warning("Tastatur konnte nicht auf '%s' umgestellt werden: %s", layout, error)


def for_user(request: Request, user: User):
    if is_terminal(request) and user.is_terminal:
        _apply(LANGUAGES[user.language]["keyboard"])


def reset(request: Request, db: Db):
    """Niemand angemeldet: Layout der Anmeldeseite (Einstellung „terminal_language“)."""
    if is_terminal(request):
        _apply(LANGUAGES[get_setting(db, "terminal_language")]["keyboard"])
