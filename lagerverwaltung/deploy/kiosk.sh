#!/bin/bash
# Richtet den Bildschirm des Servers als Terminal ein (Ubuntu Server, ohne Desktop):
# Nach dem Hochfahren erscheint automatisch WEAS im Vollbild.
#
#   sudo bash deploy/kiosk.sh        (vorher: sudo bash deploy/install.sh)
#
# Zurück zur normalen Anmeldung am Bildschirm:
#   sudo rm /etc/systemd/system/getty@tty1.service.d/autologin.conf && sudo reboot
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Bitte mit sudo ausführen: sudo $0"; exit 1; }

RUN_AS=lager
HOME_DIR=/home/$RUN_AS
URL=http://localhost:8000
EXTRA_FLAGS=""
# Mit HTTPS (deploy/https.sh): Das selbst ausgestellte Zertifikat gilt nur für diesen
# lokalen Aufruf als vertrauenswürdig – die Verbindung verlässt den Rechner nicht.
if grep -qE '^LAGER_SSL_CERT=' /etc/lagerverwaltung.env 2>/dev/null; then
  URL=https://localhost:8000
  EXTRA_FLAGS="--ignore-certificate-errors"
fi
id "$RUN_AS" &>/dev/null || { echo "Bitte zuerst install.sh ausführen."; exit 1; }

echo "== Pakete installieren (Bildschirm, Fenster, Browser)"
apt-get update -qq
apt-get install -y -qq --no-install-recommends xserver-xorg xinit openbox x11-xserver-utils x11-xkb-utils
command -v chromium >/dev/null || snap install chromium
usermod -aG video,input,tty "$RUN_AS"

echo "== Automatische Anmeldung am Bildschirm"
mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf <<UNIT
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $RUN_AS --noclear %I \$TERM
UNIT

# Nach der Anmeldung am Bildschirm sofort die grafische Oberfläche starten
cat > "$HOME_DIR/.bash_profile" <<'PROFILE'
if [ -z "${DISPLAY:-}" ] && [ "$(tty)" = "/dev/tty1" ]; then
  exec startx
fi
PROFILE

cat > "$HOME_DIR/.xinitrc" <<XINIT
#!/bin/bash
xset s off; xset -dpms; xset s noblank      # Bildschirm bleibt an
setxkbmap de                                # danach stellt WEAS um
openbox &
# warten, bis WEAS läuft
while ! (exec 3<>/dev/tcp/127.0.0.1/8000) 2>/dev/null; do sleep 1; done
exec chromium --kiosk --incognito --no-first-run --disable-translate \\
     --disable-pinch --overscroll-history-navigation=0 $EXTRA_FLAGS $URL
XINIT
chown "$RUN_AS:$RUN_AS" "$HOME_DIR/.bash_profile" "$HOME_DIR/.xinitrc"
chmod +x "$HOME_DIR/.xinitrc"

systemctl daemon-reload
echo
echo "Fertig. Nach einem Neustart (sudo reboot) zeigt der Bildschirm WEAS."
echo "Wird der Browser geschlossen, startet er von selbst neu."
