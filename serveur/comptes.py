"""Comptes de connexion du dossier bilan : data/comptes.json, mots de passe hachés (scrypt), jamais en clair.

Au premier lancement, les comptes de COMPTES_INITIAUX sont créés avec un mot de passe provisoire affiché UNE fois dans
la fenêtre du serveur ; chacun le change ensuite dans Paramètres › Mon compte. `python gerer_comptes.py` réinitialise
un mot de passe. Les comptes initiaux se règlent par la variable BILAN_COMPTES (« id:Nom complet,id2:Nom 2 »).

Mode démo (BILAN_DEMO=1) : un seul compte « demo », mot de passe « demo », affiché sur l'écran de connexion.
"""
import json
import os
import secrets

from werkzeug.security import check_password_hash, generate_password_hash

from stockage import DATA

FICHIER = os.path.join(DATA, "comptes.json")
DEMO = os.environ.get("BILAN_DEMO") == "1"


def _comptes_initiaux():
    if DEMO:
        return {"demo": "Utilisateur démo"}
    brut = os.environ.get("BILAN_COMPTES", "").strip()
    if not brut:
        return {"admin": "Administrateur"}
    out = {}
    for morceau in brut.split(","):
        ident, _, nom = morceau.partition(":")
        if ident.strip():
            out[ident.strip().lower()] = nom.strip() or ident.strip()
    return out


COMPTES_INITIAUX = _comptes_initiaux()
LONGUEUR_MINI = 10


def lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ecrire(comptes):
    os.makedirs(DATA, exist_ok=True)
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(comptes, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def provisoire():
    return "-".join(secrets.token_urlsafe(4) for _ in range(3))  # ex. « k3Pq-Zx9a-Lm2w »


def initialiser():
    """Crée les comptes manquants. Retourne {identifiant: mot de passe provisoire} des comptes créés."""
    comptes, crees = lire(), {}
    for identifiant, nom in COMPTES_INITIAUX.items():
        if identifiant not in comptes:
            mdp = "demo" if DEMO else provisoire()
            comptes[identifiant] = {"nom": nom, "hash": generate_password_hash(mdp)}
            crees[identifiant] = mdp
    if crees:
        ecrire(comptes)
    return crees


def verifier(identifiant, mot_de_passe):
    """Le compte si le mot de passe est bon, sinon None."""
    c = lire().get((identifiant or "").strip().lower())
    if c and mot_de_passe and check_password_hash(c["hash"], mot_de_passe):
        return {"identifiant": identifiant.strip().lower(), "nom": c["nom"]}
    return None


def changer(identifiant, nouveau):
    if len(nouveau or "") < LONGUEUR_MINI:
        raise ValueError(f"Au moins {LONGUEUR_MINI} caractères.")
    comptes = lire()
    comptes[identifiant]["hash"] = generate_password_hash(nouveau)
    ecrire(comptes)
