"""Datenbanktabellen. Neue Module (Artikel, Projekte, Bewegungen) kommen hier dazu."""
import time

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .registry import PERMISSION_KEYS


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    users: Mapped[list["User"]] = relationship(back_populates="role")

    @property
    def permission_set(self) -> set[str]:
        if self.is_system:
            return set(PERMISSION_KEYS)
        return set(self.permissions or []) & PERMISSION_KEYS


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    full_name: Mapped[str] = mapped_column(String(100), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(5), default="de")
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)  # arbeitet am Terminal des Servers
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    role: Mapped[Role] = relationship(back_populates="users")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def can(self, permission: str) -> bool:
        return permission in self.role.permission_set


class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user: Mapped[User] = relationship(back_populates="sessions")
    last_seen: Mapped[float] = mapped_column(Float, default=time.time)
    created_at: Mapped[float | None] = mapped_column(Float, default=time.time, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(500))


# --- Lager -------------------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    kind: Mapped[str] = mapped_column(String(20), default="material")
    articles: Mapped[list["Article"]] = relationship(back_populates="category")


class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category: Mapped[Category] = relationship(back_populates="articles")
    unit: Mapped[str] = mapped_column(String(20), default="Stück")
    stock: Mapped[float] = mapped_column(Float, default=0)
    min_stock: Mapped[float] = mapped_column(Float, default=0)
    location: Mapped[str] = mapped_column(String(100), default="")
    price: Mapped[float] = mapped_column(Float, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str] = mapped_column(String(500), default="")


class ArticleImage(Base):
    """Kleines Bild zum Artikel. Liegt in der Datenbank und ist damit in jeder Sicherung enthalten."""
    __tablename__ = "article_images"
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True)
    mime: Mapped[str] = mapped_column(String(30))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    customer: Mapped[str] = mapped_column(String(150), default="")
    address: Mapped[str] = mapped_column(String(200), default="")
    status: Mapped[str] = mapped_column(String(20), default="aktiv")
    note: Mapped[str] = mapped_column(String(500), default="")


class Movement(Base):
    """Jede Bestandsänderung. Wird nie gelöscht oder geändert."""
    __tablename__ = "movements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(20))
    article_id: Mapped[int] = mapped_column(ForeignKey("articles.id"), index=True)
    article: Mapped[Article] = relationship()
    quantity: Mapped[float] = mapped_column(Float)  # mit Vorzeichen: + Zugang, - Abgang
    unit_price: Mapped[float] = mapped_column(Float, default=0)  # Preis zum Zeitpunkt der Buchung
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True, nullable=True)
    project: Mapped[Project | None] = relationship()
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(100), default="")  # bleibt erhalten, auch wenn der Benutzer gelöscht wird
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)
    note: Mapped[str] = mapped_column(String(300), default="")
    # Lieferschein, zu dem die Buchung gehört (optional)
    delivery_note_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_notes.id", ondelete="SET NULL"), nullable=True, index=True)
    delivery_note: Mapped["DeliveryNote | None"] = relationship()
    # Bezeichnung und Einheit zum Zeitpunkt der Buchung: Ein Lieferschein ändert sich nicht, wenn der Artikel umbenannt wird
    article_name: Mapped[str] = mapped_column(String(150), default="")
    article_unit: Mapped[str] = mapped_column(String(20), default="")


class Wish(Base):
    """Funktionswunsch eines Benutzers."""
    __tablename__ = "wishes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(20), default="neu")
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    user_name: Mapped[str] = mapped_column(String(100), default="")  # bleibt erhalten, auch wenn der Benutzer gelöscht wird
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


# --- Lieferscheine -----------------------------------------------------------
class StoredFile(Base):
    """Hochgeladene Datei (Lieferschein-Foto/PDF, Firmenlogo). Liegt in der Datenbank, also auch in jeder Sicherung."""
    __tablename__ = "files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    mime: Mapped[str] = mapped_column(String(50))
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class DeliveryNote(Base):
    __tablename__ = "delivery_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)     # eingang | ausgang
    number: Mapped[str] = mapped_column(String(50), default="")   # eigene Nummer bzw. Nummer des Lieferanten
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)   # nur eigene: Jahr und laufende Nummer
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    partner: Mapped[str] = mapped_column(String(300), default="")  # Lieferant bzw. Empfänger (mehrzeilig)
    note: Mapped[str] = mapped_column(String(500), default="")
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    project: Mapped[Project | None] = relationship()
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[float] = mapped_column(Float, default=time.time, index=True)


class JsonStore(Base):
    """Kleine Ablage für zusammengesetzte Einstellungen (z. B. die Lieferschein-Vorlage)."""
    __tablename__ = "json_store"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
