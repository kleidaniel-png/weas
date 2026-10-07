"""Zentrale Listen für Rechte, Einstellungen und Standardrollen.

Neue Rechte oder Einstellungen werden NUR hier ergänzt – die Oberfläche
(Rollen-Editor, Einstellungsseite) baut sich automatisch daraus auf.
"""

# --- Rechte: (Schlüssel, Bezeichnung, Gruppe) --------------------------------
PERMISSIONS = [
    ("articles.view", "Artikel und Bestand ansehen", "Artikel"),
    ("articles.manage", "Artikel und Kategorien bearbeiten", "Artikel"),
    ("movements.in", "Wareneingang buchen", "Warenbewegungen"),
    ("movements.out", "Warenausgang buchen", "Warenbewegungen"),
    ("movements.correct", "Bestand korrigieren", "Warenbewegungen"),
    ("projects.view", "Projekte ansehen", "Projekte"),
    ("projects.manage", "Projekte anlegen und bearbeiten", "Projekte"),
    ("analysis.view", "Analyse ansehen", "Analyse"),
    ("users.manage", "Benutzer verwalten", "Verwaltung"),
    ("roles.manage", "Rollen und Rechte verwalten", "Verwaltung"),
    ("settings.manage", "Allgemeine Einstellungen ändern", "Verwaltung"),
    ("delivery.view", "Lieferscheine ansehen", "Lieferscheine"),
    ("delivery.manage", "Lieferscheine löschen und Vorlage bearbeiten", "Lieferscheine"),
    ("wishes.create", "Funktionswünsche einreichen", "Wünsche"),
    ("wishes.manage", "Alle Funktionswünsche ansehen und bearbeiten", "Wünsche"),
    ("session.stay_logged_in", "Angemeldet bleiben (keine automatische Abmeldung)", "Sitzung"),
]
PERMISSION_KEYS = {p[0] for p in PERMISSIONS}

# --- Name des Programms -------------------------------------------------------
PRODUCT_NAME = "WEAS"
PRODUCT_LONG_NAME = "Warenerfassungs- und Analysesystem"

# --- Sprachen ----------------------------------------------------------------
# keyboard = Tastaturlayout am Server-Terminal. Bei kyrillischen Layouts bleibt
# Englisch als zweites Layout erhalten (Umschalten mit Alt+Umschalt).
# Neue Sprache: hier eintragen und in frontend/src/locales/ eine Datei anlegen.
LANGUAGES = {
    "de": {"label": "Deutsch", "keyboard": "de"},
    "en": {"label": "English", "keyboard": "us"},
    "ru": {"label": "Русский", "keyboard": "ru,us"},
    "uk": {"label": "Українська", "keyboard": "ua,us"},
}
DEFAULT_LANGUAGE = "de"

# --- Einstellungen -----------------------------------------------------------
# type: text | number (min, max) | bool | select (options)
SETTINGS = {
    "company_name": {"label": "Firmenname", "type": "text", "default": PRODUCT_NAME},
    "idle_timeout_minutes": {
        "label": "Automatische Abmeldung nach (Minuten)",
        "type": "number", "default": 5, "min": 1, "max": 240,
    },
    "backup_keep_days": {
        "label": "Datensicherungen aufbewahren (Tage)",
        "type": "number", "default": 30, "min": 1, "max": 3650,
    },
    "terminal_language": {
        "label": "Tastatur am Terminal ohne Anmeldung",
        "type": "select", "default": DEFAULT_LANGUAGE,
        "options": {code: lang["label"] for code, lang in LANGUAGES.items()},
    },
    "scanner_enabled": {"label": "Scanner-Tab anzeigen", "type": "bool", "default": True},
}

# --- Rollen, die beim ersten Start angelegt werden ---------------------------
ADMIN_ROLE = "Administrator"  # Systemrolle: hat immer alle Rechte
DEFAULT_ROLES = {
    "Lagerist": ["articles.view", "articles.manage", "movements.in", "movements.out",
                 "movements.correct", "projects.view", "projects.manage", "analysis.view", "delivery.view", "wishes.create"],
    "Mitarbeiter": ["articles.view", "movements.out", "projects.view", "wishes.create"],
}

# --- Lager -------------------------------------------------------------------
# Art einer Kategorie: bestimmt, ob Kosten aufs Projekt laufen (Material)
# oder ob der Artikel nur ausgeliehen wird (Werkzeug).
CATEGORY_KINDS = {
    "material": "Material (wird verbraucht)",
    "werkzeug": "Werkzeug (wird ausgegeben und zurückgegeben)",
}
DEFAULT_CATEGORIES = [("Material", "material"), ("Werkzeug", "werkzeug")]
DEFAULT_UNITS = ["Stück", "m", "m²", "m³", "kg", "l", "Sack", "Rolle", "Paket", "Palette"]

# Bewegungsarten: sign = Wirkung auf den Bestand, project = Projekt wählbar,
# delivery = Art des Lieferscheins, der an die Buchung gehängt werden kann
MOVEMENT_TYPES = {
    "in": {"label": "Wareneingang", "permission": "movements.in", "sign": 1, "project": False, "delivery": "eingang"},
    "out": {"label": "Warenausgang", "permission": "movements.out", "sign": -1, "project": True, "delivery": "ausgang"},
    "return": {"label": "Rückgabe", "permission": "movements.out", "sign": 1, "project": True},
    "correction": {"label": "Korrektur", "permission": "movements.correct", "sign": 0, "project": False},
}
PROJECT_STATUSES = {"aktiv": "Aktiv", "abgeschlossen": "Abgeschlossen"}

# Funktionswünsche: Bearbeitungsstand (erster Eintrag = Stand eines neuen Wunsches)
WISH_STATUSES = {"neu": "Neu", "geplant": "Geplant", "erledigt": "Erledigt", "abgelehnt": "Abgelehnt"}

# --- Lieferscheine -----------------------------------------------------------
# eingang = Beleg des Lieferanten (wird angehängt), ausgang = eigener Lieferschein (wird erzeugt)
DELIVERY_KINDS = {"eingang": "Eingang", "ausgang": "Ausgang"}

# Vorlage des eigenen Lieferscheins. Jeder Eintrag ist im Programm unter
# Lieferscheine > Vorlage änderbar. Neues Feld: hier ergänzen, im Editor
# (DeliveryTemplate.jsx) ein Eingabefeld und im Dokument (DeliveryNoteDocument.jsx) die Ausgabe.
DELIVERY_TEMPLATE = {
    "title": "Lieferschein",
    "number_prefix": "LS-",
    "company_name": "",
    "company_address": "",       # mehrzeilig
    "company_contact": "",       # mehrzeilig: Telefon, E-Mail, Web
    "intro_text": "",
    "footer_text": "",
    "logo_position": "left",     # left | center | right
    "logo_size": "medium",       # small | medium | large
    "show_article_number": True,
    "show_prices": False,
    "show_project": True,
    "show_signatures": True,
}
DELIVERY_TEMPLATE_CHOICES = {"logo_position": ("left", "center", "right"), "logo_size": ("small", "medium", "large")}
