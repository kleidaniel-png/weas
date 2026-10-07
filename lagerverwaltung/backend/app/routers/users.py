from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Role, Session, User
from ..registry import DEFAULT_LANGUAGE, LANGUAGES
from ..config import MAX_PASSWORD_LENGTH
from ..security import check_password_rules, hash_password, require

router = APIRouter(prefix="/api/users", tags=["Benutzer"])
manage = require("users.manage")


class UserIn(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    full_name: str = Field(default="", max_length=100)
    role_id: int
    active: bool = True
    language: str = DEFAULT_LANGUAGE
    is_terminal: bool = False
    password: str | None = Field(default=None, max_length=MAX_PASSWORD_LENGTH)


def user_out(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name,
            "active": u.active, "role_id": u.role_id, "role": u.role.name,
            "language": u.language, "is_terminal": u.is_terminal}


def _ensure_admin_remains(db: Db):
    """Es muss immer mindestens ein aktiver Administrator existieren."""
    db.flush()
    admins = db.query(User).join(Role).filter(Role.is_system, User.active).count()
    if admins == 0:
        db.rollback()
        raise HTTPException(400, "Es muss mindestens ein aktiver Administrator bestehen bleiben.")


def _guard(me: User, role: Role):
    """Niemand darf mehr Rechte vergeben oder antasten, als er selbst hat.

    Sonst könnte sich jemand mit dem Recht „Benutzer verwalten“ selbst zum
    Administrator machen oder das Passwort des Administrators ändern.
    """
    if me.role.is_system:
        return
    if role.is_system or not role.permission_set <= me.role.permission_set:
        raise HTTPException(403, "Diesen Benutzer oder diese Rolle darf nur ein Administrator verwalten.")


def _apply(db: Db, me: User, user: User, data: UserIn):
    role = db.get(Role, data.role_id)
    if role is None:
        raise HTTPException(400, "Die gewählte Rolle existiert nicht.")
    _guard(me, role)
    if data.language not in LANGUAGES:
        raise HTTPException(400, "Unbekannte Sprache.")
    user.language, user.is_terminal = data.language, data.is_terminal
    user.username = data.username.strip().lower()
    user.full_name = data.full_name.strip()
    user.role_id = data.role_id
    user.active = data.active
    if data.password:
        check_password_rules(data.password)
        user.password_hash = hash_password(data.password)


def _commit(db: Db):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Dieser Benutzername ist bereits vergeben.")


@router.get("")
def list_users(db: Db = Depends(get_db), _: User = Depends(manage)):
    return [user_out(u) for u in db.query(User).order_by(User.username)]


@router.post("")
def create_user(data: UserIn, db: Db = Depends(get_db), me: User = Depends(manage)):
    if not data.password:
        raise HTTPException(400, "Bitte ein Passwort vergeben.")
    user = User()
    _apply(db, me, user, data)
    db.add(user)
    _commit(db)
    return user_out(user)


@router.put("/{user_id}")
def update_user(user_id: int, data: UserIn, db: Db = Depends(get_db), me: User = Depends(manage)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Benutzer nicht gefunden.")
    if user.id == me.id and not data.active:
        raise HTTPException(400, "Sie können sich nicht selbst deaktivieren.")
    _guard(me, user.role)
    _apply(db, me, user, data)
    _ensure_admin_remains(db)
    if not data.active or (data.password and user.id != me.id):
        db.query(Session).filter_by(user_id=user.id).delete()  # sofort abmelden
    _commit(db)
    db.refresh(user)
    return user_out(user)


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, db: Db = Depends(get_db), me: User = Depends(manage)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Benutzer nicht gefunden.")
    if user.id == me.id:
        raise HTTPException(400, "Sie können sich nicht selbst löschen.")
    _guard(me, user.role)
    db.delete(user)
    _ensure_admin_remains(db)
    db.commit()
