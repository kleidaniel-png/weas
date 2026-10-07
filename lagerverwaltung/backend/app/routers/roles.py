from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Role, User
from ..registry import PERMISSION_KEYS, PERMISSIONS
from ..security import current_user, require

router = APIRouter(prefix="/api", tags=["Rollen"])
manage = require("roles.manage")


class RoleIn(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    permissions: list[str] = []


def role_out(r: Role) -> dict:
    return {"id": r.id, "name": r.name, "is_system": r.is_system,
            "permissions": sorted(r.permission_set), "user_count": len(r.users)}


@router.get("/permissions")
def list_permissions(_: User = Depends(current_user)):
    return [{"key": k, "label": label, "group": group} for k, label, group in PERMISSIONS]


@router.get("/roles")
def list_roles(db: Db = Depends(get_db), user: User = Depends(current_user)):
    if not (user.can("roles.manage") or user.can("users.manage")):
        raise HTTPException(403, "Dafür fehlt Ihnen die Berechtigung.")
    return [role_out(r) for r in db.query(Role).order_by(Role.is_system.desc(), Role.name)]


def _guard(me: User, permissions: set[str]):
    """Wer Rollen verwaltet, darf nur Rechte vergeben oder ändern, die er selbst besitzt."""
    if not me.role.is_system and not permissions <= me.role.permission_set:
        raise HTTPException(403, "Sie können nur Rechte vergeben, die Sie selbst besitzen.")


def _save(db: Db, me: User, role: Role, data: RoleIn):
    unknown = set(data.permissions) - PERMISSION_KEYS
    if unknown:
        raise HTTPException(400, f"Unbekannte Rechte: {', '.join(sorted(unknown))}")
    _guard(me, set(data.permissions) | set(role.permissions or []))
    role.name = data.name.strip()
    role.permissions = sorted(set(data.permissions))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Eine Rolle mit diesem Namen gibt es bereits.")
    return role_out(role)


@router.post("/roles")
def create_role(data: RoleIn, db: Db = Depends(get_db), me: User = Depends(manage)):
    role = Role()
    db.add(role)
    return _save(db, me, role, data)


@router.put("/roles/{role_id}")
def update_role(role_id: int, data: RoleIn, db: Db = Depends(get_db), me: User = Depends(manage)):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Rolle nicht gefunden.")
    if role.is_system:
        raise HTTPException(400, "Die Administrator-Rolle kann nicht geändert werden.")
    return _save(db, me, role, data)


@router.delete("/roles/{role_id}", status_code=204)
def delete_role(role_id: int, db: Db = Depends(get_db), me: User = Depends(manage)):
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(404, "Rolle nicht gefunden.")
    if role.is_system:
        raise HTTPException(400, "Die Administrator-Rolle kann nicht gelöscht werden.")
    _guard(me, role.permission_set)
    if role.users:
        raise HTTPException(400, "Dieser Rolle sind noch Benutzer zugeordnet.")
    db.delete(role)
    db.commit()
