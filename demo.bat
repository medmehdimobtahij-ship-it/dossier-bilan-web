@echo off
rem Dossier Bilan : demo hors ligne (dossiers fictifs, aucun compte externe).
title Dossier Bilan - demo
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creation de l'environnement Python ^(.venv^)...
  python -m venv .venv || ( echo Python 3.10+ est requis : https://www.python.org & pause & exit /b 1 )
)
.venv\Scripts\python.exe -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 ( echo Echec de l'installation des dependances. & pause & exit /b 1 )
set BILAN_DEMO=1
start "" http://localhost:8095
.venv\Scripts\python.exe serveur\lancer.py
pause
