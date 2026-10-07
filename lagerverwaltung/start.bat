@echo off
rem WEAS (Warenerfassungs- und Analysesystem) zum Ausprobieren starten (Windows).
rem Nur auf diesem Rechner erreichbar. Daten liegen in backend\data.
setlocal
cd /d "%~dp0backend"

rem Python suchen: zuerst der Python-Launcher "py", dann "python"
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo.
  echo Python wurde nicht gefunden.
  echo Bitte Python 3.11 oder neuer von https://www.python.org/downloads/ installieren
  echo und dabei "Add python.exe to PATH" ankreuzen. Danach diese Datei erneut starten.
  echo.
  pause
  exit /b 1
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo.
  echo Die installierte Python-Version ist zu alt. Benoetigt wird 3.11 oder neuer.
  %PY% --version
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Erster Start: Umgebung wird eingerichtet, das dauert einen Moment ...
  %PY% -m venv .venv
  if errorlevel 1 goto :fehler
)
".venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :fehler

if not defined LAGER_HOST set "LAGER_HOST=127.0.0.1"
if not defined LAGER_PORT set "LAGER_PORT=8000"
echo.
echo WEAS laeuft unter http://localhost:%LAGER_PORT%
echo Dieses Fenster offen lassen. Beenden: Fenster schliessen oder Strg+C.
echo.
rem Browser oeffnen, sobald der Server bereit ist
start "" /b cmd /c "ping -n 4 127.0.0.1 >nul & start http://localhost:%LAGER_PORT%"
".venv\Scripts\python.exe" run.py
echo.
echo WEAS wurde beendet.
pause
exit /b 0

:fehler
echo.
echo Die Einrichtung ist fehlgeschlagen. Besteht eine Internetverbindung?
echo Die Meldungen oben bitte aufbewahren.
echo.
pause
exit /b 1
