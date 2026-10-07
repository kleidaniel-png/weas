"""Bestandsbuchung – die einzige Stelle, an der sich ein Bestand ändert."""
import threading

from fastapi import HTTPException
from sqlalchemy.orm import Session as Db

from .models import Article, DeliveryNote, Movement, Project, User
from .registry import MOVEMENT_TYPES

_lock = threading.Lock()  # verhindert, dass zwei Rechner gleichzeitig denselben Bestand ändern


def book(db: Db, user: User, type: str, article_id: int, quantity: float,
         project_id: int | None = None, note: str = "", delivery_note_id: int | None = None) -> Movement:
    spec = MOVEMENT_TYPES.get(type)
    if spec is None:
        raise HTTPException(400, "Unbekannte Bewegungsart.")
    with _lock:
        article = db.get(Article, article_id)
        if article is None:
            raise HTTPException(404, "Artikel nicht gefunden.")
        db.refresh(article)
        if not article.active:
            raise HTTPException(400, "Dieser Artikel ist deaktiviert.")

        if type == "correction":  # Menge = gezählter neuer Bestand
            if quantity < 0:
                raise HTTPException(400, "Der Bestand kann nicht negativ sein.")
            delta = round(quantity - article.stock, 3)
            if delta == 0:
                raise HTTPException(400, "Der Bestand stimmt bereits.")
        else:
            if quantity <= 0:
                raise HTTPException(400, "Die Menge muss größer als 0 sein.")
            delta = round(spec["sign"] * quantity, 3)
        if article.stock + delta < 0:
            raise HTTPException(400, f"Nicht genug Bestand: verfügbar sind {article.stock:g} {article.unit}.")

        if delivery_note_id is not None:
            delivery_note = db.get(DeliveryNote, delivery_note_id)
            if delivery_note is None or delivery_note.kind != spec.get("delivery"):
                raise HTTPException(400, "Der Lieferschein passt nicht zu dieser Buchung.")
            if spec["project"] and delivery_note.project_id is not None:
                if project_id is not None and project_id != delivery_note.project_id:
                    raise HTTPException(400, "Der Lieferschein gehört zu einem anderen Projekt.")
                project_id = delivery_note.project_id

        if not spec["project"]:
            project_id = None
        elif project_id is not None:
            project = db.get(Project, project_id)
            if project is None:
                raise HTTPException(400, "Das gewählte Projekt existiert nicht.")
            if project.status != "aktiv":
                raise HTTPException(400, "Auf abgeschlossene Projekte kann nicht gebucht werden.")

        article.stock = round(article.stock + delta, 3)
        movement = Movement(type=type, article_id=article.id, quantity=delta, unit_price=article.price,
                            project_id=project_id, user_id=user.id,
                            user_name=user.full_name or user.username, note=note.strip(),
                            delivery_note_id=delivery_note_id, article_name=article.name, article_unit=article.unit)
        db.add(movement)
        db.commit()
        return movement
