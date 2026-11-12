"""Cadrage du chiffre d'affaires et de la TVA (feuilles Cadrage_CA, TVA_Récap_Pennylane, TVA_Récap_Interne,
TVA_Cadrage_Solde, TVA_Cadrage_Flux)."""
from datetime import date

from . import referentiel as R
from .balance import somme
from .outils import ajouter_mois, arrondi, div, egal, nombre, signalisation

CHAMPS_COLONNE = ["fae_n1", "aae_n1", "pca_n1", "fae_n", "aae_n", "pca_n", "cessions", "debours",
                  "client_411_n1", "client_416_n1", "client_4191_n1", "client_411_n", "client_416_n", "client_4191_n",
                  "pertes", "produits_exc"]


def _taux_compte(saisie):
    """Le taux saisi pour un compte de CA, normalisé sur les clés de R.TAUX_CA ('8.5' -> '8,5')."""
    t = str((saisie or {}).get("taux") or "").strip().upper().replace(".", ",")
    if t.endswith(",0"):
        t = t[:-2]
    return t


def cadrage_ca(bg, saisies):
    s = saisies or {}
    par_compte = s.get("comptes") or {}
    comptes = []
    for r in bg:
        if r["compte"][:2] == "70":
            sc = par_compte.get(r["compte"]) or {}
            comptes.append({"compte": r["compte"], "libelle": r["libelle"], "n": r["n"], "n1": r["n1"],
                            "commentaire": r["commentaire"], "taux": _taux_compte(sc), "type": sc.get("type") or ""})
    colonnes = {}
    for cle, taux in R.TAUX_CA:
        c = {k: nombre(((s.get("colonnes") or {}).get(cle) or {}).get(k)) for k in CHAMPS_COLONNE}
        taxe = cle in R.TAUX_CA_TAXES
        ht = -sum(x["n"] for x in comptes if x["taux"] == cle)
        corr_debut = c["fae_n1"] - c["aae_n1"] - c["pca_n1"]
        corr_fin = -c["fae_n"] + c["aae_n"] + c["pca_n"]
        ca_facture = ht + corr_debut + corr_fin
        tva_ca = ca_facture * taux / 100 if taxe else 0.0
        # La reconstitution reprend les cessions seules (ligne 61 = ligne 55), pas les débours : voir ECARTS_EXCEL.md, Q2.
        autres = c["cessions"]
        tva_autres = autres * taux / 100 if taxe else 0.0
        corr_ht = c["pertes"] - c["produits_exc"]
        if taxe:
            corr_ttc = -corr_ht * (1 + taux / 100)
        elif cle == "0":
            corr_ttc = 0.0  # la colonne 0 % n'a pas de formule dans l'Excel
        else:
            corr_ttc = -corr_ht
        colonnes[cle] = {
            **c, "taux": taux, "libelle_ht": f"HT-{cle}", "libelle_ttc": f"TTC-{cle}" if taxe else f"HT-{cle}",
            "ht_realise": ht, "corr_debut": corr_debut, "corr_fin": corr_fin, "debours_total": c["cessions"] + c["debours"],
            "ca_facture": ca_facture, "tva_ca": tva_ca, "autres": autres, "tva_autres": tva_autres,
            "facturation_ttc": ca_facture + tva_ca + autres + tva_autres,
            "solde_client_n1": c["client_411_n1"] + c["client_416_n1"] + c["client_4191_n1"],
            "solde_client_n": c["client_411_n"] + c["client_416_n"] + c["client_4191_n"],
            "corrections_ht": corr_ht, "corrections_ttc": corr_ttc,
        }
    controles = []
    for racine, libelle, k in (("411", "Clients", "411"), ("416", "Clients douteux", "416"), ("4191", "Avances et acomptes", "4191")):
        n1, n = somme(bg, racine, "n1"), somme(bg, racine, "n")
        saisi_n1 = sum(col[f"client_{k}_n1"] for col in colonnes.values())
        saisi_n = sum(col[f"client_{k}_n"] for col in colonnes.values())
        controles.append({"racine": racine, "libelle": f"{racine} - {libelle}", "n1": n1, "n": n,
                          "ecart_n1": saisi_n1 - n1, "ecart_n": saisi_n - n})
    non_affectes = [x for x in comptes if x["taux"] not in dict(R.TAUX_CA) and x["n"]]
    return {"comptes": comptes, "total_ca": sum(x["n"] for x in comptes), "colonnes": colonnes, "controles": controles,
            "non_affectes": non_affectes}


