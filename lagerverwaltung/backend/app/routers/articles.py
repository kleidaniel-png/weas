import base64
import binascii
import time

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as Db

from ..config import MAX_IMAGE_BYTES
from ..database import get_db
from ..models import Article, ArticleImage, Category, Movement, User
from ..registry import DELIVERY_KINDS, CATEGORY_KINDS, DEFAULT_UNITS, MOVEMENT_TYPES, PROJECT_STATUSES, WISH_STATUSES
from ..security import current_user, require
from ..stock import book

router = APIRouter(prefix="/api", tags=["Artikel"])
view = require("articles.view")
manage = require("articles.manage")


@router.get("/meta")
def meta(db: Db = Depends(get_db), _: User = Depends(current_user)):
    """Auswahllisten für die Oberfläche (kommen aus registry.py)."""
    used = {u for (u,) in db.query(Article.unit).distinct()}
    return {
        "category_kinds": CATEGORY_KINDS,
        "project_statuses": PROJECT_STATUSES,
        "wish_statuses": WISH_STATUSES,
        "delivery_kinds": DELIVERY_KINDS,
        "movement_types": {k: {"label": v["label"], "permission": v["permission"], "project": v["project"],
                               "delivery": v.get("delivery")}
                           for k, v in MOVEMENT_TYPES.items()},
        "units": DEFAULT_UNITS + sorted(used - set(DEFAULT_UNITS)),
    }


# --- Kategorien --------------------------------------------------------------
class CategoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=50)
    kind: str = "material"


def category_out(c: Category) -> dict:
    return {"id": c.id, "name": c.name, "kind": c.kind, "article_count": len(c.articles)}


@router.get("/categories")
def list_categories(db: Db = Depends(get_db), _: User = Depends(view)):
    return [category_out(c) for c in db.query(Category).order_by(Category.name)]


def _save_category(db: Db, category: Category, data: CategoryIn):
    if data.kind not in CATEGORY_KINDS:
        raise HTTPException(400, "Unbekannte Art.")
    category.name, category.kind = data.name.strip(), data.kind
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Eine Kategorie mit diesem Namen gibt es bereits.")
    return category_out(category)


