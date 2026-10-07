from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


@event.listens_for(engine, "connect")
def _sqlite_pragmas(conn, _):
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")  # mehrere Rechner gleichzeitig lesen/schreiben
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def _literal(value) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def migrate():
    """Ergänzt neue Spalten in bestehenden Tabellen (bestehende Daten bleiben erhalten).

    Damit genügt es, ein neues Feld in models.py einzutragen – mit `default=...`.
    """
    with engine.begin() as conn:
        existing_tables = inspect(conn)  # dieselbe Verbindung liest und ändert
        for table in Base.metadata.sorted_tables:
            if not existing_tables.has_table(table.name):
                continue
            existing = {c["name"] for c in existing_tables.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {column.type.compile(engine.dialect)}'
                if column.default is not None and column.default.is_scalar:
                    ddl += f" DEFAULT {_literal(column.default.arg)}"
                conn.execute(text(ddl))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
