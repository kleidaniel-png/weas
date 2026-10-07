#!/bin/sh
# WEAS (Warenerfassungs- und Analysesystem) zum Ausprobieren starten (Linux/macOS).
# Nur auf diesem Rechner erreichbar. Für den Server: sudo bash deploy/install.sh
cd "$(dirname "$0")/backend" || exit 1
[ -d .venv ] || python3 -m venv .venv || exit 1
.venv/bin/pip install -q --disable-pip-version-check -r requirements.txt || exit 1
export LAGER_HOST="${LAGER_HOST:-127.0.0.1}"
echo "WEAS laeuft unter http://localhost:${LAGER_PORT:-8000}  (Beenden: Strg+C)"
exec .venv/bin/python run.py