@router.post("/categories")
def create_category(data: CategoryIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    category = Category()
    db.add(category)
    return _save_category(db, category, data)


@router.put("/categories/{category_id}")
def update_category(category_id: int, data: CategoryIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Kategorie nicht gefunden.")
    return _save_category(db, category, data)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(404, "Kategorie nicht gefunden.")
    if category.articles:
        raise HTTPException(400, "Dieser Kategorie sind noch Artikel zugeordnet.")
    db.delete(category)
    db.commit()


# --- Artikel -----------------------------------------------------------------
MAX_NUMBER = 1_000_000_000  # größte erlaubte Menge bzw. größter Preis


class ArticleIn(BaseModel):
    number: str = Field(default="", max_length=30)  # leer = automatisch
    name: str = Field(min_length=1, max_length=150)
    category_id: int
    unit: str = Field(min_length=1, max_length=20)
    min_stock: float = Field(default=0, ge=0, le=MAX_NUMBER, allow_inf_nan=False)
    location: str = Field(default="", max_length=100)
    price: float = Field(default=0, ge=0, le=MAX_NUMBER, allow_inf_nan=False)
    active: bool = True
    note: str = Field(default="", max_length=500)
    initial_stock: float = Field(default=0, ge=0, le=MAX_NUMBER, allow_inf_nan=False)  # nur beim Anlegen


def article_out(a: Article, image_version: float | None) -> dict:
    return {"image": f"/api/articles/{a.id}/image?v={int(image_version * 1000)}" if image_version else None,
            "id": a.id, "number": a.number, "name": a.name, "category_id": a.category_id,
            "category": a.category.name, "kind": a.category.kind, "unit": a.unit, "stock": a.stock,
            "min_stock": a.min_stock, "low": a.active and a.stock < a.min_stock,
            "location": a.location, "price": a.price, "active": a.active, "note": a.note}


def _apply(db: Db, article: Article, data: ArticleIn):
    if db.get(Category, data.category_id) is None:
        raise HTTPException(400, "Die gewählte Kategorie existiert nicht.")
    for field in ("name", "unit", "location", "note"):
        setattr(article, field, getattr(data, field).strip())
    article.category_id, article.min_stock = data.category_id, data.min_stock
    article.price, article.active = data.price, data.active
    article.number = data.number.strip() or article.number or f"tmp-{id(article)}"
    try:
        db.flush()
        if article.number.startswith("tmp-"):
            article.number = f"A-{article.id:04d}"
            db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Diese Artikelnummer ist bereits vergeben.")


@router.get("/articles")
def list_articles(db: Db = Depends(get_db), _: User = Depends(view)):
    versions = dict(db.query(ArticleImage.article_id, ArticleImage.updated_at))
    return [article_out(a, versions.get(a.id)) for a in db.query(Article).order_by(Article.name)]


@router.post("/articles")
def create_article(data: ArticleIn, db: Db = Depends(get_db), user: User = Depends(manage)):
    article = Article(stock=0)
    db.add(article)
    _apply(db, article, data)
    db.commit()
    if data.initial_stock > 0 and article.active:
        book(db, user, "correction", article.id, data.initial_stock, note="Anfangsbestand")
    return article_out(article, None)


@router.put("/articles/{article_id}")
def update_article(article_id: int, data: ArticleIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(404, "Artikel nicht gefunden.")
    _apply(db, article, data)
    db.commit()
    db.refresh(article)
    image = db.get(ArticleImage, article.id)
    return article_out(article, image.updated_at if image else None)


@router.delete("/articles/{article_id}", status_code=204)
def delete_article(article_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(404, "Artikel nicht gefunden.")
    if db.query(Movement).filter_by(article_id=article.id).count():
        raise HTTPException(400, "Zu diesem Artikel gibt es Buchungen. Bitte stattdessen deaktivieren.")
    db.delete(article)
    db.commit()


# --- Artikelbild -------------------------------------------------------------
class ImageIn(BaseModel):
    data: str = Field(max_length=MAX_IMAGE_BYTES * 2)  # Data-URL ("data:image/jpeg;base64,...") oder reines Base64


def _image_type(data: bytes) -> str | None:
    """Erkennt den Bildtyp am Inhalt – der Dateiname wird nicht geglaubt."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


@router.get("/articles/{article_id}/image")
def get_image(article_id: int, db: Db = Depends(get_db), _: User = Depends(view)):
    image = db.get(ArticleImage, article_id)
    if image is None:
        raise HTTPException(404, "Kein Bild vorhanden.")
    # Die Adresse enthält eine Versionsnummer, deshalb darf der Browser das Bild behalten
    return Response(image.data, media_type=image.mime,
                    headers={"Cache-Control": "private, max-age=31536000, immutable",
                             "X-Content-Type-Options": "nosniff"})


@router.put("/articles/{article_id}/image")
def set_image(article_id: int, body: ImageIn, db: Db = Depends(get_db), _: User = Depends(manage)):
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(404, "Artikel nicht gefunden.")
    try:
        data = base64.b64decode(body.data.split(",", 1)[-1], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(400, "Das Bild konnte nicht gelesen werden.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(400, "Das Bild ist zu groß.")
    mime = _image_type(data)
    if mime is None:
        raise HTTPException(400, "Nur Bilder (JPEG, PNG, WebP) sind erlaubt.")
    image = db.merge(ArticleImage(article_id=article.id, mime=mime, data=data, updated_at=time.time()))
    db.commit()
    return article_out(article, image.updated_at)


@router.delete("/articles/{article_id}/image", status_code=204)
def delete_image(article_id: int, db: Db = Depends(get_db), _: User = Depends(manage)):
    db.query(ArticleImage).filter_by(article_id=article_id).delete()
    db.commit()
