from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Movement, Project, User
from ..registry import PROJECT_STATUSES
from ..security import require, require_any

router = APIRouter(prefix="/api/projects", tags=["Projekte"])
view = require_any("projects.view", "movements.out")  # zum Buchen muss man Projekte auswählen können
manage = require("projects.manage")


class ProjectIn(BaseModel):
    number: str = Field(default="", max_length=30)  # leer = automatisch
    name: str = Field(min_length=1, max_length=150)
    customer: str = Field(default="", max_length=150)
    address: str = Field(default="", max_length=200)
    status: str = "aktiv"
    note: str = Field(default="", max_length=500)


def project_out(p: Project) -> dict:
    return {"id": p.id, "number": p.number, "name": p.name, "customer": p.customer,
            "address": p.address, "status": p.status, "note": p.note}


def _get(db: Db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Projekt nicht gefunden.")
    return project


def _save(db: Db, project: Project, data: ProjectIn):
    if data.status not in PROJECT_STATUSES:
        raise HTTPException(400, "Unbekannter Status.")
    for field in ("name", "customer", "address", "note"):
        setattr(project, field, getattr(data, field).strip())
    project.status = data.status
    project.number = data.number.strip() or project.number or f"tmp-{id(project)}"
    try:
        db.flush()
        if project.number.startswith("tmp-"):
            project.number = f"P-{project.id:04d}"
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Diese Projektnummer ist bereits vergeben.")
    return project_out(project)


@router.get("")
def list_projects(db: Db = Depends(get_db), _: User = Depends(view)):
    return [project_out(p) for p in db.query(Project).order_by(Project.status, Project.name)]


@router.post("")
def create_project(data: ProjectIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    project = Project()
    db.add(project)
    return _save(db, project, data)


@router.put("/{project_id}")
def update_project(project_id: int, data: ProjectIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    return _save(db, _get(db, project_id), data)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    project = _get(db, project_id)
    if db.query(Movement).filter_by(project_id=project.id).count():
        raise HTTPException(400, "Auf dieses Projekt wurde bereits gebucht. Bitte stattdessen abschließen.")
    db.delete(project)
    db.commit()


@router.get("/{project_id}/summary")
def project_summary(project_id: int, db: Db = Depends(get_db), _: User = Depends(require("projects.view"))):
    """Was wurde auf das Projekt gebucht: je Artikel ausgegeben, zurück, offen und Materialkosten."""
    project = _get(db, project_id)
    items: dict[int, dict] = {}
    for m in db.query(Movement).filter_by(project_id=project.id):
        a = m.article
        item = items.setdefault(a.id, {"article_id": a.id, "number": a.number, "name": a.name, "unit": a.unit,
                                       "kind": a.category.kind, "out": 0.0, "returned": 0.0, "cost": 0.0})
        if m.quantity < 0:
            item["out"] += -m.quantity
        else:
            item["returned"] += m.quantity
        if item["kind"] == "material":
            item["cost"] += -m.quantity * m.unit_price
    for item in items.values():
        item["open"] = round(item["out"] - item["returned"], 3)
        item["cost"] = round(item["cost"], 2)
    rows = sorted(items.values(), key=lambda i: i["name"])
    return {"project": project_out(project), "items": rows,
            "material_cost": round(sum(i["cost"] for i in rows), 2)}
