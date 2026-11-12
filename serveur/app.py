"""Dossier Bilan, version web : le serveur (Flask). Sert l'interface (dossier web/) et l'API JSON des dossiers bilan.

Le calcul (moteur/) est refait en entier à chaque modification : il prend quelques millisecondes, donc l'écran est
toujours à jour et il n'y a pas de cache à invalider. Comptes dans comptes.py ; toute l'API exige une session.

Mode démo (BILAN_DEMO=1) : base séparée remplie de dossiers fictifs (demo.py), connexion « demo » sans mot de passe,
aucun appel à Pennylane ni au connecteur ComptaZap.

Lancement : `python lancer.py` (serveur waitress, voir README.md).
"""
import io
import os
import secrets
import time
from datetime import date, timedelta
from functools import wraps

from flask import Flask, abort, jsonify, request, send_file, send_from_directory, session

import comptazap
import comptes
import demo
import export_excel
import import_fichier
import pennylane
import stockage
from moteur import calculer
from moteur.outils import ajouter_mois, lire_date
from moteur.referentiel import STATUTS_REVISION

WEB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web")
ESSAIS = {}                       # adresse -> [instants des connexions ratées] (anti-devinette)
TAILLE_MAX = 15 * 1024 * 1024
DEMO = os.environ.get("BILAN_DEMO") == "1"          # démo hors ligne : dossiers fictifs, aucun service externe
SANS_MDP = DEMO or os.environ.get("BILAN_SANS_MDP") == "1"  # réseau local de confiance : on choisit son nom, sans mot de passe
MSG_DEMO = "Désactivé en mode démo : aucune connexion à Pennylane ni au connecteur ComptaZap."
PARAMETRES_MODIFIABLES = {"taux_cotis_tns_dividendes"}  # le jeton Pennylane d'un dossier ne repart jamais vers l'interface


