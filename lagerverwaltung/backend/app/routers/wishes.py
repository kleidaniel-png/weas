"""Funktionswünsche: Benutzer reichen ein, die Verwaltung sieht und bearbeitet alle."""
import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import User, Wish
from ..registry import WISH_STATUSES
from ..security import require

router = APIRouter(prefix="/api/wishes", tags=["Wünsche"])
create = require("wishes.create")
manage = require("wishes.manage")

MAX_OPEN_PER_USER = 50  # verhindert, dass jemand die Liste zumüllt


class WishIn(BaseModel):
    text: str = Field(min_length=3, max_length=2000)


class StatusIn(BaseModel):
    status: str


def wish_out(w: Wish) -> dict:
    return {"id": w.id, "text": w.text, "status": w.status, "user": w.user_name, "created_at": w.created_at}


def _get(db: Db, wish_id: int) -> Wish:
    wish = db.get(Wish, wish_id)
    if wish is None:
        raise HTTPException(404, "Wunsch nicht gefunden.")
    return wish


@router.get("/mine")
def my_wishes(db: Db = Depends(get_db), user: User = Depends(create)):
    """Nur die eigenen Wünsche – andere sieht ein normaler Benutzer nicht."""
    rows = db.query(Wish).filter_by(user_id=user.id).order_by(Wish.created_at.desc())
    return [wish_out(w) for w in rows]


@router.post("")
def create_wish(data: WishIn, db: Db = Depends(get_db), user: User = Depends(create)):
    text = data.text.strip()
    if len(text) < 3:
        raise HTTPException(400, "Bitte den Wunsch kurz beschreiben.")
    first_status = next(iter(WISH_STATUSES))
    if db.query(Wish).filter_by(user_id=user.id, status=first_status).count() >= MAX_OPEN_PER_USER:
        raise HTTPException(400, "Sie haben bereits sehr viele offene Wünsche eingereicht.")
    wish = Wish(text=text, status=first_status, user_id=user.id,
                user_name=user.full_name or user.username, created_at=time.time())
    db.add(wish)
    db.commit()
    return wish_out(wish)


@router.get("")
def all_wishes(db: Db = Depends(get_db), _: User = Depends(manage)):
    return [wish_out(w) for w in db.query(Wish).order_by(Wish.created_at.desc())]


@router.put("/{wish_id}")
def set_status(wish_id: int, data: StatusIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    if data.status not in WISH_STATUSES:
        raise HTTPException(400, "Unbekannter Status.")
    wish = _get(db, wish_id)
    wish.status = data.status
    db.commit()
    return wish_out(wish)


@router.delete("/{wish_id}", status_code=204)
def delete_wish(wish_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    db.delete(_get(db, wish_id))
    db.commit()
