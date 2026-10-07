"""Lieferscheine: Belege der Lieferanten anhängen, eigene Lieferscheine erzeugen, Vorlage pflegen."""
import base64
import binascii
import threading
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session as Db

from ..config import MAX_FILE_BYTES, MAX_LOGO_BYTES
from ..database import get_db
from ..models import DeliveryNote, JsonStore, Movement, Project, StoredFile, User
from ..registry import DELIVERY_KINDS, DELIVERY_TEMPLATE, DELIVERY_TEMPLATE_CHOICES, MOVEMENT_TYPES
from ..security import current_user, require, require_any

router = APIRouter(prefix="/api", tags=["Lieferscheine"])

# Ansehen darf, wer das Recht hat – und wer buchen darf (er legt Lieferscheine ja an).
BOOKING_PERMISSIONS = {spec["delivery"]: spec["permission"] for spec in MOVEMENT_TYPES.values() if spec.get("delivery")}
view = require_any("delivery.view", "delivery.manage", *BOOKING_PERMISSIONS.values())
manage = require("delivery.manage")

TEMPLATE_KEY = "delivery_template"
RECENT_DAYS = 3  # so lange wird ein Lieferschein beim Buchen zur Auswahl angeboten
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_number_lock = threading.Lock()


# --- Dateien -----------------------------------------------------------------
class FileIn(BaseModel):
    data: str = Field(max_length=MAX_FILE_BYTES * 2)  # Data-URL oder reines Base64
    name: str = Field(default="", max_length=200)