def ventilation_liasse(ca):
    """Chiffre d'affaires ventilé pour la liasse (Liasse_fiscale E7 à E10).

    CORRECTION n°9 : l'Excel ne lit que les 13 premiers comptes 70 (Cadrage_CA D7:D19) ; ici, tous.
    """
    def total(type_, taux):
        return -sum(x["n"] for x in ca["comptes"] if egal(x["type"], type_) and x["taux"] in taux)
    france, inter = R.TAUX_CA_TAXES, ["INTRA", "EXTRA"]
    return {"march_france": total("Marchandises", france), "march_inter": total("Marchandises", inter),
            "services_france": total("Services", france), "services_inter": total("Services", inter)}


# ---------------------------------------------------------------------------------------------------------------
# Récapitulatif des déclarations de TVA
# ---------------------------------------------------------------------------------------------------------------
def periodes(debut, cloture):
    """Les mois de l'exercice (premier jour de chaque mois), au plus 22 comme l'Excel (colonnes F à AA)."""
    mois, d = [], date(debut.year, debut.month, 1)
    while d < cloture and len(mois) < 24:
        mois.append(d)
        d = ajouter_mois(d, 1)
    return mois


def recap_tva(recap_pennylane, debut, cloture, saisies):
    """TVA_Récap_Interne : la CA3 de chaque mois, reprise du récapitulatif Pennylane.

    recap_pennylane : {"AAAA-MM": {code: {"base": x, "taxe": y}}}. Un mois absent vaut 0.
    """
    recap = recap_pennylane or {}
    rembourse = (saisies or {}).get("remboursements") or {}
    mois_list = periodes(debut, cloture) if debut and cloture else []
    colonnes = []
    for m in mois_list:
        cle = m.strftime("%Y-%m")
        donnees = recap.get(cle) or {}

        def base(code):
            return nombre((donnees.get(code) or {}).get("base"))

        def taxe(code):
            return nombre((donnees.get(code) or {}).get("taxe"))
        v = {code: base(code) for code in R.CA3_BASES}
        brute = 0.0
        for code, taux in R.CA3_TAXABLES:
            v[code] = base(code)
            v[code + "_taxe"] = arrondi(v[code] * taux, 0)
            brute += v[code + "_taxe"]
        for code in R.CA3_TAXE_DUE:
            v[code] = taxe(code)
        v["16"] = brute + v["15"] + v["5B"]
        v["17"] = arrondi(v["B2"] * 0.2, 0)
        for code in R.CA3_DEDUCTIBLE:
            v[code] = base(code)  # l'Excel lit ces lignes dans la colonne « Base HT » du récapitulatif
        v["23"] = sum(v[c] for c in R.CA3_DEDUCTIBLE)
        v["25"] = v["23"] - v["16"] if v["23"] > v["16"] else 0.0
        v["26"] = nombre(rembourse.get(cle))
        v["27"] = v["25"] - v["26"]
        v["28"] = v["16"] - v["23"] if v["16"] > v["23"] else 0.0
        colonnes.append({"mois": cle, "libelle": m.strftime("%m-%Y"), "present": bool(donnees), "valeurs": v})
    totaux = {}
    for col in colonnes:
        for k, x in col["valeurs"].items():
            totaux[k] = totaux.get(k, 0.0) + x
    return {"colonnes": colonnes, "totaux": totaux,
            "mois_manquants": [c["libelle"] for c in colonnes if not c["present"]],
            "mois_hors_exercice": sorted(k for k in recap if k not in {c["mois"] for c in colonnes})}


