# WEAS – Warenerfassungs- und Analysesystem

Web-Anwendung für Lager, Projekte und Warenbewegungen. Läuft auf dem Server-Rechner,
alle anderen Rechner öffnen sie im Browser.

Technische Namen (Ordner `lagerverwaltung`, Dienst `lagerverwaltung`, Benutzer `lager`)
bleiben unverändert, damit Aktualisierungen bestehende Installationen nicht brechen.

## Installation

Schritt für Schritt in **`INSTALLATION.md`** (Test unter Windows, Einrichtung
auf Ubuntu Server). Die Bedienung beschreibt `ANLEITUNG.md`.

Kurzfassung Server: `sudo bash deploy/install.sh` – optional danach
`deploy/https.sh` (Verschlüsselung) und `deploy/kiosk.sh` (Terminal).
Kurzfassung Test: `start.bat` (Windows) bzw. `./start.sh` (Linux), nur auf dem
eigenen Rechner erreichbar.

## Aufbau

```
backend/app/
  registry.py   Rechte, Einstellungen, Standardrollen  <- zentrale Listen
  models.py     Datenbanktabellen
  security.py   Passwörter, Sitzungen, Rechteprüfung
  stock.py      Bestandsbuchung (einzige Stelle, die Bestände ändert)
  live.py       Live-Abgleich: meldet Änderungen an alle offenen Fenster
  backup.py     tägliche Datensicherung
  keyboard.py   Tastaturumschaltung am Terminal
  routers/      je Modul eine Datei (auth, users, roles, settings,
                articles, projects, movements, analysis, backups,
                delivery, wishes)
  main.py       bindet die Router ein
backend/tests/  python tests/test_api.py
frontend/src/
  routes.jsx    Navigation + Seiten                    <- zentrale Liste
  i18n.js       Mehrsprachigkeit: t("deutscher Text")
  locales/      Übersetzungen (en, ru, uk); Schlüssel ist der deutsche Text
  live.js       Live-Abgleich: in einer Seite genügt `useLive(load)`
  image.js      Bilder vor dem Hochladen verkleinern (Größe/Qualität einstellbar)
  components/   ui.jsx (Bausteine), Layout.jsx, MovementTable.jsx, ImagePicker.jsx,
                charts.jsx (Diagramme)
  format.js     Darstellung von Zahlen, Geld, Datum
  pages/        je Seite eine Datei
  index.css     Farben und Schrift
```

## Typische Änderungen

| Ziel | Wo |
|---|---|
| Neues Recht | eine Zeile in `registry.py` (PERMISSIONS) – erscheint automatisch im Rollen-Editor |
| Neue Einstellung | ein Eintrag in `registry.py` (SETTINGS) – erscheint automatisch unter „Allgemein“ |
| Neue Bewegungsart, Einheit oder Kategorie-Art | ein Eintrag in `registry.py` |
| Text ändern oder übersetzen | deutscher Text steht in der Seite, Übersetzung in `locales/<sprache>.js`; fehlt sie, erscheint Deutsch |
| Neue Sprache | Eintrag in `registry.py` (LANGUAGES, mit Tastaturlayout), Datei in `locales/`, Eintrag in `i18n.js` |
| Programmteil ein-/ausschaltbar machen | bool-Einstellung in `registry.py`, in `auth.py` unter `features`, in `routes.jsx` als `feature` |
| Neues Feld in einer Tabelle | Spalte mit `default=...` in `models.py` – wird beim Start automatisch ergänzt |
| Route absichern | `Depends(require("recht.name"))` |
| Neues Modul | Tabelle in `models.py`, Datei in `routers/`, Eintrag in `main.py` (ROUTERS) |
| Neue Seite | Datei in `pages/`, eine Zeile in `routes.jsx` |
| Farben (Palette, Diagramme) | `frontend/src/index.css` |
| Name des Programms | `backend/app/registry.py` (PRODUCT_NAME) und `<title>` in `frontend/index.html` |
| Lieferschein: neues Feld in der Vorlage | Vorgabe in `registry.py` (DELIVERY_TEMPLATE), Eingabe in `pages/DeliveryTemplate.jsx`, Ausgabe in `components/DeliveryNoteDocument.jsx` |
| Lieferschein: Aussehen des Blatts | `components/DeliveryNoteDocument.jsx`, Druckregeln am Ende von `index.css` |
| Neue Auswertung | Berechnung in `routers/analysis.py`, Anzeige in `pages/Analysis.jsx` |
| Seite live aktualisieren | `useLive(load)` in der Seite – der Server meldet jede Änderung automatisch |
| Port, Sicherungsordner, Tastaturbefehl | `/etc/lagerverwaltung.env` (siehe `config.py`) |
| Passwortregeln, Sperrzeiten, Sitzungsdauer | `backend/app/config.py`, Abschnitt Sicherheit |

