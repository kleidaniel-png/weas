"""Auswertungen über die Warenbewegungen."""
import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session as Db

from ..database import get_db
from ..models import Article, Movement, User
from ..registry import MOVEMENT_TYPES
from ..security import require
from .movements import movement_out

router = APIRouter(prefix="/api/analysis", tags=["Analyse"])
view = require("analysis.view")

DAILY_UP_TO_DAYS = 45  # längere Zeiträume werden nach Monaten zusammengefasst
TOP_N = 10


class Filters:
    """Gemeinsame Filter für Auswertung und Export."""

    def __init__(self, date_from: str | None = Query(None, alias="from", max_length=10),
                 date_to: str | None = Query(None, alias="to", max_length=10),
                 category_id: int | None = None, project_id: int | None = None,
                 article_id: int | None = None, user: str | None = Query(None, max_length=100)):
        self.start = self._day(date_from)
        end = self._day(date_to)
        self.end = end + timedelta(days=1) if end else None  # „bis“ ist einschließlich
        self.category_id, self.project_id, self.article_id, self.user = category_id, project_id, article_id, user

    @staticmethod
    def _day(text: str | None) -> datetime | None:
        if not text:
            return None
        try:
            return datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "Ungültiges Datum.")

    def movements(self, db: Db) -> list[Movement]:
        q = db.query(Movement).join(Article)
        if self.start:
            q = q.filter(Movement.created_at >= self.start.timestamp())
        if self.end:
            q = q.filter(Movement.created_at < self.end.timestamp())
        if self.category_id is not None:
            q = q.filter(Article.category_id == self.category_id)
        if self.project_id is not None:
            q = q.filter(Movement.project_id == self.project_id)
        if self.article_id is not None:
            q = q.filter(Movement.article_id == self.article_id)
        if self.user:
            q = q.filter(Movement.user_name == self.user)
        return q.order_by(Movement.created_at, Movement.id).all()


def _value(m: Movement) -> float:
    return abs(m.quantity) * m.unit_price


def _series(rows: list[Movement], f: Filters) -> list[dict]:
    """Warenwert von Eingang und Ausgang je Tag bzw. Monat, lückenlos."""
    if not rows and not (f.start and f.end):
        return []
    start = f.start or datetime.fromtimestamp(rows[0].created_at)
    end = f.end or datetime.fromtimestamp(rows[-1].created_at) + timedelta(days=1)
    daily = (end - start).days <= DAILY_UP_TO_DAYS
    key = (lambda d: d.strftime("%Y-%m-%d")) if daily else (lambda d: d.strftime("%Y-%m"))
    label = (lambda d: d.strftime("%d.%m.")) if daily else (lambda d: d.strftime("%m/%Y"))
    buckets: dict[str, dict] = {}
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day < end:
        buckets.setdefault(key(day), {"label": label(day), "in": 0.0, "out": 0.0, "count": 0})
        day += timedelta(days=1)
    for m in rows:
        bucket = buckets.get(key(datetime.fromtimestamp(m.created_at)))
        if bucket is None:
            continue
        bucket["count"] += 1
        if m.type in ("in", "out"):
            bucket[m.type] += _value(m)
    return [{**b, "in": round(b["in"], 2), "out": round(b["out"], 2)} for b in buckets.values()]


def _stock_history(db: Db, f: Filters) -> list[dict]:
    """Bestandsverlauf eines Artikels (nur wenn ein Artikel gewählt ist)."""
    if f.article_id is None:
        return []
    stock, points = 0.0, []
    lo = f.start.timestamp() if f.start else None
    hi = f.end.timestamp() if f.end else None
    for m in db.query(Movement).filter_by(article_id=f.article_id).order_by(Movement.created_at, Movement.id):
        if lo is not None and m.created_at >= lo and not points:
            points.append({"t": lo, "stock": stock})  # Stand zu Beginn des Zeitraums
        stock = round(stock + m.quantity, 3)
        if (lo is None or m.created_at >= lo) and (hi is None or m.created_at < hi):
            points.append({"t": m.created_at, "stock": stock})
    return points