def cadrage_solde(bg, ca, saisies):
    """TVA_Cadrage_Solde : solde théorique de la TVA collectée (d'après le solde client) contre le solde des 4457."""
    s = saisies or {}
    types = s.get("types") or {}
    comptes = []
    for r in bg:
        if r["compte"][:4] == "4457":
            t = str(types.get(r["compte"], "20")).strip().replace(".", ",")
            comptes.append({"compte": r["compte"], "libelle": r["libelle"], "n": r["n"], "n1": r["n1"], "type": t})
    colonnes = {}
    for cle, taux in R.TAUX_CA:
        col = ca["colonnes"][cle]
        c = {"libelle": col["libelle_ttc"], "solde_client_n1": col["solde_client_n1"], "solde_client_n": col["solde_client_n"]}
        if cle in R.TAUX_CA_TAXES:
            for suf, champ_client, champ_solde in (("n1", "solde_client_n1", "n1"), ("n", "solde_client_n", "n")):
                theo = -(col[champ_client] / (1 + taux / 100) * (taux / 100))
                reel = sum(x[champ_solde] for x in comptes if x["type"] == cle)
                ecart = reel - theo
                c.update({f"tva_theorique_{suf}": theo, f"tva_reelle_{suf}": reel, f"ecart_{suf}": ecart,
                          f"signal_{suf}": signalisation(ecart), f"ecart_ht_{suf}": ecart / (taux / 100),
                          f"signal_ht_{suf}": signalisation(ecart / (taux / 100))})
        colonnes[cle] = c
    return {"comptes": comptes, "colonnes": colonnes}


def cadrage_flux(bg, ca, recap, solde, saisies):
    """TVA_Cadrage_Flux : base HT théorique (encaissements) contre base HT déclarée sur l'exercice."""
    s = saisies or {}
    t = recap["totaux"]
    declare_auto = {
        "20": t.get("08", 0) - t.get("B2", 0) - t.get("A4", 0) - t.get("A3", 0) - t.get("A2", 0),
        "10": t.get("9B", 0), "8,5": t.get("10", 0), "5,5": t.get("09", 0),
    }
    colonnes = {}
    for cle, taux in R.TAUX_CA:
        col, sc = ca["colonnes"][cle], (s.get(cle) or {})
        taxe = cle in R.TAUX_CA_TAXES
        encaisse = col["solde_client_n1"] + col["facturation_ttc"] + col["corrections_ttc"] - col["solde_client_n"]
        theorique = encaisse / (1 + taux / 100) if taxe else encaisse
        declare = declare_auto[cle] if taxe else nombre(sc.get("base_declaree"))
        ecart = declare - theorique
        regul = nombre(sc.get("regularisation"))
        # CORRECTION n°2 : pour 0 %, INTRA et EXTRA, l'Excel divise par le taux de la colonne voisine et renvoie
        # toujours 0 (« ok »). Sans TVA, la régularisation s'ajoute telle quelle à la base.
        apres = ecart + (regul / (taux / 100) if taxe else regul)
        sol = solde["colonnes"][cle]
        ecart_solde_n = sol.get("ecart_ht_n", 0.0) if taxe else 0.0
        ecart_solde_n1 = sol.get("ecart_ht_n1", 0.0) if taxe else 0.0
        diff = apres + ecart_solde_n + ecart_solde_n1
        colonnes[cle] = {
            "libelle": col["libelle_ttc"], "solde_client_n1": col["solde_client_n1"], "facturation_ttc": col["facturation_ttc"],
            "corrections_ttc": col["corrections_ttc"], "solde_client_n": col["solde_client_n"], "encaissements": encaisse,
            "base_theorique": theorique, "base_declaree": declare, "base_declaree_auto": taxe, "ecart": ecart,
            "signal": signalisation(ecart), "regularisation": regul, "ecart_apres_regul": apres,
            "signal_apres": signalisation(apres), "ecart_solde_n": ecart_solde_n, "ecart_solde_n1": ecart_solde_n1,
            "difference": diff, "signal_difference": signalisation(diff),
        }
    comptes = [{"compte": r["compte"], "libelle": r["libelle"], "n": r["n"], "n1": r["n1"]}
               for r in bg if r["compte"][:4] in ("4457", "4458")]
    return {"colonnes": colonnes, "comptes": comptes}
