from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Setting, User
from ..registry import SETTINGS
from ..security import get_setting, require

router = APIRouter(prefix="/api/settings", tags=["Einstellungen"])
manage = require("settings.manage")


def _all(db: Db) -> list[dict]:
    return [{"key": key, **spec, "value": get_setting(db, key)} for key, spec in SETTINGS.items()]


@router.get("")
def list_settings(db: Db = Depends(get_db), _: User = Depends(manage)):
    return _all(db)


@router.put("")
def update_settings(values: dict, db: Db = Depends(get_db), _: User = Depends(manage)):
    for key, value in values.items():
        spec = SETTINGS.get(key)
        if spec is None:
            raise HTTPException(400, f"Unbekannte Einstellung: {key}")
        if spec["type"] == "number":
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise HTTPException(400, f"„{spec['label']}“ muss eine Zahl sein.")
            if not spec["min"] <= value <= spec["max"]:
                raise HTTPException(400, f"„{spec['label']}“ muss zwischen {spec['min']} und {spec['max']} liegen.")
        elif spec["type"] == "bool":
            value = "1" if value in (True, "1", "true", 1) else "0"
        elif spec["type"] == "select":
            if value not in spec["options"]:
                raise HTTPException(400, f"„{spec['label']}“: ungültige Auswahl.")
        else:
            value = str(value).strip()
            if not value:
                raise HTTPException(400, f"„{spec['label']}“ darf nicht leer sein.")
        db.merge(Setting(key=key, value=str(value)))
    db.commit()
    return _all(db)
