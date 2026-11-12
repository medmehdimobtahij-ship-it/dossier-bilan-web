"""Connecteur du poste pour Dossier Bilan en ligne : le pont entre le PC où tourne ComptaZap et le site.

Un serveur web ne peut pas lire le disque d'un PC. Ce petit programme tourne en arrière-plan sur le PC de ComptaZap
(lancé au démarrage de Windows) et, toutes les 30 minutes ou dès que quelqu'un clique « Synchroniser » sur le site :
- copie la base fiscale de ComptaZap (jamais modifiée, jamais ouverte en écriture) ;
- lit les déclarations de TVA (CA3, CA12) des trois dernières années, contrôle chacune (montant lu = montant ComptaZap) ;
- envoie au site le détail des cases, puis les PDF que le site n'a pas encore.

Réglages et journal dans le dossier « donnees » à côté de ce fichier.
    python connecteur.py --lier <adresse du site> <code>   enregistre l'adresse et le code de liaison (Paramètres du site)
    python connecteur.py --une-fois                         une synchro tout de suite, puis s'arrête
    python connecteur.py --demarrage oui|non                lancement automatique au démarrage de Windows
    pythonw connecteur.py                                   en continu, sans fenêtre
"""
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime

sys.dont_write_bytecode = True
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

import lecture_tva  # noqa: E402

DONNEES = os.path.join(ICI, "donnees")
REGLAGES = os.path.join(DONNEES, "reglages.json")
CACHE = os.path.join(DONNEES, "lectures.json")      # PDF déjà lus (par empreinte) : on ne relit pas 1 000 PDF à chaque passage
JOURNAL = os.path.join(DONNEES, "journal.log")
PAUSE = 60                                          # une demande « Synchroniser » est vue en une minute au plus
RACCOURCI = "Dossier Bilan - connecteur.lnk"
FORMULAIRES = ("3310CA3", "3517SCA12")


def noter(message):
    """Journal du connecteur (300 dernières lignes)."""
    try:
        os.makedirs(DONNEES, exist_ok=True)
        lignes = open(JOURNAL, encoding="utf-8").read().splitlines()[-300:] if os.path.exists(JOURNAL) else []
        lignes.append(f"{datetime.now():%d/%m/%Y %H:%M:%S}  {message}")
        open(JOURNAL, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
    except OSError:
        pass


def lire_json(chemin, defaut):
    try:
        with open(chemin, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return defaut


def ecrire_json(chemin, donnees):
    os.makedirs(DONNEES, exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    os.replace(tmp, chemin)


def lier(adresse, code):
    r = lire_json(REGLAGES, {})
    r.update(adresse=adresse.rstrip("/"), code=code.strip())
    ecrire_json(REGLAGES, r)


class ErreurSite(Exception):
    pass


def appel(methode, route, corps=None, binaire=None, delai=120):
    """Appel à l'API du site, identifié par le code de liaison."""
    r = lire_json(REGLAGES, {})
    if not r.get("adresse") or not r.get("code"):
        raise ErreurSite("connecteur non lié : lancez « connecteur.py --lier <adresse> <code> »")
    entetes = {"Authorization": f"Bearer {r['code']}", "Accept": "application/json", "User-Agent": "DossierBilan-Connecteur/1.0"}
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps, ensure_ascii=False).encode("utf-8")
        entetes["Content-Type"] = "application/json"
    elif binaire is not None:
        donnees = binaire
        entetes["Content-Type"] = "application/octet-stream"
    url = r["adresse"] + "/api/poste/" + route
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=donnees, method=methode, headers=entetes), timeout=delai) as rep:
            return json.loads(rep.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read() or b"{}").get("erreur", "")
        except ValueError:
            detail = ""
        raise ErreurSite(f"le site a refusé ({e.code}) {detail}".strip())
    except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
        raise ErreurSite(f"site injoignable ({getattr(e, 'reason', e)})")


# --- ComptaZap -------------------------------------------------------------------------------------------------------

