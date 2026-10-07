#!/bin/bash
# Installiert ODER aktualisiert WEAS (Warenerfassungs- und Analysesystem) als Dienst auf Ubuntu Server.
# Der Dienst startet danach bei jedem Hochfahren von selbst.
#
#   sudo bash deploy/install.sh
#
# Die Daten liegen getrennt vom Programm in /var/lib/lagerverwaltung und bleiben
# bei einer Aktualisierung erhalten.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausführen: sudo $0"; exit 1; }

SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/lagerverwaltung
DATA=/var/lib/lagerverwaltung
RUN_AS=lager
ENV_FILE=/etc/lagerverwaltung.env

echo "== Pakete installieren"
apt-get update -qq
apt-get install -y -qq python3 python3-venv rsync

echo "== Benutzer und Ordner anlegen"
id "$RUN_AS" &>/dev/null || useradd --system --create-home --shell /bin/bash "$RUN_AS"
mkdir -p "$APP/backend" "$DATA"

echo "== Programm kopieren"
rsync -a --delete --exclude data --exclude .venv --exclude __pycache__ "$SRC/backend/" "$APP/backend/"
[ -d "$APP/backend/.venv" ] || python3 -m venv "$APP/backend/.venv"
"$APP/backend/.venv/bin/pip" install -q -r "$APP/backend/requirements.txt"
chown -R root:root "$APP"                 # Programm: für den Dienst nur lesbar
chown -R "$RUN_AS:$RUN_AS" "$DATA"
chmod 700 "$DATA"                        # Daten: nur der Dienst-Benutzer

# Eigene Einstellungen (bleiben bei Aktualisierungen erhalten)
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<ENV
# Einstellungen von WEAS. Nach Änderungen: sudo systemctl restart lagerverwaltung
LAGER_DATA_DIR=$DATA
LAGER_PORT=8000
# Datensicherungen auf ein anderes Laufwerk legen (empfohlen, z. B. USB-Platte oder NAS):
#LAGER_BACKUP_DIR=/mnt/sicherung
# (danach install.sh erneut ausführen, damit der Dienst dort schreiben darf)
ENV
fi
chown root:"$RUN_AS" "$ENV_FILE"; chmod 640 "$ENV_FILE"

# Zusätzlicher Sicherungsordner aus der Einstellungsdatei (falls gesetzt)
BACKUP_DIR="$(grep -E '^LAGER_BACKUP_DIR=' "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
EXTRA_PATHS=""
if [ -n "$BACKUP_DIR" ]; then
  mkdir -p "$BACKUP_DIR"; chown "$RUN_AS:$RUN_AS" "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"
  EXTRA_PATHS=" $BACKUP_DIR"
fi

echo "== Dienst einrichten"
cat > /etc/systemd/system/lagerverwaltung.service <<UNIT
[Unit]
Description=WEAS - Warenerfassungs- und Analysesystem
After=network.target

[Service]
User=$RUN_AS
WorkingDirectory=$APP/backend
EnvironmentFile=$ENV_FILE
# Zugriff auf den Bildschirm des Terminals (Tastaturumschaltung)
Environment=XAUTHORITY=/home/$RUN_AS/.Xauthority
ExecStart=$APP/backend/.venv/bin/python run.py
Restart=always
RestartSec=3
# Absicherung: Der Dienst darf außer seinem Datenordner nichts verändern
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=$DATA$EXTRA_PATHS
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable lagerverwaltung >/dev/null
systemctl restart lagerverwaltung

# Firewall öffnen, falls sie eingeschaltet ist
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
  ufw allow 8000/tcp >/dev/null
fi

sleep 2
systemctl --no-pager --lines=0 status lagerverwaltung || true
echo
echo "Fertig. Aufruf im Browser der Mitarbeiter-Rechner:"
for ip in $(hostname -I); do echo "   http://$ip:8000"; done
if [ -f "$DATA/einrichtungscode.txt" ]; then
  echo
  echo "Ersteinrichtung: Beim ersten Aufruf wird das Administrator-Konto angelegt."
  echo "Einrichtungscode (nur von anderen Rechnern nötig):  $(cat "$DATA/einrichtungscode.txt")"
fi
echo
echo "Terminal am Server einrichten:   sudo bash deploy/kiosk.sh"
echo "Verschlüsselung (HTTPS) einrichten: sudo bash deploy/https.sh"