def _slow_movers(db: Db, f: Filters) -> list[dict]:
    """Ladenhüter: Artikel mit Bestand, aber ohne Ausgang im Zeitraum."""
    # bewusst unabhängig von Artikel-, Projekt- und Mitarbeiterfilter
    out = db.query(Movement.article_id).filter(Movement.type == "out")
    if f.start:
        out = out.filter(Movement.created_at >= f.start.timestamp())
    if f.end:
        out = out.filter(Movement.created_at < f.end.timestamp())
    moved = {article_id for (article_id,) in out.distinct()}
    last_out = dict(db.query(Movement.article_id, func.max(Movement.created_at))
                    .filter(Movement.type == "out").group_by(Movement.article_id))
    q = db.query(Article).filter(Article.active, Article.stock > 0)
    if f.category_id is not None:
        q = q.filter(Article.category_id == f.category_id)
    slow = [{"id": a.id, "number": a.number, "name": a.name, "category": a.category.name, "stock": a.stock,
             "unit": a.unit, "value": round(a.stock * a.price, 2), "last_out": last_out.get(a.id)}
            for a in q if a.id not in moved and a.category.kind == "material"]
    return sorted(slow, key=lambda s: -s["value"])


@router.get("")
def analysis(f: Filters = Depends(), db: Db = Depends(get_db), _: User = Depends(view)):
    rows = f.movements(db)
    articles: dict[int, dict] = {}
    projects: dict[int, dict] = {}
    users: dict[str, int] = defaultdict(int)
    categories: dict[str, float] = defaultdict(float)
    in_value = out_value = 0.0
    for m in rows:
        a = m.article
        item = articles.setdefault(a.id, {"number": a.number, "name": a.name, "unit": a.unit, "count": 0, "out": 0.0})
        item["count"] += 1
        users[m.user_name] += 1
        if m.type == "in":
            in_value += _value(m)
        elif m.type == "out":
            out_value += _value(m)
            item["out"] += -m.quantity
            categories[a.category.name] += _value(m)
        if m.project and a.category.kind == "material":  # Verbrauch = Ausgang minus Rückgabe
            p = projects.setdefault(m.project_id, {"id": m.project_id, "name": m.project.name, "cost": 0.0})
            p["cost"] += -m.quantity * m.unit_price
    slow = _slow_movers(db, f)
    return {
        "kpis": {"count": len(rows), "in_value": round(in_value, 2), "out_value": round(out_value, 2),
                 "slow_count": len(slow)},
        "series": _series(rows, f),
        "stock_history": _stock_history(db, f),
        "top_articles": sorted(articles.values(), key=lambda i: -i["count"])[:TOP_N],
        "by_project": sorted(({**p, "cost": round(p["cost"], 2)} for p in projects.values()), key=lambda p: -p["cost"])[:TOP_N],
        "by_user": sorted(({"name": n, "count": c} for n, c in users.items()), key=lambda u: -u["count"]),
        "by_category": sorted(({"name": n, "value": round(v, 2)} for n, v in categories.items()), key=lambda c: -c["value"]),
        "slow": slow[:20],
        "movements": [movement_out(m) for m in reversed(rows[-200:])],
        "users": [n for (n,) in db.query(Movement.user_name).distinct().order_by(Movement.user_name)],
    }


def _text(value: str) -> str:
    """Verhindert, dass Excel Texte als Formel ausführt."""
    return "'" + value if value[:1] in ("=", "+", "-", "@", "\t", "\r") else value


def _num(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".").replace(".", ",")


@router.get("/export.csv")
def export(f: Filters = Depends(), db: Db = Depends(get_db), _: User = Depends(view)):
    """Bewegungen als CSV – öffnet sich direkt in Excel (Semikolon, Dezimalkomma)."""
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(["Datum", "Art", "Artikelnr.", "Artikel", "Kategorie", "Menge", "Einheit",
                     "Einzelpreis", "Wert", "Projekt", "Benutzer", "Bemerkung"])
    for m in f.movements(db):
        a = m.article
        writer.writerow([datetime.fromtimestamp(m.created_at).strftime("%d.%m.%Y %H:%M"), MOVEMENT_TYPES[m.type]["label"],
                         _text(a.number), _text(a.name), _text(a.category.name), _num(m.quantity), _text(a.unit),
                         _num(m.unit_price), _num(round(m.quantity * m.unit_price, 2)),
                         _text(m.project.name) if m.project else "", _text(m.user_name), _text(m.note)])
    return Response("﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="warenbewegungen.csv"'})
