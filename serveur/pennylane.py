"""Lecture des balances dans Pennylane (API publique, lecture seule : aucun appel n'écrit dans Pennylane).

Deux façons de se connecter, au choix dans Paramètres › Pennylane :
  - « cabinet » : un jeton de l'API cabinet donne la liste des dossiers du portefeuille et leurs balances ;
  - « entreprise » : un jeton par dossier (API entreprise v2), saisi à la création du dossier.

Les adresses de l'API sont regroupées dans CHEMINS. Elles suivent la documentation publique de Pennylane
(pennylane.readme.io : trial balance en v2, API cabinet sous /api/external/firm/v1) mais n'ont pas encore été essayées
avec un vrai jeton du cabinet : si Pennylane diffère, c'est le seul endroit à modifier (le bouton « Tester la connexion »
affiche la réponse brute). La pagination par curseur (cursor / limit) et l'ancienne (page / per_page) sont gérées.
Le jeton est conservé dans data/pennylane.json, sur le serveur seulement (jamais renvoyé à l'interface).
"""
import json
import os
import time

import requests

from stockage import DATA

FICHIER = os.path.join(DATA, "pennylane.json")
BASE = os.environ.get("PENNYLANE_BASE", "https://app.pennylane.com")
CHEMINS = {
    "cabinet_dossiers": "/api/external/firm/v1/companies",
    "cabinet_balance": "/api/external/firm/v1/companies/{company_id}/trial_balance",
    "cabinet_exercices": "/api/external/firm/v1/companies/{company_id}/fiscal_years",
    "entreprise_moi": "/api/external/v2/me",
    "entreprise_balance": "/api/external/v2/trial_balance",
    "entreprise_exercices": "/api/external/v2/fiscal_years",
}
DELAI = 30


class ErreurPennylane(Exception):
    pass


def lire_config():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ecrire_config(cfg):
    os.makedirs(DATA, exist_ok=True)
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def etat():
    """Ce que l'interface a le droit de savoir : le mode et si un jeton est enregistré (jamais le jeton)."""
    cfg = lire_config()
    jeton = os.environ.get("PENNYLANE_TOKEN") or cfg.get("jeton")
    return {"mode": cfg.get("mode", "cabinet"), "jeton_present": bool(jeton),
            "jeton_fin": ("…" + jeton[-4:]) if jeton else "", "teste_le": cfg.get("teste_le", ""), "test_ok": cfg.get("test_ok")}


def _jeton(jeton_dossier=None):
    j = jeton_dossier or os.environ.get("PENNYLANE_TOKEN") or lire_config().get("jeton")
    if not j:
        raise ErreurPennylane("Aucun jeton Pennylane : renseignez-le dans Paramètres › Pennylane.")
    return j


def _get(chemin, params=None, jeton=None):
    url = BASE + chemin
    for essai in range(4):
        try:
            r = requests.get(url, params=params or {}, timeout=DELAI,
                             headers={"Authorization": f"Bearer {_jeton(jeton)}", "Accept": "application/json"})
        except requests.RequestException as e:
            raise ErreurPennylane(f"Pennylane ne répond pas ({e.__class__.__name__}).") from e
        if r.status_code == 429 and essai < 3:  # limite de débit : on patiente et on réessaie
            time.sleep(float(r.headers.get("Retry-After", 2 + essai * 2)))
            continue
        if r.status_code == 401:
            raise ErreurPennylane("Jeton Pennylane refusé (401) : vérifiez-le ou régénérez-le dans Pennylane.")
        if r.status_code == 403:
            raise ErreurPennylane("Accès refusé par Pennylane (403) : le jeton n'a pas le droit de lire ce dossier.")
        if r.status_code == 404:
            raise ErreurPennylane(f"Adresse inconnue de Pennylane (404) : {chemin}. Voir CHEMINS dans pennylane.py.")
        if r.status_code >= 400:
            raise ErreurPennylane(f"Erreur Pennylane {r.status_code} : {r.text[:300]}")
        try:
            return r.json()
        except ValueError as e:
            raise ErreurPennylane("Réponse de Pennylane illisible.") from e
    raise ErreurPennylane("Pennylane limite les appels : réessayez dans une minute.")


def _pages(chemin, params=None, jeton=None, max_pages=100):
    """Toutes les pages d'une liste (Pennylane pagine par « page » ou par curseur selon les ressources)."""
    params = dict(params or {})
    taille = 1000 if "trial_balance" in chemin else 100
    params.setdefault("limit", taille)      # pagination par curseur (API 2026)
    params.setdefault("per_page", taille)   # ancienne pagination par pages, encore acceptée
    elements, page, curseur = [], 1, None
    for _ in range(max_pages):
        p = dict(params)
        if curseur:
            p["cursor"] = curseur
        else:
            p["page"] = page
        rep = _get(chemin, p, jeton)
        lot = rep.get("items") if isinstance(rep, dict) else rep
        if lot is None and isinstance(rep, dict):
            lot = rep.get("data") or rep.get("companies") or []
        elements.extend(lot or [])
        if isinstance(rep, dict) and rep.get("has_more") and rep.get("next_cursor"):
            curseur = rep["next_cursor"]
            continue
        total = rep.get("total_pages") if isinstance(rep, dict) else None
        if total and page < int(total):
            page += 1
            continue
        break
    return elements