def _file_type(data: bytes) -> str | None:
    """Erkennt den Typ am Inhalt – Dateiname und Angabe des Browsers werden nicht geglaubt."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"%PDF-":
        return "application/pdf"
    return None


def _store(db: Db, body: FileIn, max_bytes: int, images_only: bool = False) -> StoredFile:
    try:
        data = base64.b64decode(body.data.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "Die Datei konnte nicht gelesen werden.")
    if len(data) > max_bytes:
        raise HTTPException(400, "Die Datei ist zu groß.")
    mime = _file_type(data)
    if mime is None or (images_only and mime not in IMAGE_TYPES):
        raise HTTPException(400, "Nur Bilder (JPEG, PNG, WebP) sind erlaubt." if images_only
                            else "Erlaubt sind Bilder (JPEG, PNG, WebP) und PDF-Dateien.")
    stored = StoredFile(name=body.name.strip(), mime=mime, data=data, created_at=time.time())
    db.add(stored)
    db.flush()
    return stored


def _file_url(file_id: int | None) -> str | None:
    return f"/api/delivery-files/{file_id}" if file_id else None


@router.get("/delivery-files/{file_id}")
def get_file(file_id: int, db: Db = Depends(get_db), _: User = Depends(view)):
    """Liefert einen Anhang oder das Logo. Die Nummer ändert sich bei jedem Hochladen, daher zwischenspeicherbar."""
    stored = db.get(StoredFile, file_id)
    if stored is None:
        raise HTTPException(404, "Datei nicht gefunden.")
    return Response(stored.data, media_type=stored.mime,
                    headers={"Cache-Control": "private, max-age=31536000, immutable",
                             "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"})


# --- Vorlage -----------------------------------------------------------------
def load_template(db: Db) -> dict:
    row = db.get(JsonStore, TEMPLATE_KEY)
    saved = row.data if row else {}
    template = {key: saved.get(key, default) for key, default in DELIVERY_TEMPLATE.items()}
    template["logo"] = _file_url(saved.get("logo_file_id"))
    return template


def _save_template(db: Db, changes: dict):
    row = db.get(JsonStore, TEMPLATE_KEY)
    if row is None:
        row = JsonStore(key=TEMPLATE_KEY, data={})
        db.add(row)
    row.data = {**(row.data or {}), **changes}  # neues Objekt, damit die Änderung gespeichert wird
    db.commit()


@router.get("/delivery-template")
def get_template(db: Db = Depends(get_db), _: User = Depends(view)):
    return load_template(db)


@router.put("/delivery-template")
def update_template(values: dict, db: Db = Depends(get_db), _: User = Depends(manage)):
    changes = {}
    for key, value in values.items():
        if key not in DELIVERY_TEMPLATE:
            continue  # z. B. "logo": wird getrennt hochgeladen
        default = DELIVERY_TEMPLATE[key]
        if isinstance(default, bool):
            value = bool(value)
        else:
            value = str(value).strip()
            if len(value) > 1000:
                raise HTTPException(400, "Ein Text der Vorlage ist zu lang (höchstens 1000 Zeichen).")
            if key in DELIVERY_TEMPLATE_CHOICES and value not in DELIVERY_TEMPLATE_CHOICES[key]:
                raise HTTPException(400, "Ungültige Auswahl in der Vorlage.")
        changes[key] = value
    _save_template(db, changes)
    return load_template(db)


def _remove_logo(db: Db):
    row = db.get(JsonStore, TEMPLATE_KEY)
    old = (row.data or {}).get("logo_file_id") if row else None
    if old:
        db.query(StoredFile).filter_by(id=old).delete()


@router.put("/delivery-template/logo")
def set_logo(body: FileIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    stored = _store(db, body, MAX_LOGO_BYTES, images_only=True)
    _remove_logo(db)
    _save_template(db, {"logo_file_id": stored.id})
    return load_template(db)


@router.delete("/delivery-template/logo")
def delete_logo(db: Db = Depends(get_db), _: User = Depends(manage)):
    _remove_logo(db)
    _save_template(db, {"logo_file_id": None})
    return load_template(db)


# --- Lieferscheine -----------------------------------------------------------
class NoteIn(BaseModel):
    kind: str
    number: str = Field(default="", max_length=50)    # nur Eingang: Nummer des Lieferanten
    partner: str = Field(default="", max_length=300)  # Lieferant bzw. Empfänger
    note: str = Field(default="", max_length=500)
    project_id: int | None = None


class NoteUpdate(BaseModel):
    number: str = Field(default="", max_length=50)
    partner: str = Field(default="", max_length=300)
    note: str = Field(default="", max_length=500)


def note_out(n: DeliveryNote, item_count: int = 0) -> dict:
    return {"id": n.id, "kind": n.kind, "kind_label": DELIVERY_KINDS[n.kind], "number": n.number,
            "partner": n.partner, "note": n.note, "project_id": n.project_id,
            "project": n.project.name if n.project else "", "user": n.user_name, "created_at": n.created_at,
            "file": _file_url(n.file_id), "item_count": item_count}


def _get(db: Db, note_id: int) -> DeliveryNote:
    note = db.get(DeliveryNote, note_id)
    if note is None:
        raise HTTPException(404, "Lieferschein nicht gefunden.")
    return note


def _may_edit(user: User, note: DeliveryNote):
    """Bearbeiten darf, wer diese Art buchen darf, oder wer Lieferscheine verwaltet."""
    if not (user.can("delivery.manage") or user.can(BOOKING_PERMISSIONS[note.kind])):
        raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")


@router.get("/delivery-notes")
def list_notes(kind: str | None = None, recent: bool = False,
               db: Db = Depends(get_db), _: User = Depends(view)):
    query = db.query(DeliveryNote)
    if kind:
        query = query.filter_by(kind=kind)
    if recent:
        query = query.filter(DeliveryNote.created_at >= time.time() - RECENT_DAYS * 86400)
    counts = dict(db.query(Movement.delivery_note_id, func.count()).filter(Movement.delivery_note_id.isnot(None))
                  .group_by(Movement.delivery_note_id))
    rows = query.order_by(DeliveryNote.created_at.desc(), DeliveryNote.id.desc()).limit(1000)
    return [note_out(n, counts.get(n.id, 0)) for n in rows]


@router.post("/delivery-notes")
def create_note(data: NoteIn, db: Db = Depends(get_db), user: User = Depends(current_user)):
    if data.kind not in DELIVERY_KINDS:
        raise HTTPException(400, "Unbekannte Art.")
    if not user.can(BOOKING_PERMISSIONS[data.kind]):
        raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")
    project = None
    if data.project_id is not None:
        project = db.get(Project, data.project_id)
        if project is None:
            raise HTTPException(400, "Das gewählte Projekt existiert nicht.")
    note = DeliveryNote(kind=data.kind, partner=data.partner.strip(), note=data.note.strip(),
                        project_id=data.project_id, user_id=user.id,
                        user_name=user.full_name or user.username, created_at=time.time())
    if data.kind == "ausgang":
        # Eigener Lieferschein: fortlaufende Nummer je Jahr, Empfänger aus dem Projekt vorbelegen
        if not note.partner and project is not None:
            note.partner = "\n".join(part for part in (project.customer, project.address) if part)
        with _number_lock:
            year = datetime.now().year
            last = db.query(func.max(DeliveryNote.seq)).filter_by(kind="ausgang", year=year).scalar() or 0
            note.year, note.seq = year, last + 1
            note.number = f"{load_template(db)['number_prefix']}{year}-{note.seq:04d}"
            db.add(note)
            db.commit()
    else:
        note.number = data.number.strip()
        db.add(note)
        db.commit()
    return note_out(note)


@router.get("/delivery-notes/{note_id}")
def get_note(note_id: int, db: Db = Depends(get_db), _: User = Depends(view)):
    """Alles, was zum Anzeigen und Drucken nötig ist: Kopf, Positionen, Vorlage."""
    note = _get(db, note_id)
    lines = [{"article_number": m.article.number, "name": m.article_name or m.article.name,
              "unit": m.article_unit or m.article.unit, "quantity": abs(m.quantity), "unit_price": m.unit_price,
              "total": round(abs(m.quantity) * m.unit_price, 2)}
             for m in db.query(Movement).filter_by(delivery_note_id=note.id).order_by(Movement.id)]
    file_type = db.query(StoredFile.mime).filter_by(id=note.file_id).scalar() if note.file_id else None
    return {"note": {**note_out(note, len(lines)), "file_type": file_type},
            "lines": lines, "template": load_template(db)}


@router.put("/delivery-notes/{note_id}")
def update_note(note_id: int, data: NoteUpdate, db: Db = Depends(get_db), user: User = Depends(current_user)):
    note = _get(db, note_id)
    _may_edit(user, note)
    note.partner, note.note = data.partner.strip(), data.note.strip()
    if note.kind == "eingang":  # die eigene Nummer bleibt unveränderlich
        note.number = data.number.strip()
    db.commit()
    return note_out(note)


@router.put("/delivery-notes/{note_id}/file")
def attach_file(note_id: int, body: FileIn, db: Db = Depends(get_db), user: User = Depends(current_user)):
    """Hängt ein Foto oder PDF an: den Beleg des Lieferanten oder den unterschriebenen eigenen Lieferschein."""
    note = _get(db, note_id)
    _may_edit(user, note)
    stored = _store(db, body, MAX_FILE_BYTES)
    if note.file_id:
        db.query(StoredFile).filter_by(id=note.file_id).delete()
    note.file_id = stored.id
    db.commit()
    return note_out(note)


@router.delete("/delivery-notes/{note_id}/file", status_code=204)
def remove_file(note_id: int, db: Db = Depends(get_db), user: User = Depends(current_user)):
    note = _get(db, note_id)
    _may_edit(user, note)
    if note.file_id:
        db.query(StoredFile).filter_by(id=note.file_id).delete()
        note.file_id = None
        db.commit()


@router.delete("/delivery-notes/{note_id}", status_code=204)
def delete_note(note_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    """Löscht nur den Lieferschein. Die Buchungen bleiben bestehen."""
    note = _get(db, note_id)
    db.query(Movement).filter_by(delivery_note_id=note.id).update({"delivery_note_id": None})
    if note.file_id:
        db.query(StoredFile).filter_by(id=note.file_id).delete()
    db.delete(note)
    db.commit()
