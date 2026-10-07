from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Movement, User
from ..registry import MOVEMENT_TYPES
from ..security import current_user, require_any
from ..stock import book

router = APIRouter(prefix="/api/movements", tags=["Warenbewegungen"])


class MovementIn(BaseModel):
    type: str
    article_id: int
    quantity: float = Field(ge=-1_000_000_000, le=1_000_000_000, allow_inf_nan=False)  # bei Korrektur: der gezählte neue Bestand
    project_id: int | None = None
    note: str = Field(default="", max_length=300)
    delivery_note_id: int | None = None


def movement_out(m: Movement) -> dict:
    return {"id": m.id, "type": m.type, "type_label": MOVEMENT_TYPES[m.type]["label"],
            "article_id": m.article_id, "article_number": m.article.number, "article_name": m.article.name,
            "unit": m.article.unit, "quantity": m.quantity, "unit_price": m.unit_price,
            "project_id": m.project_id, "project": m.project.name if m.project else "",
            "user": m.user_name, "created_at": m.created_at, "note": m.note,
            "delivery_note_id": m.delivery_note_id,
            "delivery_note": (m.delivery_note.number or f"#{m.delivery_note.id}") if m.delivery_note else ""}


@router.get("")
def list_movements(article_id: int | None = None, project_id: int | None = None, limit: int = 200,
                   db: Db = Depends(get_db), _: User = Depends(require_any("articles.view", "projects.view"))):
    query = db.query(Movement)
    if article_id is not None:
        query = query.filter_by(article_id=article_id)
    if project_id is not None:
        query = query.filter_by(project_id=project_id)
    rows = query.order_by(Movement.created_at.desc(), Movement.id.desc()).limit(max(1, min(limit, 1000)))
    return [movement_out(m) for m in rows]


@router.post("")
def create_movement(data: MovementIn, db: Db = Depends(get_db), user: User = Depends(current_user)):
    spec = MOVEMENT_TYPES.get(data.type)
    if spec is None:
        raise HTTPException(400, "Unbekannte Bewegungsart.")
    if not user.can(spec["permission"]):
        raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")
    return movement_out(book(db, user, data.type, data.article_id, data.quantity, data.project_id,
                             data.note, data.delivery_note_id))
