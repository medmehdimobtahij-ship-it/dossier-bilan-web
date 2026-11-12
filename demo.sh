#!/usr/bin/env sh
# Dossier Bilan : démo hors ligne (dossiers fictifs, aucun compte externe).
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Création de l'environnement Python (.venv)..."
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
echo "Ouvrez http://localhost:8095"
BILAN_DEMO=1 exec .venv/bin/python serveur/lancer.py