def cle_secrete():
    """Clé des sessions, créée au premier lancement (data/secret.key), jamais dans le code."""
    chemin = os.path.join(stockage.DATA, "secret.key")
    if not os.path.exists(chemin):
        os.makedirs(stockage.DATA, exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as f:
            f.write(secrets.token_hex(32))
    with open(chemin, encoding="utf-8") as f:
        return f.read().strip()


def dossier_moteur(d):
    """L'enregistrement stocké, au format attendu par le moteur."""
    infos = dict(d["infos"] or {})
    infos.setdefault("client", d["nom"])
    infos["debut_exercice"] = d["debut_exercice"]
    infos["cloture"] = d["cloture"]
    return {"infos": infos, "balance": d["balance"], "saisies": d["saisies"], "recap_tva": d["recap_tva"],
            "journal_paie": d["journal_paie"], "parametres": d["parametres"]}


def exercice_precedent(debut, cloture):
    """Dates de l'exercice N-1, de même durée, qui se termine la veille du début de N."""
    d, c = lire_date(debut), lire_date(cloture)
    fin_n1 = d - timedelta(days=1)
    mois = (c.year - d.year) * 12 + c.month - d.month + 1
    debut_n1 = ajouter_mois(date(fin_n1.year, fin_n1.month, 1), -(mois - 1))
    return debut_n1.isoformat(), fin_n1.isoformat()


def creer_app():
    app = Flask(__name__, static_folder=None)
    app.config.update(SECRET_KEY=cle_secrete(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Strict",
                      SESSION_COOKIE_SECURE=os.environ.get("BILAN_HTTPS") == "1", PERMANENT_SESSION_LIFETIME=timedelta(days=14),
                      MAX_CONTENT_LENGTH=TAILLE_MAX)
    stockage.initialiser()
    comptazap.initialiser()
    if DEMO:
        comptes.initialiser()
        demo.semer()

    # ---------- Sécurité ----------
    def connecte(f):
        @wraps(f)
        def garde(*a, **k):
            if not session.get("identifiant") or session["identifiant"] not in comptes.lire():
                return jsonify(erreur="Session expirée : reconnectez-vous."), 401
            if request.method in ("POST", "PATCH", "PUT", "DELETE") and request.headers.get("X-Bilan") != "1":
                abort(403)  # requête venue d'ailleurs que l'interface
            return f(*a, **k)
        return garde

    def hors_demo(f):
        """Routes qui parlent à un service externe (Pennylane, connecteur du poste) : coupées en démo."""
        @wraps(f)
        def garde(*a, **k):
            if DEMO:
                return jsonify(erreur=MSG_DEMO, demo=True), 403
            return f(*a, **k)
        return garde

    @app.after_request
    def entetes(r):
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["Referrer-Policy"] = "same-origin"
        r.headers["Content-Security-Policy"] = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
                                                "script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
        if request.path.startswith("/api/"):
            r.headers["Cache-Control"] = "no-store"
        return r

    @app.errorhandler(stockage.Conflit)
    def conflit(_):
        return jsonify(erreur="Ce dossier vient d'être modifié par quelqu'un d'autre : l'écran a été rechargé.", conflit=True), 409

    @app.errorhandler(import_fichier.ErreurImport)
    def erreur_import(e):
        return jsonify(erreur=str(e)), 422

    @app.errorhandler(pennylane.ErreurPennylane)
    def erreur_pennylane(e):
        return jsonify(erreur=str(e)), 502

    @app.errorhandler(413)
    def trop_gros(_):
        return jsonify(erreur="Fichier trop volumineux (15 Mo au plus)."), 413

    # ---------- Pages ----------
    @app.get("/")
    def accueil():
        return send_from_directory(WEB, "index.html")

    @app.get("/<path:fichier>")
    def statique(fichier):
        if fichier.startswith("api/"):
            abort(404)
        return send_from_directory(WEB, fichier)

    # ---------- Connexion ----------
    @app.post("/api/connexion")
    def connexion():
        ip, t = request.remote_addr or "?", time.time()
        ESSAIS[ip] = [x for x in ESSAIS.get(ip, []) if t - x < 300]
        if len(ESSAIS[ip]) >= 5:
            return jsonify(erreur="Trop d'essais : réessayez dans 5 minutes."), 429
        d = request.get_json(silent=True) or {}
        if SANS_MDP:
            ident = (d.get("identifiant") or "").strip().lower()
            c = comptes.lire().get(ident)
            compte = {"identifiant": ident, "nom": c["nom"]} if c else None
        else:
            compte = comptes.verifier(d.get("identifiant"), d.get("mot_de_passe"))
        if not compte:
            ESSAIS[ip].append(t)
            return jsonify(erreur="Identifiant ou mot de passe incorrect."), 401
        session.clear()
        session.permanent = True
        session["identifiant"], session["nom"] = compte["identifiant"], compte["nom"]
        return jsonify(compte)

    @app.get("/api/config")
    def config():
        """Avant connexion : sans mot de passe, l'écran d'accueil propose simplement les comptes."""
        liste = [{"identifiant": k, "nom": v["nom"]} for k, v in comptes.lire().items()] if SANS_MDP else []
        return jsonify(sans_mdp=SANS_MDP, demo=DEMO, comptes=liste)

    @app.post("/api/deconnexion")
    def deconnexion():
        session.clear()
        return jsonify(ok=True)

    @app.get("/api/moi")
    @connecte
    def moi():
        return jsonify(identifiant=session["identifiant"], nom=session["nom"], statuts=STATUTS_REVISION, sans_mdp=SANS_MDP, demo=DEMO)

    @app.post("/api/mot-de-passe")
    @connecte
    def mot_de_passe():
        if DEMO:
            return jsonify(erreur="Pas de mot de passe à changer en mode démo."), 403
        d = request.get_json(silent=True) or {}
        if not comptes.verifier(session["identifiant"], d.get("ancien")):
            return jsonify(champs={"ancien": "Mot de passe actuel incorrect."}), 422
        try:
            comptes.changer(session["identifiant"], d.get("nouveau"))
        except ValueError as e:
            return jsonify(champs={"nouveau": str(e)}), 422
        return jsonify(ok=True)

    # ---------- Dossiers ----------
    def qui():
        return session.get("nom") or session.get("identifiant") or "?"

    def charger(dossier_id):
        d = stockage.lire(dossier_id)
        if not d:
            abort(404)
        return d

    def reponse_dossier(d):
        t = time.perf_counter()
        r = calculer(dossier_moteur(d))
        duree = (time.perf_counter() - t) * 1000
        meta = {k: d[k] for k in ("id", "nom", "siren", "pennylane_id", "debut_exercice", "cloture", "source_balance",
                                  "balance_importee_le", "maj_le", "maj_par", "version")}
        meta["jeton_dossier"] = bool((d["parametres"] or {}).get("jeton_pennylane"))
        params = {k: v for k, v in (d["parametres"] or {}).items() if k in PARAMETRES_MODIFIABLES}
        return jsonify(dossier=meta, saisies=d["saisies"], infos=d["infos"], parametres=params, resultats=r, calcul_ms=round(duree, 1),
                       nb_paie=len(d["journal_paie"] or []), mois_tva=sorted((d["recap_tva"] or {}).keys()))

    @app.get("/api/dossiers")
    @connecte
    def dossiers():
        return jsonify(dossiers=stockage.lister(request.args.get("archives") == "1"))

    @app.post("/api/dossiers")
    @connecte
    def nouveau():
        d = request.get_json(silent=True) or {}
        nom = (d.get("nom") or "").strip()
        debut, cloture = lire_date(d.get("debut_exercice")), lire_date(d.get("cloture"))
        champs = {}
        if not nom:
            champs["nom"] = "Le nom du dossier est obligatoire."
        if not cloture:
            champs["cloture"] = "Date de clôture obligatoire."
        if cloture and not debut:
            debut = date.fromordinal(ajouter_mois(cloture, -12).toordinal() + 1)
        if debut and cloture and debut >= cloture:
            champs["debut_exercice"] = "Le début doit précéder la clôture."
        if champs:
            return jsonify(champs=champs), 422
        params = {}
        if d.get("jeton_pennylane"):
            params["jeton_pennylane"] = d["jeton_pennylane"].strip()
        infos = {"cabinet": "CABINET EXEMPLE", "client": nom, "forme": d.get("forme") or "", "annee_ir": cloture.year}
        saisies = {}
        if d.get("reprendre_de"):
            saisies = reprise(int(d["reprendre_de"]))
        nid = stockage.creer(nom, debut.isoformat(), cloture.isoformat(), qui(), d.get("siren") or "", d.get("pennylane_id") or "",
                             infos, saisies, params)
        return jsonify(id=nid)

    def reprise(precedent_id):
        """Ce qui passe d'un exercice au suivant (comme le faisait la macro Clearbalance) : statuts et commentaires de
        révision par compte, commentaires de balance, paramètres des associés, des emprunts et du cadrage."""
        p = stockage.lire(precedent_id)
        if not p:
            return {}
        s = p["saisies"] or {}
        garder = {}
        for k in ("revision", "commentaires"):
            if s.get(k):
                garder[k] = s[k]
        if s.get("cadrage_ca", {}).get("comptes"):
            garder["cadrage_ca"] = {"comptes": s["cadrage_ca"]["comptes"]}
        if s.get("tva_solde"):
            garder["tva_solde"] = s["tva_solde"]
        if s.get("ago_n", {}).get("associes"):
            assoc = [{k: a.get(k) for k in ("nom", "qualite", "dispense", "regime", "parts")} for a in s["ago_n"]["associes"] if a]
            garder["ago_n1"] = {"associes": assoc}
            garder["ago_n"] = {"associes": assoc}
        if s.get("tns"):
            garder["tns"] = {k: s["tns"].get(k) for k in ("nom", "mois_cloture", "comptes") if s["tns"].get(k)}
        if s.get("fiscal", {}).get("soumise_is"):
            garder["fiscal"] = {k: s["fiscal"].get(k) for k in ("soumise_is", "taux_reduit")}
        return garder

    @app.get("/api/dossiers/<int:dossier_id>")
    @connecte
    def lire_dossier(dossier_id):
        return reponse_dossier(charger(dossier_id))

    @app.delete("/api/dossiers/<int:dossier_id>")
    @connecte
    def supprimer(dossier_id):
        charger(dossier_id)
        stockage.supprimer(dossier_id, qui())
        return jsonify(ok=True)

    @app.patch("/api/dossiers/<int:dossier_id>")
    @connecte
    def modifier(dossier_id):
        """Une ou plusieurs saisies : {version, changements: [{chemin: "fiscal.tvs", valeur: 1200}, ...]}.
        Le chemin commence par « saisies. », « infos. », « parametres. » ou « dossier. » (nom, dates)."""
        d = charger(dossier_id)
        corps = request.get_json(silent=True) or {}
        saisies, infos, params, meta, libelles = d["saisies"], d["infos"], d["parametres"] or {}, {}, []
        for ch in corps.get("changements") or []:
            chemin, valeur = str(ch.get("chemin") or ""), ch.get("valeur")
            if isinstance(valeur, str) and len(valeur) > 20000:
                return jsonify(erreur="Texte trop long."), 422
            racine, _, reste = chemin.partition(".")
            if racine == "saisies" and reste:
                stockage.poser(saisies, reste, valeur)
            elif racine == "infos" and reste:
                stockage.poser(infos, reste, valeur)
            elif racine == "parametres" and reste in PARAMETRES_MODIFIABLES:
                if valeur in (None, ""):
                    params.pop(reste, None)
                else:
                    params[reste] = valeur
            elif racine == "dossier" and reste in ("nom", "debut_exercice", "cloture", "siren"):
                if reste in ("debut_exercice", "cloture") and not lire_date(valeur):
                    return jsonify(champs={reste: "Date invalide."}), 422
                meta[reste] = lire_date(valeur).isoformat() if reste != "nom" and reste != "siren" else str(valeur).strip()
            else:
                return jsonify(erreur=f"Champ inconnu : {chemin}"), 422
            libelles.append(chemin)
        stockage.modifier(dossier_id, {"saisies": saisies, "infos": infos, "parametres": params, **meta}, qui(), corps.get("version"),
                          action="Saisie : " + ", ".join(libelles)[:300] if libelles else "")
        return reponse_dossier(charger(dossier_id))

    @app.get("/api/dossiers/<int:dossier_id>/historique")
    @connecte
    def historique(dossier_id):
        return jsonify(historique=stockage.historique(dossier_id))

    # ---------- Imports ----------
    def fichier_recu():
        f = request.files.get("fichier")
        if f and f.filename:
            return f.read(), f.filename
        texte = request.form.get("texte") or (request.get_json(silent=True) or {}).get("texte")
        if texte:
            return texte.encode("utf-8"), "colle.txt"
        raise import_fichier.ErreurImport("Aucun fichier ni texte reçu.")

    @app.post("/api/dossiers/<int:dossier_id>/balance/fichier")
    @connecte
    def balance_fichier(dossier_id):
        d = charger(dossier_id)
        contenu, nom = fichier_recu()
        cible = request.form.get("cible") or "les_deux"
        lignes = import_fichier.balance(contenu, nom, cible)
        if cible == "n":
            lignes = import_fichier.fusionner(lignes, [{"compte": l["compte"], "libelle": l["libelle"], "solde_n": 0, "solde_n1": l["solde_n1"]} for l in d["balance"]])
        elif cible == "n1":
            lignes = import_fichier.fusionner([{"compte": l["compte"], "libelle": l["libelle"], "solde_n": l["solde_n"], "solde_n1": 0} for l in d["balance"]], lignes)
        stockage.modifier(dossier_id, {"balance": lignes, "source_balance": f"Fichier : {nom}", "balance_importee_le": stockage.maintenant()},
                          qui(), request.form.get("version"), action=f"Import de la balance ({nom}, {len(lignes)} comptes)")
        return reponse_dossier(charger(dossier_id))

    @app.post("/api/dossiers/<int:dossier_id>/balance/pennylane")
    @hors_demo
    @connecte
    def balance_pennylane(dossier_id):
        d = charger(dossier_id)
        corps = request.get_json(silent=True) or {}
        jeton = (d["parametres"] or {}).get("jeton_pennylane")
        company = None if jeton else (d["pennylane_id"] or corps.get("pennylane_id"))
        if not jeton and not company:
            return jsonify(erreur="Ce dossier n'est pas relié à Pennylane : choisissez le dossier Pennylane."), 422
        debut_n1, fin_n1 = exercice_precedent(d["debut_exercice"], d["cloture"])
        lignes = pennylane.balance_comparative(d["debut_exercice"], d["cloture"], debut_n1, fin_n1, company, jeton)
        if not lignes:
            return jsonify(erreur="Pennylane n'a renvoyé aucun compte sur cet exercice."), 422
        stockage.modifier(dossier_id, {"balance": lignes, "source_balance": "Pennylane", "balance_importee_le": stockage.maintenant(),
                                       "pennylane_id": str(company or d["pennylane_id"] or "")},
                          qui(), corps.get("version"), action=f"Import de la balance depuis Pennylane ({len(lignes)} comptes)")
        return reponse_dossier(charger(dossier_id))

    @app.post("/api/dossiers/<int:dossier_id>/tva/fichier")
    @connecte
    def tva_fichier(dossier_id):
        charger(dossier_id)
        contenu, nom = fichier_recu()
        recap = import_fichier.recap_tva(contenu, nom)
        stockage.modifier(dossier_id, {"recap_tva": recap}, qui(), request.form.get("version"),
                          action=f"Import du récapitulatif TVA ({nom}, {len(recap)} mois)")
        return reponse_dossier(charger(dossier_id))

    @app.post("/api/dossiers/<int:dossier_id>/paie/fichier")
    @connecte
    def paie_fichier(dossier_id):
        charger(dossier_id)
        contenu, nom = fichier_recu()
        journal = import_fichier.journal_paie(contenu, nom)
        stockage.modifier(dossier_id, {"journal_paie": journal}, qui(), request.form.get("version"),
                          action=f"Import du journal de paie ({len(journal)} lignes)")
        return reponse_dossier(charger(dossier_id))

    @app.get("/api/dossiers/<int:dossier_id>/export.xlsx")
    @connecte
    def export(dossier_id):
        d = charger(dossier_id)
        contenu = export_excel.exporter(d, calculer(dossier_moteur(d)))
        nom = f"Dossier bilan {d['nom']} {d['cloture']}.xlsx".replace("/", "-")
        return send_file(io.BytesIO(contenu), as_attachment=True, download_name=nom,
                         mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # ---------- Pennylane ----------
    @app.get("/api/pennylane")
    @hors_demo
    @connecte
    def pennylane_etat():
        return jsonify(pennylane.etat())

    @app.post("/api/pennylane")
    @hors_demo
    @connecte
    def pennylane_config():
        d = request.get_json(silent=True) or {}
        cfg = pennylane.lire_config()
        if d.get("mode") in ("cabinet", "entreprise"):
            cfg["mode"] = d["mode"]
        if d.get("jeton"):
            cfg["jeton"] = d["jeton"].strip()
        if d.get("effacer"):
            cfg.pop("jeton", None)
        pennylane.ecrire_config(cfg)
        pennylane._CACHE_DOSSIERS["liste"] = None  # nouveau jeton : la liste du portefeuille est relue
        return jsonify(pennylane.etat())

    @app.post("/api/pennylane/test")
    @hors_demo
    @connecte
    def pennylane_test():
        return jsonify(pennylane.tester())

    @app.get("/api/pennylane/dossiers")
    @hors_demo
    @connecte
    def pennylane_dossiers():
        return jsonify(dossiers=pennylane.dossiers(request.args.get("q", "")))

    @app.get("/api/pennylane/exercices")
    @hors_demo
    @connecte
    def pennylane_exercices():
        return jsonify(exercices=pennylane.exercices(request.args.get("company_id") or None))

    # ---------- Connecteur du poste (ComptaZap) : appels du programme installé sur le PC de ComptaZap ----------
    def poste(f):
        """Routes du connecteur : identifiées par le code de liaison (en-tête Authorization: Bearer DBL-…)."""
        @wraps(f)
        def garde(*a, **k):
            code = (request.headers.get("Authorization") or "").removeprefix("Bearer ").strip()
            if not comptazap.verifier_code(code):
                return jsonify(erreur="Code de liaison inconnu : recréez-le dans Paramètres › Connecteur du poste."), 401
            return f(*a, **k)
        return garde

    @app.get("/api/poste/config")
    @hors_demo
    @poste
    def poste_config():
        cfg = comptazap.contact(request.args.get("poste", ""))
        annee = date.today().year
        return jsonify(intervalle_minutes=30, demande=bool(cfg.get("demande")), annees=[annee, annee - 1, annee - 2])

    @app.post("/api/poste/tva")
    @hors_demo
    @poste
    def poste_tva():
        d = request.get_json(silent=True) or {}
        decl = d.get("declarations") or []
        if not isinstance(decl, list):
            return jsonify(erreur="Format inattendu."), 422
        manquants = comptazap.recevoir(decl, d.get("poste", ""), d.get("maj_comptazap", ""))
        return jsonify(recues=len(decl), pdfs_manquants=manquants)

    @app.post("/api/poste/pdf/<sha>")
    @hors_demo
    @poste
    def poste_pdf(sha):
        try:
            comptazap.enregistrer_pdf(sha, request.get_data())
        except ValueError as e:
            return jsonify(erreur=str(e)), 422
        return jsonify(ok=True)

    @app.post("/api/poste/etat")
    @hors_demo
    @poste
    def poste_etat():
        d = request.get_json(silent=True) or {}
        comptazap.contact(d.get("poste", ""), erreur=str(d.get("erreur") or "")[:500], demande=None)
        return jsonify(ok=True)

    # ---------- Connecteur : réglages (Paramètres) ----------
    @app.get("/api/connecteur")
    @hors_demo
    @connecte
    def connecteur_etat():
        return jsonify(comptazap.etat())

    @app.post("/api/connecteur/code")
    @hors_demo
    @connecte
    def connecteur_code():
        return jsonify(code=comptazap.nouveau_code(), adresse=request.host_url.rstrip("/"), **comptazap.etat())

    @app.post("/api/connecteur/synchroniser")
    @hors_demo
    @connecte
    def connecteur_synchro():
        comptazap.demander_synchro(qui())
        return jsonify(comptazap.etat())

    @app.post("/api/connecteur/delier")
    @hors_demo
    @connecte
    def connecteur_delier():
        comptazap.delier()
        return jsonify(comptazap.etat())

    # ---------- Déclarations de TVA ComptaZap dans un dossier ----------
    def declarations_dossier(d):
        return comptazap.declarations_exercice(d["siren"], lire_date(d["debut_exercice"]), lire_date(d["cloture"]))

    @app.get("/api/dossiers/<int:dossier_id>/comptazap")
    @hors_demo
    @connecte
    def dossier_comptazap(dossier_id):
        d = charger(dossier_id)
        decl = declarations_dossier(d)
        for x in decl:
            x.pop("recap", None)
            x["pdf"] = bool(x.get("pdf_sha") and comptazap.chemin_pdf(x["pdf_sha"]))
        return jsonify(siren=d["siren"], declarations=decl, connecteur=comptazap.etat())

    @app.post("/api/dossiers/<int:dossier_id>/tva/comptazap")
    @hors_demo
    @connecte
    def dossier_tva_comptazap(dossier_id):
        d = charger(dossier_id)
        if len("".join(c for c in (d["siren"] or "") if c.isdigit())) != 9:
            return jsonify(erreur="Renseignez le SIREN du dossier (onglet Dossier) : il relie le dossier à ComptaZap."), 422
        decl = declarations_dossier(d)
        recap, ecartees = comptazap.vers_recap(decl)
        if not recap:
            return jsonify(erreur="Aucune déclaration de TVA ComptaZap contrôlée sur cet exercice pour ce SIREN."
                           + (f" ({len(ecartees)} écartée(s) : contrôle non concluant)" if ecartees else "")), 422
        retenues = [x for x in decl if x["retenue"] and x["controle_ok"]]
        saisies = d["saisies"]
        stockage.poser(saisies, "tva.source", {"origine": "ComptaZap", "le": stockage.maintenant(), "declarations": len(retenues),
                                               "ecartees": [f"{x['periode_debut']} → {x['periode_fin']} : {x['controle_msg']}" for x in ecartees]})
        corps = request.get_json(silent=True) or {}
        stockage.modifier(dossier_id, {"recap_tva": recap, "saisies": saisies}, qui(), corps.get("version"),
                          action=f"Import TVA depuis ComptaZap ({len(retenues)} déclarations)")
        return reponse_dossier(charger(dossier_id))

    @app.get("/api/comptazap/pdf/<sha>")
    @hors_demo
    @connecte
    def comptazap_pdf(sha):
        chemin = comptazap.chemin_pdf(sha)
        if not chemin:
            abort(404)
        return send_file(chemin, mimetype="application/pdf")

    return app
