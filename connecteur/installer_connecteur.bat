@echo off
title Dossier Bilan - installation du connecteur ComptaZap
cd /d "%~dp0"
echo.
echo   Connecteur ComptaZap pour Dossier Bilan
echo   ---------------------------------------
echo   A installer sur le PC ou tourne ComptaZap (inutile pour la demo).
echo.
python -m pip install --quiet --user "pymupdf>=1.24"
if errorlevel 1 ( echo   Echec de l'installation de PyMuPDF. & pause & exit /b 1 )
echo.
set /p ADRESSE=  Adresse du site (ex. https://bilan.example.com) :
set /p CODE=  Code de liaison (Parametres du site, Connecteur du poste) :
python connecteur.py --lier "%ADRESSE%" "%CODE%"
python connecteur.py --une-fois
if errorlevel 1 ( echo. & echo   La premiere synchro a echoue : voir donnees\journal.log & pause & exit /b 1 )
python connecteur.py --demarrage oui
start "" pythonw connecteur.py
echo.
echo   Installe. Le connecteur tourne en fond et se relancera au demarrage de Windows.
pause
