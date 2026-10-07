# WEAS – Erstinstallation

Reihenfolge: erst unter Windows ausprobieren (Teil A), dann auf dem Server
einrichten (Teil B). Beides ist voneinander unabhängig; die Testdaten von
Windows wandern nicht automatisch auf den Server.

---

## Teil A – Ausprobieren unter Windows

1. **Python installieren** (einmalig): https://www.python.org/downloads/ ,
   Version 3.11 oder neuer. Im Installationsfenster **„Add python.exe to PATH“**
   ankreuzen.
2. **ZIP entpacken**, z. B. nach `C:\lagerverwaltung`.
3. **`start.bat` doppelklicken.** Beim ersten Mal werden die benötigten Pakete
   geladen (Internet nötig, etwa eine Minute). Danach öffnet sich der Browser
   mit `http://localhost:8000`.
   Meldet Windows „Der Computer wurde geschützt“: *Weitere Informationen* →
   *Trotzdem ausführen*.
4. **Administrator-Konto anlegen** und ausprobieren.
5. **Beenden:** das schwarze Fenster schließen.

Gut zu wissen:

- Im Testbetrieb ist das Programm **nur auf diesem Rechner** erreichbar.
- Die Testdaten liegen in `backend\data`. Ordner löschen = wieder ganz von vorn.
- Handy-Ansicht testen: im Browser F12 drücken und das Geräte-Symbol wählen.
- Die Tastaturumschaltung für Terminal-Benutzer und der Autostart gibt es nur
  auf dem Server (Teil B).

---

## Teil B – Einrichtung auf dem Server (Ubuntu Server)

Voraussetzungen: Ubuntu Server 22.04 oder 24.04, Internetzugang während der
Installation, ein Benutzer mit `sudo`. Der Server sollte im Router eine
**feste Adresse** bekommen, sonst ändert sich die Adresse für die Mitarbeiter.

### 1. Paket auf den Server bringen

Von Windows aus (PowerShell, im Ordner mit dem ZIP):

    scp lagerverwaltung.zip BENUTZER@SERVER-ADRESSE:~

Oder per USB-Stick.

### 2. Installieren

Am Server (direkt oder per `ssh BENUTZER@SERVER-ADRESSE`):

    sudo apt install -y unzip
    unzip lagerverwaltung.zip
    cd lagerverwaltung
    sudo bash deploy/install.sh

Das Skript richtet das Programm als Dienst ein, der bei jedem Hochfahren
startet, und zeigt am Ende die **Adresse** und den **Einrichtungscode**.

### 3. Administrator-Konto anlegen

An einem Mitarbeiter-Rechner die angezeigte Adresse öffnen
(`http://SERVER-ADRESSE:8000`), Einrichtungscode eingeben, Konto anlegen.
Der Code verhindert, dass sich jemand anderes im Netz zuerst zum Administrator
macht; er gilt nur dieses eine Mal. Erneut anzeigen:

    sudo cat /var/lib/lagerverwaltung/einrichtungscode.txt

### 4. Danach im Programm

- **Einstellungen → Allgemein:** Firmenname eintragen.
- **Einstellungen → Benutzer:** Konten für die Mitarbeiter anlegen, Sprache
  wählen, bei Bedarf „Terminal-Benutzer“ ankreuzen.
- **Einstellungen → Kategorien** und **Artikel** anlegen.

### 5. Empfohlen

| Was | Befehl | Wozu |
|---|---|---|
| Verschlüsselung | `sudo bash deploy/https.sh` | Passwörter laufen sonst lesbar durchs (W)LAN. Adresse danach `https://…`; jeder Browser zeigt einmalig eine Zertifikatswarnung. |
| Terminal am Server | `sudo bash deploy/kiosk.sh`, dann `sudo reboot` | Bildschirm des Servers zeigt WEAS im Vollbild. Nach `https.sh` ausführen. |
| Sicherung auf anderes Gerät | in `/etc/lagerverwaltung.env` die Zeile `LAGER_BACKUP_DIR=/pfad` eintragen, dann `sudo bash deploy/install.sh` | Das RAID schützt nicht vor Löschen, Diebstahl oder Brand. |

### Testdaten von Windows übernehmen (nur wenn gewünscht)

    sudo systemctl stop lagerverwaltung
    # lager.db aus backend\data vom Windows-Rechner nach /var/lib/lagerverwaltung/ kopieren
    sudo chown lager:lager /var/lib/lagerverwaltung/lager.db
    sudo systemctl start lagerverwaltung

---

## Später: Aktualisieren

Neues ZIP auf den Server kopieren, entpacken und erneut ausführen:

    sudo bash deploy/install.sh

Daten und Einstellungen bleiben erhalten; neue Datenfelder ergänzt das
Programm beim Start von selbst.

## Nützliche Befehle am Server

    sudo systemctl status lagerverwaltung      # läuft der Dienst?
    sudo systemctl restart lagerverwaltung     # neu starten
    sudo journalctl -u lagerverwaltung -n 50   # letzte Meldungen

## Wichtig für die Sicherheit

- Den Server **nicht aus dem Internet erreichbar machen** (keine
  Portfreigabe im Router). Das Programm ist für das Firmennetz gedacht.
- Für das Administrator-Konto ein langes Passwort wählen.
- Wer den Server anfassen kann, kommt an die Daten. Er gehört in einen
  abschließbaren Raum.
