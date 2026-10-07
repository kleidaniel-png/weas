"""Zentrale Konfiguration. Alle Werte lassen sich per Umgebungsvariable überschreiben."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("LAGER_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'lager.db'}"
STATIC_DIR = BASE_DIR / "static"  # gebaute Oberfläche (npm run build)

HOST = os.environ.get("LAGER_HOST", "0.0.0.0")  # 0.0.0.0 = im Firmennetz erreichbar
PORT = int(os.environ.get("LAGER_PORT", "8000"))

# Datensicherungen. Auf ein anderes Laufwerk legen: LAGER_BACKUP_DIR=/mnt/sicherung
BACKUP_DIR = Path(os.environ.get("LAGER_BACKUP_DIR", DATA_DIR / "backups"))

# Tastatur am Server-Terminal umschalten ({layout} wird ersetzt). Leer = aus.
# Unter Windows (Testbetrieb) standardmäßig aus.
KEYBOARD_COMMAND = os.environ.get(
    "LAGER_KEYBOARD_COMMAND",
    "" if os.name == "nt" else "setxkbmap -display :0 -layout {layout} -option grp:alt_shift_toggle")

# Verschlüsselte Verbindung (HTTPS): beide Dateien angeben, siehe deploy/https.sh
SSL_CERT = os.environ.get("LAGER_SSL_CERT") or None
SSL_KEY = os.environ.get("LAGER_SSL_KEY") or None

# --- Sicherheit --------------------------------------------------------------
MAX_PASSWORD_LENGTH = 200              # schützt vor absichtlich riesigen Eingaben
MAX_BODY_BYTES = 8 * 1024 * 1024       # größte erlaubte Anfrage
MAX_FILE_BYTES = 5 * 1024 * 1024       # angehängter Lieferschein (Foto oder PDF)
MAX_LOGO_BYTES = 1 * 1024 * 1024       # Firmenlogo
SESSION_MAX_DAYS = 30                  # spätestens dann neu anmelden (auch bei „Angemeldet bleiben“)
LOGIN_MAX_ATTEMPTS = 5                 # Fehlversuche je Benutzername und Rechner ...
LOGIN_LOCK_SECONDS = 60                # ... danach so lange gesperrt
LOGIN_MAX_ATTEMPTS_PER_ADDRESS = 30    # Fehlversuche je Rechner in 10 Minuten (alle Benutzernamen)
SETUP_CODE_FILE = DATA_DIR / "einrichtungscode.txt"  # nur bis zur Ersteinrichtung vorhanden


SESSION_COOKIE = "lager_session"
MIN_PASSWORD_LENGTH = 8
MAX_IMAGE_BYTES = 2 * 1024 * 1024  # Artikelbild (wird im Browser vorher verkleinert)