def dossier_comptazap():
    """Dossier de données de ComptaZap (réglage « comptazap » sinon %APPDATA%\\comptazap)."""
    choisi = lire_json(REGLAGES, {}).get("comptazap")
    for d in filter(None, [choisi, os.path.join(os.environ.get("APPDATA", ""), "comptazap")]):
        if os.path.isfile(os.path.join(d, "data", "fiscal.db")):
            return d
    raise FileNotFoundError("base de ComptaZap introuvable (%APPDATA%\\comptazap\\data\\fiscal.db)")


def copier_base():
    """Copie fiscal.db et son journal dans %TEMP% : ComptaZap tourne, on ne lit jamais l'original."""
    source = os.path.join(dossier_comptazap(), "data", "fiscal.db")
    cible_dir = os.path.join(tempfile.gettempdir(), "DossierBilan", "comptazap")
    os.makedirs(cible_dir, exist_ok=True)
    cible = os.path.join(cible_dir, "fiscal.db")
    for suffixe in ("", "-wal", "-shm"):
        if os.path.exists(source + suffixe):
            shutil.copyfile(source + suffixe, cible + suffixe)
        elif os.path.exists(cible + suffixe):
            os.remove(cible + suffixe)
    return cible


def lire_declarations(annees):
    """Déclarations CA3 / CA12 des années demandées, lues et contrôlées. Renvoie (déclarations, {empreinte: chemin})."""
    base = copier_base()
    con = sqlite3.connect(base)
    con.row_factory = sqlite3.Row
    try:
        marques = ",".join("?" * len(annees))
        rows = [dict(r) for r in con.execute(
            f"SELECT siren, client_name, annee, periode_debut, periode_fin, type_depot, date_depot, montant, is_credit, numero_formulaire, "
            f"pdf_path FROM tva_declarations WHERE numero_formulaire IN ('3310CA3', '3517SCA12') AND annee IN ({marques})",
            [int(a) for a in annees])]
        maj = con.execute("SELECT MAX(synced_at) FROM tva_declarations").fetchone()[0] or ""
    finally:
        con.close()
    cache = lire_json(CACHE, {})
    pdfs, out, nouvelles = {}, [], 0
    for r in rows:
        chemin = r.pop("pdf_path") or ""
        d = {"siren": r["siren"], "client": r["client_name"], "formulaire": "CA12" if r["numero_formulaire"] == "3517SCA12" else "CA3",
             "periode_debut": r["periode_debut"], "periode_fin": r["periode_fin"], "type_depot": r["type_depot"], "date_depot": r["date_depot"],
             "montant": r["montant"], "is_credit": bool(r["is_credit"]), "recap": {}, "controle_ok": False, "controle_msg": "", "pdf_sha": "", "pdf_nom": ""}
        if not chemin or not os.path.isfile(chemin):
            d["controle_msg"] = "PDF absent du poste (ComptaZap ne l'a pas encore téléchargé)"
            out.append(d)
            continue
        with open(chemin, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        d["pdf_sha"], d["pdf_nom"] = sha, os.path.basename(chemin)
        pdfs[sha] = chemin
        lecture = cache.get(sha)
        if lecture is None:
            try:
                lu = lecture_tva.lire_pdf(chemin)
                lecture = {"recap": lu["recap"], "neant": lu["neant"], "nette": lu["nette"], "credit": lu["credit"]}
            except Exception as e:  # PDF abîmé ou formulaire inconnu : signalé, jamais bloquant
                lecture = {"erreur": f"lecture impossible : {e}"}
            cache[sha] = lecture
            nouvelles += 1
        if lecture.get("erreur"):
            d["controle_msg"] = lecture["erreur"]
        else:
            ok, msg = lecture_tva.controler(lecture, r["montant"], r["is_credit"])
            d.update(recap=lecture["recap"], controle_ok=ok, controle_msg=msg)
        out.append(d)
    if nouvelles:
        ecrire_json(CACHE, cache)
    return out, pdfs, maj


def synchroniser(config):
    annees = config.get("annees") or [datetime.now().year, datetime.now().year - 1]
    declarations, pdfs, maj = lire_declarations(annees)
    r = appel("POST", "tva", {"declarations": declarations, "poste": socket.gethostname(), "maj_comptazap": maj}, delai=300)
    manquants = r.get("pdfs_manquants") or []
    for sha in manquants:
        if sha in pdfs:
            with open(pdfs[sha], "rb") as f:
                appel("POST", f"pdf/{sha}", binaire=f.read())
    ko = sum(1 for d in declarations if not d["controle_ok"])
    noter(f"Envoyé : {len(declarations)} déclarations ({ko} non contrôlées), {len(manquants)} PDF")
    return len(declarations), ko


# --- Boucle ----------------------------------------------------------------------------------------------------------

def passage(etat):
    config = appel("GET", "config?poste=" + urllib.request.quote(socket.gethostname()))
    intervalle = int(config.get("intervalle_minutes") or 30) * 60
    if config.get("demande") or time.time() - etat.get("derniere", 0) >= intervalle:
        try:
            synchroniser(config)
        except ErreurSite:
            raise
        except Exception as e:  # ComptaZap absent ou base illisible : dit au site, réessayé au prochain passage
            appel("POST", "etat", {"erreur": f"ComptaZap illisible : {e}", "poste": socket.gethostname()})
            noter(f"ComptaZap illisible : {e}")
        etat["derniere"] = time.time()


def prendre_verrou():
    """Un seul connecteur à la fois (fichier verrouillé tant qu'il tourne)."""
    import msvcrt
    os.makedirs(DONNEES, exist_ok=True)
    f = open(os.path.join(DONNEES, "connecteur.verrou"), "a+")
    try:
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f
    except OSError:
        f.close()
        return None


def tourner():
    verrou = prendre_verrou()
    if verrou is None:
        return
    etat = {}
    noter("Connecteur démarré")
    while True:
        try:
            passage(etat)
        except ErreurSite as e:
            noter(str(e))
        except Exception as e:  # jamais d'arrêt sur une erreur imprévue
            noter(f"erreur imprévue : {e.__class__.__name__} {e}")
        time.sleep(PAUSE)


def regler_demarrage(actif):
    """Raccourci dans le dossier Démarrage de Windows : pythonw connecteur.py, sans fenêtre."""
    import ctypes
    import subprocess
    tampon = ctypes.create_unicode_buffer(260)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x07, None, 0, tampon)  # CSIDL_STARTUP
    lien = os.path.join(tampon.value, RACCOURCI)
    if not actif:
        if os.path.exists(lien):
            os.remove(lien)
        return
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    pyw = pyw if os.path.exists(pyw) else sys.executable
    e = lambda s: s.replace("'", "''")
    script = (f"$s = New-Object -ComObject WScript.Shell; $l = $s.CreateShortcut('{e(lien)}'); $l.TargetPath = '{e(pyw)}'; "
              f"$l.Arguments = '-s -E \"{e(os.path.abspath(__file__))}\"'; $l.WorkingDirectory = '{e(ICI)}'; "
              "$l.WindowStyle = 7; $l.Description = 'Dossier Bilan - connecteur ComptaZap'; $l.Save()")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], check=True,
                   creationflags=0x08000000, capture_output=True)


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--lier":
        lier(sys.argv[2], sys.argv[3])
        print("Connecteur lié à", sys.argv[2])
    elif len(sys.argv) >= 3 and sys.argv[1] == "--demarrage":
        regler_demarrage(sys.argv[2].lower() in ("oui", "on", "1"))
        print("Démarrage automatique :", sys.argv[2])
    elif "--une-fois" in sys.argv:
        n, ko = synchroniser(appel("GET", "config?poste=" + urllib.request.quote(socket.gethostname())))
        print(f"Synchro envoyée : {n} déclarations, {ko} non contrôlées")
    else:
        tourner()
