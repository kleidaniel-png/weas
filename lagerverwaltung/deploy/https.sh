#!/bin/bash
# Schaltet die verschlüsselte Verbindung (HTTPS) ein – empfohlen, sobald Handys
# über WLAN zugreifen. Ohne HTTPS laufen Passwörter unverschlüsselt durchs Netz.
#
#   sudo bash deploy/https.sh        (vorher: sudo bash deploy/install.sh)
#
# Es wird ein selbst ausgestelltes Zertifikat erzeugt (10 Jahre gültig). Jeder
# Browser zeigt deshalb beim ersten Aufruf einmalig eine Warnung, die bestätigt
# werden muss. Die Adresse lautet danach https://... statt http://...
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausführen: sudo bash $0"; exit 1; }

RUN_AS=lager
DIR=/etc/lagerverwaltung
ENV_FILE=/etc/lagerverwaltung.env
[ -f "$ENV_FILE" ] || { echo "Bitte zuerst install.sh ausführen."; exit 1; }

apt-get install -y -qq openssl
mkdir -p "$DIR"

# Zertifikat für den Rechnernamen und alle aktuellen Adressen des Servers
NAMES="DNS:localhost,DNS:$(hostname),IP:127.0.0.1"
for ip in $(hostname -I); do NAMES="$NAMES,IP:$ip"; done
openssl req -x509 -newkey rsa:2048 -nodes -days 3650 \
  -keyout "$DIR/server.key" -out "$DIR/server.crt" \
  -subj "/CN=$(hostname)" -addext "subjectAltName=$NAMES" 2>/dev/null
chown root:"$RUN_AS" "$DIR/server.key" "$DIR/server.crt"
chmod 640 "$DIR/server.key"; chmod 644 "$DIR/server.crt"

sed -i '/^LAGER_SSL_CERT=/d; /^LAGER_SSL_KEY=/d' "$ENV_FILE"
echo "LAGER_SSL_CERT=$DIR/server.crt" >> "$ENV_FILE"
echo "LAGER_SSL_KEY=$DIR/server.key" >> "$ENV_FILE"
systemctl restart lagerverwaltung

echo
echo "HTTPS ist eingeschaltet. Neue Adresse:"
for ip in $(hostname -I); do echo "   https://$ip:8000"; done
echo "Falls das Terminal eingerichtet ist: sudo bash deploy/kiosk.sh erneut ausführen."
echo "Ändert sich die Adresse des Servers, dieses Skript erneut ausführen."
