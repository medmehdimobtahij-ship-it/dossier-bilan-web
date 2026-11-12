"""ComptaZap côté site : le connecteur du poste et les déclarations de TVA qu'il envoie.

Le site (en ligne) ne peut pas lire le PC où tourne ComptaZap. Le connecteur (dossier connecteur/, installé sur ce PC)
lit les déclarations de TVA téléchargées par ComptaZap depuis impots.gouv, contrôle chacune, et les envoie ici avec
leur PDF. Il s'identifie par un code de liaison créé dans Paramètres (seule son empreinte est gardée).

Données : data/connecteur.json (réglages et état), table comptazap_tva de bilan.sqlite, PDF dans data/pdf/.
"""
import hashlib
import json
import os
import secrets
from datetime import date

import stockage
from moteur.outils import ajouter_mois, lire_date

FICHIER = os.path.join(stockage.DATA, "connecteur.json")
PDF = os.path.join(stockage.DATA, "pdf")


# ---------------------------------------------------------------------------------------------------------------
# Connecteur : code de liaison, état, demandes
# ---------------------------------------------------------------------------------------------------------------
def lire():
    try:
        with open(FICHIER, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def ecrire(cfg):
    os.makedirs(stockage.DATA, exist_ok=True)
    tmp = FICHIER + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def empreinte(code):
    return hashlib.sha256((code or "").strip().encode("utf-8")).hexdigest()


def nouveau_code():
    """Un nouveau code de liaison (montré une seule fois) ; l'ancien cesse de marcher."""
    code = "DBL-" + secrets.token_urlsafe(24)
    cfg = lire()
    cfg.update(code=empreinte(code), cree_le=stockage.maintenant(), dernier_contact="", erreur="")
    ecrire(cfg)
    return code


def verifier_code(code):
    attendu = lire().get("code")
    return bool(attendu) and secrets.compare_digest(attendu, empreinte(code))


def delier():
    cfg = lire()
    for k in ("code", "poste", "dernier_contact"):
        cfg.pop(k, None)
    ecrire(cfg)


def demander_synchro(qui):
    cfg = lire()
    cfg["demande"] = {"le": stockage.maintenant(), "par": qui}
    ecrire(cfg)


def contact(poste="", **maj):
    cfg = lire()
    cfg["dernier_contact"] = stockage.maintenant()
    if poste:
        cfg["poste"] = poste
    cfg.update(maj)
    ecrire(cfg)
    return cfg


def etat():
    cfg = lire()
    with stockage._connexion() as cx:
        n, maj = cx.execute("SELECT COUNT(*), MAX(recu_le) FROM comptazap_tva").fetchone()
        ko = cx.execute("SELECT COUNT(*) FROM comptazap_tva WHERE controle_ok = 0").fetchone()[0]
    return {"lie": bool(cfg.get("code")), "cree_le": cfg.get("cree_le", ""), "poste": cfg.get("poste", ""),
            "dernier_contact": cfg.get("dernier_contact", ""), "derniere_synchro": cfg.get("derniere_synchro", ""),
            "maj_comptazap": cfg.get("maj_comptazap", ""), "erreur": cfg.get("erreur", ""),
            "demande_en_attente": bool(cfg.get("demande")), "declarations": n or 0, "non_controlees": ko or 0}


# ---------------------------------------------------------------------------------------------------------------
# Déclarations reçues
# ---------------------------------------------------------------------------------------------------------------
def initialiser():
    os.makedirs(PDF, exist_ok=True)
    with stockage.VERROU, stockage._connexion() as cx:
        cx.executescript("""
        CREATE TABLE IF NOT EXISTS comptazap_tva (
            siren TEXT NOT NULL, client TEXT, formulaire TEXT, periode_debut TEXT NOT NULL, periode_fin TEXT NOT NULL,
            type_depot TEXT, date_depot TEXT, montant REAL, is_credit INTEGER, controle_ok INTEGER, controle_msg TEXT,
            recap TEXT, pdf_sha TEXT, pdf_nom TEXT, recu_le TEXT,
            PRIMARY KEY (siren, periode_debut, periode_fin, type_depot, date_depot)
        );
        CREATE INDEX IF NOT EXISTS comptazap_tva_siren ON comptazap_tva(siren);
        """)


def recevoir(declarations, poste="", maj_comptazap=""):
    """Enregistre les déclarations envoyées par le connecteur ; renvoie les empreintes des PDF que le site n'a pas."""
    t = stockage.maintenant()
    manquants = set()
    with stockage.VERROU, stockage._connexion() as cx:
        for d in declarations:
            siren = "".join(ch for ch in str(d.get("siren") or "") if ch.isdigit())
            debut, fin = lire_date(d.get("periode_debut")), lire_date(d.get("periode_fin"))
            if len(siren) != 9 or not debut or not fin:
                continue
            sha = str(d.get("pdf_sha") or "")
            cx.execute("""INSERT OR REPLACE INTO comptazap_tva VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                       (siren, d.get("client") or "", d.get("formulaire") or "", debut.isoformat(), fin.isoformat(),
                        d.get("type_depot") or "", d.get("date_depot") or "", float(d.get("montant") or 0), int(bool(d.get("is_credit"))),
                        int(bool(d.get("controle_ok"))), d.get("controle_msg") or "", json.dumps(d.get("recap") or {}, ensure_ascii=False),
                        sha, d.get("pdf_nom") or "", t))
            if sha and len(sha) == 64 and not os.path.exists(os.path.join(PDF, sha + ".pdf")):
                manquants.add(sha)
    contact(poste, derniere_synchro=t, maj_comptazap=maj_comptazap, erreur="", demande=None)
    return sorted(manquants)


def enregistrer_pdf(sha, contenu):
    if hashlib.sha256(contenu).hexdigest() != sha:
        raise ValueError("empreinte du PDF incorrecte")
    if not contenu.startswith(b"%PDF"):
        raise ValueError("ce n'est pas un PDF")
    os.makedirs(PDF, exist_ok=True)
    with open(os.path.join(PDF, sha + ".pdf"), "wb") as f:
        f.write(contenu)


def chemin_pdf(sha):
    if len(sha) != 64 or not all(c in "0123456789abcdef" for c in sha):
        return None
    p = os.path.join(PDF, sha + ".pdf")
    return p if os.path.exists(p) else None


def _ordre_depot(d):
    """Pour une même période, la dernière déposée l'emporte (une rectificative remplace l'initiale)."""
    j = d["date_depot"] or ""
    # « JJ/MM/AAAA » ou ISO : on trie sur AAAA-MM-JJ
    if len(j) >= 10 and j[2] == "/":
        j = j[6:10] + "-" + j[3:5] + "-" + j[0:2] + j[10:]
    return j


def declarations_exercice(siren, debut, cloture):
    """Les déclarations du SIREN dont la période commence dans l'exercice, la dernière déposée par période."""
    siren = "".join(ch for ch in str(siren or "") if ch.isdigit())
    if len(siren) != 9:
        return []
    with stockage._connexion() as cx:
        rows = [dict(r) for r in cx.execute("SELECT * FROM comptazap_tva WHERE siren = ? AND periode_debut >= ? AND periode_debut <= ?",
                                            (siren, debut.isoformat(), cloture.isoformat()))]
    par_periode = {}
    for r in sorted(rows, key=_ordre_depot):
        r["recap"] = json.loads(r["recap"] or "{}")
        par_periode[(r["periode_debut"], r["periode_fin"])] = r
    toutes = sorted(rows, key=lambda r: (r["periode_debut"], _ordre_depot(r)))
    retenues = {id(r) for r in par_periode.values()}
    for r in toutes:
        r["retenue"] = id(r) in retenues
        if isinstance(r["recap"], str):
            r["recap"] = json.loads(r["recap"] or "{}")
    return toutes


def vers_recap(declarations):
    """Le récapitulatif du moteur ({AAAA-MM: {case: {base, taxe}}}) depuis les déclarations retenues et contrôlées.

    Une déclaration trimestrielle ou annuelle est rangée sur son premier mois ; les autres mois de la période sont
    marqués « couverts » (pas d'alerte « mois sans déclaration »)."""
    recap, ecartees = {}, []
    for d in declarations:
        if not d.get("retenue"):
            continue
        if not d["controle_ok"]:
            ecartees.append(d)
            continue
        debut, fin = date.fromisoformat(d["periode_debut"]), date.fromisoformat(d["periode_fin"])
        cle = debut.strftime("%Y-%m")
        recap[cle] = dict(d["recap"])
        m = ajouter_mois(date(debut.year, debut.month, 1), 1)
        while m <= fin:
            recap.setdefault(m.strftime("%Y-%m"), {"_couvert_par": cle})
            m = ajouter_mois(m, 1)
    return recap, ecartees
