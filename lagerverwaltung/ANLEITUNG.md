# WEAS – Kurzanleitung

## Anmelden

- Am Mitarbeiter-Rechner den Browser öffnen: `http://ADRESSE-DES-SERVERS:8000`
  (mit eingerichteter Verschlüsselung `https://…`)
  (die Adresse zeigt das Installationsskript am Ende an).
- Am Terminal des Servers erscheint die Anmeldung von selbst.
- Am Handy (im Firmen-WLAN) dieselbe Adresse im Browser öffnen. Das Menü
  steckt dort hinter dem Symbol oben links.
- Unten auf der Anmeldeseite lässt sich die Sprache wählen. Nach der Anmeldung
  gilt die Sprache des Benutzers.
- Nach 5 Minuten ohne Eingabe wird automatisch abgemeldet. Oben rechts läuft
  die Restzeit mit.

## Tägliche Arbeit

| Aufgabe | Wo |
|---|---|
| Bestand nachsehen, Artikel suchen | **Artikel** |
| Ware entnehmen | **Warenbewegungen** → Warenausgang → Artikel, Menge, Projekt |
| Ware oder Werkzeug zurückbringen | **Warenbewegungen** → Rückgabe |
| Lieferung einbuchen | **Warenbewegungen** → Wareneingang |
| Bestand nach Zählung berichtigen | **Warenbewegungen** → Korrektur (gezählten Bestand eingeben) |
| Bild zum Artikel | **Artikel** → Stift → „Bild auswählen“, am Handy auch „Foto aufnehmen“ |
| Lieferschein des Lieferanten ablegen | **Warenbewegungen** → Wareneingang → Lieferschein: „Neuer Lieferschein“ → Lieferant, Nummer, Foto oder PDF anhängen |
| Eigenen Lieferschein ausstellen | **Warenbewegungen** → Warenausgang → Lieferschein: „Neuer Lieferschein“ → buchen. Weitere Artikel landen auf demselben Schein, solange er ausgewählt bleibt. Dann „Lieferschein öffnen“ → **Drucken / PDF** |
| Lieferscheine nachschlagen | **Lieferscheine** (Suche nach Nummer, Lieferant, Empfänger, Projekt) |
| Was wurde auf eine Baustelle gebucht? | **Projekte** → Projekt anklicken |
| Was muss nachbestellt werden? | **Übersicht** → Nachbestellen |
| Auswertungen, Export für Excel | **Analyse** |
| Eine fehlende Funktion vorschlagen | **Wünsche** → Text schreiben → absenden |

Buchungen lassen sich nicht löschen. Ein Fehler wird mit einer Gegenbuchung
(Rückgabe oder Korrektur) berichtigt – so bleibt alles nachvollziehbar.

## Verwaltung (Einstellungen)

- **Kategorien:** Warengruppen. „Material“ zählt zu den Projektkosten,
  „Werkzeug“ wird nur ausgeliehen.
- **Benutzer:** Konten anlegen, Rolle und Sprache zuweisen, sperren.
  „Terminal-Benutzer“ ankreuzen, wenn jemand am Bildschirm des Servers arbeitet:
  Dort stellt sich die Tastatur dann auf seine Sprache um. Bei Russisch und
  Ukrainisch wechselt **Alt + Umschalt** zwischen kyrillisch und lateinisch.
- **Rollen & Rechte:** Legt fest, wer was darf. Das Recht „Angemeldet bleiben“
  schaltet die automatische Abmeldung für eine Rolle ab.
- **Lieferscheine → Vorlage:** Logo, Firmenanschrift, Überschrift, Nummernkreis,
  Texte über und unter den Positionen sowie Preise, Projekt und
  Unterschriftsfelder ein- oder ausblenden. Rechts steht sofort die Vorschau.
  Nötig ist das Recht „Lieferscheine löschen und Vorlage bearbeiten“.
- **Wunschliste:** Alle eingereichten Wünsche mit Absender. Status setzen
  (neu, geplant, erledigt, abgelehnt) oder löschen. Sichtbar nur mit dem Recht
  „Alle Funktionswünsche ansehen und bearbeiten“ – in der Vorbelegung hat das
  nur der Administrator. Jeder Benutzer sieht unter **Wünsche** nur seine eigenen.
- **Allgemein:** Firmenname, Abmeldezeit, Aufbewahrung der Sicherungen,
  Scanner-Tab ein/aus, Datensicherung von Hand.
- **Mein Konto:** eigene Sprache und eigenes Passwort.

Artikel und Projekte mit Buchungen lassen sich nicht löschen. Stattdessen den
Artikel deaktivieren bzw. das Projekt abschließen.

## Datensicherung

- Die Datenbank wird jeden Tag automatisch gesichert; alte Sicherungen werden
  nach der eingestellten Zahl von Tagen gelöscht.
- Das RAID schützt vor dem Ausfall einer Festplatte. Es schützt nicht vor
  versehentlichem Löschen, Diebstahl oder Brand. Deshalb die Sicherungen
  möglichst auf ein anderes Gerät legen: in `/etc/lagerverwaltung.env` die Zeile
  `LAGER_BACKUP_DIR=...` eintragen und den Dienst neu starten.
- Wiederherstellen: Dienst stoppen, die gewünschte Sicherungsdatei als
  `lager.db` in den Datenordner kopieren, Dienst starten.

      sudo systemctl stop lagerverwaltung
      sudo cp /var/lib/lagerverwaltung/backups/lager-JJJJ-MM-TT.db /var/lib/lagerverwaltung/lager.db
      sudo rm -f /var/lib/lagerverwaltung/lager.db-wal /var/lib/lagerverwaltung/lager.db-shm
      sudo chown lager:lager /var/lib/lagerverwaltung/lager.db
      sudo systemctl start lagerverwaltung

## Wenn etwas nicht geht

| Problem | Lösung |
|---|---|
| Seite nicht erreichbar | Am Server: `sudo systemctl status lagerverwaltung`, bei Bedarf `sudo systemctl restart lagerverwaltung` |
| Fehlermeldungen ansehen | `sudo journalctl -u lagerverwaltung -n 50` |
| Passwort vergessen | Ein Administrator vergibt unter **Benutzer** ein neues |
| „Zu viele Fehlversuche“ | Eine Minute warten, dann erneut anmelden |
| Tastatur am Terminal falsch | Abmelden – die Anmeldeseite stellt auf die Standardsprache zurück |