Nach Änderungen an der Oberfläche: im Ordner `frontend` einmal `npm install`, dann `npm run build`
(benötigt Node.js). Während der Entwicklung: `npm run dev`.

## Sicherheit

| Schutz | Wo |
|---|---|
| Passwörter: scrypt mit Salt, Stärke einstellbar, alte Hashes werden erneuert | `security.py` |
| Sitzung: zufälliges Token, nur als Hash gespeichert; Cookie HttpOnly, SameSite=Strict, bei HTTPS Secure | `security.py`, `routers/auth.py` |
| Abmeldung bei Leerlauf serverseitig erzwungen, Sitzung höchstens 30 Tage | `security.py`, `config.py` |
| Bremse gegen Passwort-Raten je Rechner und Benutzername | `routers/auth.py` (LoginLimiter) |
| Ersteinrichtung nur mit Einrichtungscode oder direkt am Server | `routers/auth.py` |
| Jede Route prüft das Recht am Server (`require(...)`); niemand vergibt mehr Rechte, als er hat | `routers/users.py`, `routers/roles.py` |
| Datenbankzugriffe nur über gebundene Parameter (keine SQL-Einschleusung) | SQLAlchemy, überall |
| Eingaben mit Längen- und Wertgrenzen, Anfragen höchstens 4 MB | Pydantic-Modelle, `main.py` |
| Anfragen fremder Webseiten werden abgewiesen (Herkunftsprüfung, auch WebSocket) | `main.py`, `live.py` |
| Sicherheits-Header (CSP, kein Einbetten, kein Typ-Raten, kein Zwischenspeichern von Daten) | `main.py` |
| Bilder: Typ am Inhalt geprüft, Größe begrenzt | `routers/articles.py` |
| Excel-Export ohne ausführbare Formeln | `routers/analysis.py` |
| Dienst läuft ohne Admin-Rechte und darf nur den Datenordner beschreiben | `deploy/install.sh` |

Die Regressionstests dazu stehen am Ende von `backend/tests/test_api.py`.

Grenzen: Ohne `deploy/https.sh` ist die Verbindung unverschlüsselt. Als
„Server selbst“ gilt eine Anfrage von `localhost`; steht später ein
Reverse-Proxy davor, müssen `keyboard.is_terminal` und die Ersteinrichtung
angepasst werden. Das Programm ist für das Firmennetz gedacht, nicht für das
offene Internet.

## Handy und Artikelbilder

Die Oberfläche passt sich schmalen Bildschirmen an (Menü oben links). Handys
müssen im selben Netz sein wie der Server (Firmen-WLAN) und rufen dieselbe
Adresse auf. Artikelbilder werden im Browser auf höchstens 800 Pixel verkleinert
und in der Datenbank gespeichert – sie sind damit in jeder Sicherung enthalten.

## Terminal und Tastatur

Als Terminal gilt der Browser auf dem Server selbst (Aufruf über `localhost`).
Meldet sich dort ein Benutzer mit dem Häkchen „Terminal-Benutzer“ an, stellt der
Server die Tastatur auf dessen Sprache um (`setxkbmap`), beim Abmelden zurück.
Die Rechner der Mitarbeiter sind davon nicht betroffen: Ein Webprogramm kann
die Tastatur eines fremden Rechners nicht umstellen, dort geschieht das wie
gewohnt über das Betriebssystem.
