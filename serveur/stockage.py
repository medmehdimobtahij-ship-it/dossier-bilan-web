"""Stockage des dossiers bilan : une base SQLite (data/bilan.sqlite), un enregistrement par dossier et par exercice.

Chaque modification incrémente la version du dossier : si deux personnes modifient le même dossier, la seconde écriture
fondée sur une version périmée est refusée (pas d'écrasement silencieux). Un journal garde qui a fait quoi.
"""
import json
import os
import sqlite3
import threading
from datetime import datetime

_RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# En démo (BILAN_DEMO=1), une base à part (data-demo/) : la démo ne touche jamais aux vraies données.
DATA = os.environ.get("BILAN_DATA") or os.path.join(_RACINE, "data-demo" if os.environ.get("BILAN_DEMO") == "1" else "data")
FICHIER = os.path.join(DATA, "bilan.sqlite")
VERROU = threading.RLock()
CHAMPS_JSON = ("infos", "balance", "saisies", "recap_tva", "journal_paie", "parametres")


class Conflit(Exception):
    """Le dossier a été modifié par quelqu'un d'autre entre-temps."""


def _connexion():
    os.makedirs(DATA, exist_ok=True)
    cx = sqlite3.connect(FICHIER, timeout=10)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA foreign_keys=ON")
    return cx


def initialiser():
    with VERROU, _connexion() as cx:
        cx.executescript("""
        CREATE TABLE IF NOT EXISTS dossiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL, siren TEXT DEFAULT '', pennylane_id TEXT DEFAULT '',
            debut_exercice TEXT, cloture TEXT,
            infos TEXT DEFAULT '{}', balance TEXT DEFAULT '[]', saisies TEXT DEFAULT '{}', recap_tva TEXT DEFAULT '{}',
            journal_paie TEXT DEFAULT '[]', parametres TEXT DEFAULT '{}',
            source_balance TEXT DEFAULT '', balance_importee_le TEXT DEFAULT '',
            cree_le TEXT, cree_par TEXT, maj_le TEXT, maj_par TEXT, version INTEGER DEFAULT 1, archive INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT, dossier_id INTEGER, quand TEXT, qui TEXT, action TEXT
        );
        CREATE INDEX IF NOT EXISTS journal_dossier ON journal(dossier_id);
        """)


def _ligne(row):
    if row is None:
        return None
    d = dict(row)
    for k in CHAMPS_JSON:
        try:
            d[k] = json.loads(d.get(k) or ("[]" if k in ("balance", "journal_paie") else "{}"))
        except ValueError:
            d[k] = [] if k in ("balance", "journal_paie") else {}
    return d


def maintenant():
    return datetime.now().isoformat(timespec="seconds")


def lister(archives=False):
    with _connexion() as cx:
        rows = cx.execute("SELECT id, nom, siren, pennylane_id, debut_exercice, cloture, source_balance, balance_importee_le, "
                          "maj_le, maj_par, version, archive, length(balance) AS taille FROM dossiers "
                          + ("" if archives else "WHERE archive = 0 ") + "ORDER BY nom COLLATE NOCASE, cloture DESC").fetchall()
    return [dict(r) for r in rows]


def lire(dossier_id):
    with _connexion() as cx:
        return _ligne(cx.execute("SELECT * FROM dossiers WHERE id = ?", (dossier_id,)).fetchone())


def creer(nom, debut, cloture, qui, siren="", pennylane_id="", infos=None, saisies=None, parametres=None):
    t = maintenant()
    with VERROU, _connexion() as cx:
        cur = cx.execute(
            "INSERT INTO dossiers (nom, siren, pennylane_id, debut_exercice, cloture, infos, saisies, parametres, cree_le, cree_par, maj_le, maj_par) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nom, siren, str(pennylane_id or ""), debut, cloture, json.dumps(infos or {}, ensure_ascii=False),
             json.dumps(saisies or {}, ensure_ascii=False), json.dumps(parametres or {}, ensure_ascii=False), t, qui, t, qui))
        cx.execute("INSERT INTO journal (dossier_id, quand, qui, action) VALUES (?, ?, ?, ?)", (cur.lastrowid, t, qui, "Création du dossier"))
        return cur.lastrowid


def modifier(dossier_id, changements, qui, version=None, action=""):
    """Écrit les champs donnés. version : celle sur laquelle l'interface s'appuie ; périmée -> Conflit."""
    with VERROU, _connexion() as cx:
        row = cx.execute("SELECT version FROM dossiers WHERE id = ?", (dossier_id,)).fetchone()
        if row is None:
            raise KeyError(dossier_id)
        if version is not None and int(version) != row["version"]:
            raise Conflit()
        champs, valeurs = [], []
        for k, v in changements.items():
            champs.append(f"{k} = ?")
            valeurs.append(json.dumps(v, ensure_ascii=False) if k in CHAMPS_JSON else v)
        t = maintenant()
        champs += ["maj_le = ?", "maj_par = ?", "version = version + 1"]
        valeurs += [t, qui, dossier_id]
        cx.execute(f"UPDATE dossiers SET {', '.join(champs)} WHERE id = ?", valeurs)
        if action:
            cx.execute("INSERT INTO journal (dossier_id, quand, qui, action) VALUES (?, ?, ?, ?)", (dossier_id, t, qui, action))
        return row["version"] + 1


def supprimer(dossier_id, qui):
    with VERROU, _connexion() as cx:
        cx.execute("DELETE FROM dossiers WHERE id = ?", (dossier_id,))
        cx.execute("INSERT INTO journal (dossier_id, quand, qui, action) VALUES (?, ?, ?, ?)", (dossier_id, maintenant(), qui, "Suppression"))


def historique(dossier_id, limite=200):
    with _connexion() as cx:
        return [dict(r) for r in cx.execute("SELECT quand, qui, action FROM journal WHERE dossier_id = ? ORDER BY id DESC LIMIT ?",
                                            (dossier_id, limite)).fetchall()]


LISTES = {"associes"}  # les seules clés dont le contenu est une liste indicée (« associes.2.nom »)


def poser(racine, chemin, valeur):
    """Écrit valeur à l'emplacement « a.b.c » d'un dictionnaire imbriqué (créé au besoin). Un numéro de compte
    (« revision.512000.statut ») reste une clé : seules les clés de LISTES contiennent des listes."""
    cles = chemin.split(".")
    o = racine
    for i, k in enumerate(cles[:-1]):
        if isinstance(o, list):
            k = int(k)
            while len(o) <= k:
                o.append({})
            if not isinstance(o[k], (dict, list)):
                o[k] = {}
            o = o[k]
        else:
            if k not in o or not isinstance(o[k], (dict, list)):
                o[k] = [] if k in LISTES else {}
            o = o[k]
    der = cles[-1]
    if isinstance(o, list):
        der = int(der)
        while len(o) <= der:
            o.append(None)
    o[der] = valeur
    return racine