def tester(jeton=None):
    cfg = lire_config()
    mode = cfg.get("mode", "cabinet")
    try:
        if mode == "cabinet":
            rep = _get(CHEMINS["cabinet_dossiers"], {"per_page": 1}, jeton)
        else:
            rep = _get(CHEMINS["entreprise_moi"], None, jeton)
        ok, message = True, "Connexion réussie."
    except ErreurPennylane as e:
        rep, ok, message = None, False, str(e)
    cfg.update(teste_le=time.strftime("%Y-%m-%d %H:%M"), test_ok=ok)
    ecrire_config(cfg)
    return {"ok": ok, "message": message, "apercu": json.dumps(rep, ensure_ascii=False)[:800] if rep else ""}


_CACHE_DOSSIERS = {"quand": 0.0, "liste": None}


def dossiers(recherche="", rafraichir=False):
    """Dossiers du portefeuille du cabinet : [{id, nom, siren}]. Liste gardée 10 minutes (des centaines de dossiers
    = plusieurs pages d'API : l'ouverture de « Nouveau dossier » reste instantanée)."""
    if rafraichir or _CACHE_DOSSIERS["liste"] is None or time.time() - _CACHE_DOSSIERS["quand"] > 600:
        _CACHE_DOSSIERS["liste"] = _pages(CHEMINS["cabinet_dossiers"])
        _CACHE_DOSSIERS["quand"] = time.time()
    out = []
    for c in _CACHE_DOSSIERS["liste"]:
        nom = c.get("name") or c.get("legal_name") or c.get("company_name") or ""
        if recherche and recherche.casefold() not in nom.casefold():
            continue
        out.append({"id": c.get("id"), "nom": nom, "siren": c.get("registration_number") or c.get("siren") or ""})
    return sorted(out, key=lambda x: x["nom"].casefold())


def exercices(company_id=None, jeton=None):
    """Exercices comptables : [{debut, fin}] du plus récent au plus ancien."""
    if company_id:
        brut = _pages(CHEMINS["cabinet_exercices"].format(company_id=company_id))
    else:
        brut = _pages(CHEMINS["entreprise_exercices"], jeton=jeton)
    ex = [{"debut": e.get("start") or e.get("start_date"), "fin": e.get("finish") or e.get("end") or e.get("end_date")} for e in brut]
    return sorted((e for e in ex if e["debut"] and e["fin"]), key=lambda e: e["fin"], reverse=True)


def _montant(v):
    try:
        return float(str(v).replace(",", ".")) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


def balance(debut, fin, company_id=None, jeton=None):
    """Balance générale (comptes généraux, sans les auxiliaires) sur la période : {compte: {libelle, solde}}.
    Solde = débits - crédits, comme dans l'Excel."""
    params = {"period_start": debut, "period_end": fin, "is_auxiliary": "false"}
    if company_id:
        lignes = _pages(CHEMINS["cabinet_balance"].format(company_id=company_id), params)
    else:
        lignes = _pages(CHEMINS["entreprise_balance"], params, jeton)
    out = {}
    for l in lignes:
        compte = str(l.get("number") or l.get("formatted_number") or l.get("account_number") or "").strip()
        if not compte:
            continue
        if "balance" in l and "debits" not in l:
            solde = _montant(l.get("balance"))
        else:
            solde = _montant(l.get("debits")) - _montant(l.get("credits"))
        o = out.setdefault(compte, {"libelle": l.get("label") or l.get("name") or "", "solde": 0.0})
        o["solde"] += solde
    return out


def balance_comparative(debut_n, fin_n, debut_n1, fin_n1, company_id=None, jeton=None):
    """Balance N et N-1 réunies, au format du moteur : [{compte, libelle, solde_n, solde_n1}]."""
    n = balance(debut_n, fin_n, company_id, jeton)
    n1 = balance(debut_n1, fin_n1, company_id, jeton) if debut_n1 and fin_n1 else {}
    lignes = []
    for compte in sorted(set(n) | set(n1)):
        lignes.append({"compte": compte, "libelle": (n.get(compte) or n1.get(compte))["libelle"],
                       "solde_n": round(n.get(compte, {}).get("solde", 0.0), 2), "solde_n1": round(n1.get(compte, {}).get("solde", 0.0), 2)})
    return lignes
