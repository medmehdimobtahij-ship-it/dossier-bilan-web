"""Banc de parité : l'Excel d'origine et le moteur calculent le même dossier, puis on compare cellule par cellule.

Usage (poste Windows avec Excel) :
    python tests/parite/excel_parite.py "chemin\classeur_bilan.xlsm" [graine ...]   (classeur Excel d'origine, non publié)

Pour chaque graine, un dossier fictif complet est généré (scenarios.py), écrit dans une COPIE de l'Excel (l'original
n'est jamais modifié), recalculé par Excel, relu, puis comparé au moteur. Les écarts dus aux défauts connus de l'Excel
(docs/ECARTS_EXCEL.md) sont comptés à part : ils sont attendus, et le rapport dit pourquoi.
"""
import json
import os
import shutil
import sys
import tempfile
import time
from datetime import date, datetime

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", "serveur"))
sys.path.insert(0, ICI)

import scenarios  # noqa: E402
from moteur import calculer, referentiel as R, sig as sig_module  # noqa: E402

COLS_CA = ["C", "D", "E", "F", "G", "H", "I"]          # Cadrage_CA : 20, 10, 8,5, 5,5, 0, INTRA, EXTRA
COLS_FLUX = ["D", "E", "F", "G", "H", "I", "J"]        # TVA_Cadrage_Flux, même ordre
COLS_ASSOC = ["D", "E", "F", "G", "H", "I"]
MOIS = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
TAUX_EXCEL = {"20": 20, "10": 10, "8,5": 8.5, "5,5": 5.5, "0": 0, "INTRA": "INTRA", "EXTRA": "EXTRA"}


def serie(d):
    """Une date en numéro de série Excel (écrire un datetime par COM la décale avec le fuseau horaire)."""
    return float((d - date(1899, 12, 30)).days)


def depuis_serie(x):
    return date.fromordinal(date(1899, 12, 30).toordinal() + int(x))


def col(lettre, decalage):
    """Colonne décalée : col('F', 2) -> 'H' (jusqu'à AZ)."""
    n = 0
    for ch in lettre:
        n = n * 26 + ord(ch) - 64
    n += decalage
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# ---------------------------------------------------------------------------------------------------------------
# Écriture du dossier dans l'Excel
# ---------------------------------------------------------------------------------------------------------------
def ecrire(wb, d):
    i, s = d["infos"], d["saisies"]

    def ws(nom):
        return wb.Worksheets(nom)

    def put(nom, adr, v):
        ws(nom).Range(adr).Value = v

    # Balance
    bp = ws("BalanceP")
    n = len(d["balance"])
    bp.ListObjects("Tableau7").Resize(bp.Range(f"A2:D{2 + n}"))
    bp.Range(f"A3:D{2 + n}").Value = tuple((int(l["compte"]), l["libelle"], l["solde_n"], l["solde_n1"]) for l in d["balance"])

    # Aller à
    cloture = date.fromisoformat(i["cloture"])
    for adr, v in (("J10", i["cabinet"]), ("J11", i["client"]), ("J12", i["forme"]), ("J13", None),
                   ("J14", serie(cloture)), ("J15", i["annee_ir"]),
                   ("J18", i["concerne_indemnite_rf"]), ("J19", i["concerne_indemnite_micro"]), ("J20", i["concerne_bic"]),
                   ("J21", i["concerne_lmp"]), ("J22", i["concerne_lmnp"]), ("K18", i["indemnite_rf"]), ("K19", i["indemnite_micro"])):
        put("Aller à", adr, v)

    # Capitaux
    c = s["capitaux"]
    for adr, k in (("D29", "dividendes"), ("D30", "compte_exploitant"), ("D31", "autres_1"), ("D32", "autres_2"), ("D33", "autres_3")):
        put("Capitaux", adr, c[k])

    # Assemblées
    def associes(nom, liste, lignes):
        for j, cl in enumerate(COLS_ASSOC):
            a = liste[j] if j < len(liste) else {}
            for champ, ligne in lignes.items():
                v = a.get(champ)
                if champ == "nom":
                    v = v or f"Associé {j + 1}"
                elif v in (0, "", None):
                    v = None
                put(nom, f"{cl}{ligne}", v)
    a1 = s["ago_n1"]
    put("AGO_N_1", "E4", a1["taux_ps"])
    associes("AGO_N_1", a1["associes"], {"nom": 8, "qualite": 9, "dispense": 10, "regime": 11, "parts": 12, "force": 15, "qp": 18})
    a = s["ago_n"]
    put("AGO_N", "E4", a["taux_ps"])
    for adr, k in (("D27", "reserve_statutaire"), ("D28", "reserves_reglementees"), ("D29", "autres_reserves"),
                   ("D30", "dividendes"), ("D31", "compte_courant")):
        put("AGO_N", adr, a[k])
    associes("AGO_N", a["associes"], {"nom": 37, "qualite": 38, "dispense": 39, "regime": 40, "parts": 41, "force": 44, "cc_moyen": 46})
    dp = date.fromisoformat(a["date_paiement"])
    put("AGO_N", "D55", serie(dp))

    # Cadrage du CA : taux et type par compte (ordre de la liste triée), puis les saisies par colonne
    cc = s["cadrage_ca"]
    c70 = sorted({l["compte"] for l in d["balance"] if l["compte"].startswith("70")}, key=str.casefold)
    ws("Cadrage_CA").Range("G7:H32").ClearContents()
    for k, compte in enumerate(c70):
        put("Cadrage_CA", f"G{7 + k}", TAUX_EXCEL[cc["comptes"][compte]["taux"]])
        put("Cadrage_CA", f"H{7 + k}", cc["comptes"][compte]["type"])
    lignes_ca = {"fae_n1": 47, "aae_n1": 48, "pca_n1": 49, "fae_n": 51, "aae_n": 52, "pca_n": 53, "cessions": 55, "debours": 56,
                 "client_411_n1": 66, "client_416_n1": 67, "client_4191_n1": 68, "client_411_n": 72, "client_416_n": 73,
                 "client_4191_n": 74, "pertes": 83, "produits_exc": 84}
    for (cle, _), cl in zip(R.TAUX_CA, COLS_CA):
        for champ, ligne in lignes_ca.items():
            put("Cadrage_CA", f"{cl}{ligne}", cc["colonnes"][cle][champ])

    # Récapitulatif TVA Pennylane : deux colonnes par mois (Base HT, Taxe due)
    tp = ws("TVA_Récap_Pennylane")
    tp.Range("F9:AG95").ClearContents()
    codes = {str(tp.Range(f"B{r}").Value): r for r in range(12, 96) if tp.Range(f"B{r}").Value is not None}
    k = 0
    for mois in sorted(d["recap_tva"]):
        an, m = mois.split("-")
        cb, ct = col("F", 2 * k), col("F", 2 * k + 1)
        tp.Range(f"{cb}9").Value = f"{MOIS[int(m) - 1]} {an}"
        tp.Range(f"{ct}9").Value = f"{MOIS[int(m) - 1]} {an}"
        for code, v in d["recap_tva"][mois].items():
            if code in codes:
                tp.Range(f"{cb}{codes[code]}").Value = v.get("base")
                tp.Range(f"{ct}{codes[code]}").Value = v.get("taxe")
        k += 1

    # Cadrage de la TVA
    types = s["tva_solde"]["types"]
    c4457 = sorted((l["compte"] for l in d["balance"] if l["compte"].startswith("4457")), key=str.casefold)
    ws("TVA_Cadrage_Solde").Range("O7:O21").ClearContents()
    for k, compte in enumerate(c4457):
        put("TVA_Cadrage_Solde", f"O{7 + k}", TAUX_EXCEL[types.get(compte, "20")])
    for (cle, _), cl in zip(R.TAUX_CA, COLS_FLUX):
        put("TVA_Cadrage_Flux", f"{cl}16", s["tva_flux"][cle]["regularisation"])
        if cle in ("0", "INTRA", "EXTRA"):
            put("TVA_Cadrage_Flux", f"{cl}13", s["tva_flux"][cle]["base_declaree"])

    # Résultat fiscal
    f = s["fiscal"]
    for adr, k in (("D11", "tvs"), ("D12", "loyers_cb"), ("D13", "taxe_bureaux_payee"), ("D14", "abandon"), ("D15", "sci_ir"),
                   ("D16", "amort_lmnp"), ("D17", "divers_reint"), ("E22", "taxe_bureaux_facturee"), ("D23", "dividende_smf"),
                   ("C23", "taux_qp_smf"), ("E24", "subventions_exo"), ("E25", "rmf"), ("E26", "ci_famille"), ("E27", "cir"),
                   ("E28", "divers_ded_1"), ("E29", "divers_ded_2"), ("E30", "divers_ded_3"), ("C45", "soumise_is"), ("C46", "taux_reduit")):
        put("Résultat_Fiscal", adr, f.get(k))
    for adr in ("E8", "E9", "E10"):
        put("Résultat_Fiscal", adr, None)
    put("Résultat_Fiscal", "D36", f.get("deficit_anterieur") or None)

    # Emprunts (lignes de la liste triée des 164)
    c164 = sorted((l["compte"] for l in d["balance"] if l["compte"].startswith("164")), key=str.casefold)
    ws("Caché_Emprunts").Range("F10:H18").ClearContents()
    for k, compte in enumerate(c164):
        e = s["emprunts"][compte]
        for cl, champ in (("F", "crdu_n_plus_1"), ("G", "crdu_n_plus_5"), ("H", "souscrit")):
            put("Caché_Emprunts", f"{cl}{10 + k}", e[champ])

    put("Liasse_fiscale", "E37", bool(s["liasse"]["mono_etablissement"]))
    put("Liasse_fiscale", "E49", s["liasse"]["siren_cabinet"])

    t = s["tns"]
    for adr, k in (("C11", "mois_cloture"), ("C12", "pass"), ("C15", "nom"), ("C18", "per"), ("C19", "plafond_retraite"),
                   ("C21", "prevoyance"), ("C22", "plafond_prevoyance"), ("C24", "dividendes_cotis"), ("C25", "csg_non_deductible"),
                   ("C26", "csg_deductible"), ("C27", "cotisations_payees"), ("C28", "cotisations_remboursees"),
                   ("C29", "avantages_nature"), ("C30", "remuneration"), ("C42", "cotisations_urssaf")):
        put("Caché_Provision_TNS", adr, t[k])
    put("Caché_Driti_PAMC", "F12", s["pamc"]["ca_total"])
    put("Caché_Driti_PAMC", "F14", s["pamc"]["honoraires_snir"])
    dm = s["driti_manuelle"]
    for adr, k in (("F33", "remuneration"), ("F35", "avantages_nature"), ("F37", "madelins_excedent"), ("F39", "csg_non_deductible"),
                   ("F43", "cotisations_payees"), ("F45", "csg_appelee"), ("F49", "cotisations_remboursees"),
                   ("F53", "per_deductible"), ("F55", "prevoyance_deductible"), ("F59", "dividendes_cotis")):
        put("Driti_TNS_Manuelle", adr, dm[k])
    put("IFU_Distrib_N_1", "G6", s["ifu"]["associe_n1"])
    put("Caché_IFU_Distrib_N", "G6", s["ifu"]["associe_n"])

    # Journal de paie SILAE
    so = ws("Cadrage_Social_SILAE")
    so.Range("B7:L79").ClearContents()
    for k, l in enumerate(d["journal_paie"]):
        r = 7 + k
        so.Range(f"B{r}").Value = l["code"] or None
        so.Range(f"C{r}").Value = l["libelle"]
        so.Range(f"G{r}").Value = l["salarial"] or None
        so.Range(f"J{r}").Value = l["patronal"] or None
    for k, e in enumerate(["Brut", "Avantages en nature", "Indemnités de rupture", "Cfp + taxe d'apprentissage",
                           "Prévoyance + mutuelle", "Retraite", "Tickets restaurants", "Cotisations URSSAF"]):
        so.Range(f"S{7 + k}").Value = s["social"]["compta"][e]
    so.Range("R15").Value = s["social"]["provision_cp"]
    so.Range("S15").Value = None

    m = s["mail"]
    put("Mail_bilan", "C34", bool(m["inclure_is"]))
    put("Mail_bilan", "C35", bool(m["inclure_tva"]))
    put("Mail_bilan", "C36", bool(m["inclure_flat_tax"]))


# ---------------------------------------------------------------------------------------------------------------
# Comparaison
# ---------------------------------------------------------------------------------------------------------------
class Comparateur:
    def __init__(self, wb):
        self.wb, self.ok, self.ko, self.connus, self.cache = wb, 0, [], [], {}
        self.feuilles_connues = {}  # feuille -> raison (limites de taille de l'Excel)

    def lire(self, feuille, adr):
        cle = (feuille, adr)
        if cle not in self.cache:
            self.cache[cle] = self.wb.Worksheets(feuille).Range(adr).Value2
        return self.cache[cle]

    def bloc(self, feuille, plage):
        v = self.wb.Worksheets(feuille).Range(plage).Value2
        return v if isinstance(v, tuple) else ((v,),)

    @staticmethod
    def _egal(x, y, tol):
        if isinstance(x, int) and x < -2146820000:  # valeur d'erreur Excel (#DIV/0!, #N/A...)
            x = "#ERREUR"
        if y is None and x in (None, "", 0, False):
            return True
        if isinstance(y, bool) or isinstance(x, bool):
            return bool(x) == bool(y)
        if isinstance(y, (int, float)):
            if x in (None, ""):
                x = 0.0
            try:
                return abs(float(x) - float(y)) <= tol
            except (TypeError, ValueError):
                return False
        if isinstance(x, float) and isinstance(y, str) and len(y) == 10 and y[2] == "/" and 20000 < x < 80000:
            return depuis_serie(x).strftime("%d/%m/%Y") == y
        return str(x if x is not None else "").strip() == str(y if y is not None else "").strip()

    def verifier(self, feuille, adr, attendu, libelle, tol=0.01, connu=None, valeur_excel=None):
        x = self.lire(feuille, adr) if valeur_excel is None else valeur_excel
        if self._egal(x, attendu, tol):
            self.ok += 1
            return
        ligne = {"feuille": feuille, "cellule": adr, "libelle": libelle, "excel": x if not hasattr(x, "year") else str(x),
                 "moteur": attendu}
        connu = connu or self.feuilles_connues.get(feuille)
        if connu:
            ligne["raison"] = connu
            self.connus.append(ligne)
        else:
            self.ko.append(ligne)


def comparer(wb, d, r):
    c = Comparateur(wb)
    v = c.verifier
    nb_70 = sum(1 for x in r["balance"]["lignes"] if x["compte"].startswith("70"))
    if nb_70 > 26:
        raison = f"Limite n°10 : Cadrage_CA ne peut lister que 26 comptes 70 (ici {nb_70}) ; la liste déborde (#EPARS!)"
        c.feuilles_connues.update({"Cadrage_CA": raison, "TVA_Cadrage_Flux": raison, "Liasse_fiscale": raison})
    s = d["saisies"]
    bg = r["balance"]["lignes"]

    # --- Balance comparative
    v("Bal_Comparative", "E4", r["balance"]["resultat_n"], "Résultat N")
    v("Bal_Comparative", "F4", r["balance"]["resultat_n1"], "Résultat N-1")
    v("Bal_Comparative", "E3", r["balance"]["libelle_n"], "Libellé résultat N")
    connu_qp_lib = ("Correction n°1 : 655 et 755 ont chacun leur rubrique (un seul libellé dans l'Excel)"
                    if any(x["compte"][:3] in ("655", "755") for x in bg) else None)
    blocs = c.bloc("Bal_Comparative", f"C7:R{6 + len(bg) + 1}")
    for k, l in enumerate(bg):
        row = blocs[k]
        for j, (cle, tol) in enumerate((("compte", 0), ("libelle", 0), ("n", .01), ("n1", .01), ("var", .01), ("var_pct", 1e-6))):
            v("Bal_Comparative", f"{'CDEFGH'[j]}{7 + k}", l[cle], f"Balance {l['compte']} {cle}", tol, valeur_excel=row[j] if row[j] is not None else "")
        v("Bal_Comparative", f"P{7 + k}", l["sig"] or False, f"Rubrique SIG {l['compte']}", valeur_excel=row[13] if row[13] is not None else False,
          connu=connu_qp_lib if l["compte"][:3] in ("655", "755") else None)
    v("Bal_Comparative", f"C{7 + len(bg)}", None, "Fin de la balance (pas de ligne en trop)")

    # --- Feuilles de cycle
    feuilles = {"attente": "Comptes_Attente", "treso": "Comptes_Tréso", "courants": "Comptes_Courants",
                "emprunts": "Comptes_Emprunts", "social": "Comptes_Social", "etat": "Comptes_Etat", "ce": "Comptes_CE",
                "immos": "Comptes_Immos", "cp": "Comptes_CP"}
    for cy in r["cycles"]:
        f = feuilles[cy["cle"]]
        lignes = cy["lignes"]
        if not lignes:
            v(f, "B7", "Pas de compte", f"{f} vide")
            continue
        b = c.bloc(f, f"B7:F{6 + len(lignes) + 1}")
        for k, l in enumerate(lignes):
            for j, cle in enumerate(("compte", "libelle", "n", "n1", "var")):
                v(f, f"{'BCDEF'[j]}{7 + k}", l[cle], f"{f} {l['compte']} {cle}", valeur_excel=b[k][j] if b[k][j] is not None else "")
        v(f, f"B{7 + len(lignes)}", None, f"{f} : pas de ligne en trop", valeur_excel=b[len(lignes)][0])

    # --- SIG
    lignes_sig = {"ca": 7, "ventes_march": 9, "cout_march": 58, "marge_commerciale": 107, "prod_vendue": 109, "prod_stockee": 158,
                  "prod_immo": 207, "production": 256, "marge_et_production": 258, "autres_conso_marge": 260, "marge_globale": 309,
                  "autres_conso_tiers": 311, "valeur_ajoutee": 385, "subventions": 387, "impots_taxes": 436, "personnel": 485,
                  "ebe": 534, "reprises": 536, "dotations": 585, "qp_subv": 634, "produits_cessions": 683, "vnc_cedees": 732,
                  "autres_produits": 781, "autres_charges": 830, "rex": 879, "qp_commun_produit": 881, "qp_commun_charge": 930,
                  "produits_fin": 979, "charges_fin": 1028, "rcai": 1077, "produits_exc": 1079, "charges_exc": 1128, "rexc": 1177,
                  "participation": 1183, "impots_benef": 1232, "resultat": 1281}
    qp = any(x["compte"][:3] in ("655", "755") for x in bg)
    connu_qp = "Correction n°1 : l'Excel compte deux fois la quote-part des opérations faites en commun (655/755)" if qp else None
    for l in r["sig"]["lignes"]:
        ligne = lignes_sig[l["cle"]]
        cn = connu_qp if ligne >= 881 and l["cle"] not in ("produits_fin", "charges_fin", "produits_exc", "charges_exc", "rexc", "participation", "impots_benef") else None
        v("SIG", f"E{ligne}", l["n"], f"SIG N {l['libelle']}", connu=cn)
        v("SIG", f"G{ligne}", l["n1"], f"SIG N-1 {l['libelle']}", connu=cn)
        v("SIG", f"F{ligne}", l["pct_n"], f"SIG %CA N {l['libelle']}", 1e-6, connu=cn)
        v("SIG", f"I{ligne}", l["var"], f"SIG variation {l['libelle']}", connu=cn)
        if l["detail"]:
            # L'Excel affiche le détail en -solde quelle que soit la rubrique ; le moteur, dans le sens de la rubrique.
            rubrique = next(x[3] for x in sig_module.LIGNES if x[0] == l["cle"])
            facteur = 1 if rubrique in R.SIG_BLOCS_PRODUITS else -1
            if not (qp and ligne in (881, 930)):
                b = c.bloc("SIG", f"D{ligne + 1}:H{ligne + len(l['detail'])}")
                for k, dl in enumerate(l["detail"]):
                    v("SIG", f"D{ligne + 1 + k}", f"{dl['compte']} - {dl['libelle']}", "SIG détail compte", valeur_excel=b[k][0])
                    v("SIG", f"E{ligne + 1 + k}", facteur * dl["n"], f"SIG détail {dl['compte']} N", valeur_excel=b[k][1])
                    v("SIG", f"G{ligne + 1 + k}", facteur * dl["n1"], f"SIG détail {dl['compte']} N-1", valeur_excel=b[k][3])
    v("Bal_Comparative", "H4", "OK" if abs(r["sig"]["n"]["resultat"] - r["balance"]["resultat_n"]) < 0.005 else
      round(r["balance"]["resultat_n"] - r["sig"]["n"]["resultat"], 2), "Contrôle résultat SIG / balance", connu=connu_qp)

    # --- Capitaux
    cap = r["capitaux"]
    for k, l in enumerate(cap["lignes"]):
        v("Capitaux", f"D{7 + k}", l["n1"], f"Capitaux N-1 {l['libelle']}")
        v("Capitaux", f"E{7 + k}", l["var"], f"Capitaux var {l['libelle']}")
        v("Capitaux", f"F{7 + k}", l["n"], f"Capitaux N {l['libelle']}")
    v("Capitaux", "G16", cap["lignes"][9]["alerte"], "Alerte 120")
    v("Capitaux", "G17", cap["lignes"][10]["alerte"], "Alerte 129")
    aff = cap["affectation"]
    for adr, k in (("D22", "resultat_n1"), ("D23", "reserve_legale"), ("D24", "reserve_statutaire"), ("D25", "reserves_reglementees"),
                   ("D26", "autres_reserves"), ("D27", "report_a_nouveau"), ("D28", "a_detailler")):
        v("Capitaux", adr, aff[k], f"Affectation N-1 {k}")
    for colx, k in (("D", "continuite_n1"), ("E", "continuite_n")):
        for ligne, champ in ((36, "hors_resultat"), (37, "resultat"), (38, "total"), (39, "capital"), (40, "rapport")):
            v("Capitaux", f"{colx}{ligne}", cap[k][champ], f"Continuité {k} {champ}", 1e-6 if champ == "rapport" else .01)

    # --- AGO N-1 (dividendes votés en N-1)
    a1 = r["ago_n1"]
    v("AGO_N_1", "D6", a1["dividendes"], "AGO N-1 dividendes")
    v("AGO_N_1", "D7", a1["total_parts"], "AGO N-1 parts")
    for j, a in enumerate(a1["associes"]):
        cl = COLS_ASSOC[j]
        connu = ("Correction n°4 : l'Excel applique 40 % de cotisations TNS aux associés 2 à 6 (25 % au 1er)"
                 if j > 0 and abs(a["base_cotis"]) > 0.005 else None)
        for ligne, champ in ((13, "pct"), (14, "affecte"), (16, "retenu"), (19, "base_ps"), (20, "base_cotis"), (21, "ps"),
                             (22, "precompte"), (23, "retenue"), (24, "retenue_pct"), (25, "net"), (26, "cotis_tns"),
                             (27, "economie_is"), (28, "cout"), (29, "cout_pct")):
            v("AGO_N_1", f"{cl}{ligne}", a[champ], f"AGO N-1 {a['nom']} {champ}", 1e-6 if champ.endswith("pct") else .01,
              connu=connu if ligne >= 26 else None)

    # --- AGO N
    ag = r["ago_n"]
    for k, l in enumerate(ag["lignes"]):
        v("AGO_N", f"D{7 + k}", l["n1"], f"AGO N-1 {l['libelle']}")
        v("AGO_N", f"E{7 + k}", l["n"], f"AGO N {l['libelle']}")
    v("AGO_N", "D19", ag["situation_n1"]["resultat"], "AGO résultat N-1")
    v("AGO_N", "E19", ag["situation_n"]["resultat"], "AGO résultat N")
    v("AGO_N", "D20", ag["situation_n1"]["total"], "AGO capitaux N-1")
    v("AGO_N", "E20", ag["situation_n"]["total"], "AGO capitaux N")
    v("AGO_N", "D21", ag["situation_n1"]["rapport"], "AGO rapport N-1", 1e-6)
    v("AGO_N", "E21", ag["situation_n"]["rapport"], "AGO rapport N", 1e-6)
    af = ag["affectation"]
    v("AGO_N", "D24", r["balance"]["resultat_n"], "AGO résultat à affecter")
    v("AGO_N", "D25", af["distribuable"], "AGO distribuable")
    v("AGO_N", "C25", af["libelle_distribuable"], "AGO libellé distribuable")
    v("AGO_N", "F9", af["signal_reserve_legale"], "AGO signal réserve légale")
    v("AGO_N", "D26", af["reserve_legale"], "AGO réserve légale à doter")
    v("AGO_N", "D32", af["ran_crediteur"], "AGO RAN créditeur")
    v("AGO_N", "D33", af["ran_debiteur"], "AGO RAN débiteur")
    rl = af["reserve_legale_calcul"]
    for adr, k in (("B1", "theorique"), ("B2", "actuelle"), ("B3", "reste"), ("B4", "cinq_pourcent"), ("B6", "a_doter")):
        v("Caché_Données", adr, rl[k], f"Réserve légale {k}")
    v("AGO_N", "F25", af["distribuable"], "AGO reste progressif 1")
    for k, cle in enumerate(["reserve_legale", "reserve_statutaire", "reserves_reglementees", "autres_reserves", "dividendes",
                             "compte_courant", "ran_crediteur", "ran_debiteur"]):
        v("AGO_N", f"F{26 + k}", af["reste_progressif"][cle], f"AGO reste après {cle}")
    sub = any(abs(l["n"]) > 0.005 for l in ag["lignes"] if l["racine"] in ("13", "14"))
    connu_ag = "Correction n°8 : l'Excel oublie les comptes 13 et 14 dans la situation après AG" if sub else None
    for k, l in enumerate(ag["lignes"]):
        cn = connu_ag if l["racine"] in ("13", "14") else None
        if k < 8:
            v("AGO_N", f"H{7 + k}", l["apres_ag"], f"AGO après AG {l['libelle']}", connu=cn)
        v("AGO_N", f"G{7 + k}", l["variation_ag"], f"AGO variation AG {l['libelle']}", connu=cn)
    v("AGO_N", "H20", ag["apres_ag"]["total"], "AGO capitaux après AG", connu=connu_ag)
    v("AGO_N", "H21", ag["apres_ag"]["rapport"], "AGO rapport après AG", 1e-6, connu=connu_ag)
    v("AGO_N", "G20", ag["apres_ag"]["variation_total"], "AGO variation totale", connu=connu_ag)
    rep = ag["repartition"]
    v("AGO_N", "D35", rep["dividendes"], "AGO dividendes à répartir")
    v("AGO_N", "D36", rep["total_parts"], "AGO parts")
    for j, a in enumerate(rep["associes"]):
        cl = COLS_ASSOC[j]
        for ligne, champ in ((42, "pct"), (43, "affecte"), (45, "retenu"), (47, "qp"), (48, "base_ps"), (49, "base_cotis"),
                             (50, "ps"), (51, "precompte"), (52, "retenue"), (53, "retenue_pct"), (54, "net"), (56, "cotis_tns"),
                             (57, "economie_is"), (58, "cout"), (59, "cout_pct")):
            v("AGO_N", f"{cl}{ligne}", a[champ], f"AGO N {a['nom']} {champ}", 1e-6 if champ.endswith("pct") else .01)

    # --- Cadrage du CA
    ca = r["cadrage_ca"]
    v("Cadrage_CA", "D33", ca["total_ca"], "Total CA")
    for (cle, _), cl in zip(R.TAUX_CA, COLS_CA):
        x = ca["colonnes"][cle]
        for ligne, champ in ((43, "ht_realise"), (46, "corr_debut"), (50, "corr_fin"), (54, "debours_total"), (59, "ca_facture"),
                             (60, "tva_ca"), (61, "autres"), (62, "tva_autres"), (63, "facturation_ttc"), (69, "solde_client_n1"),
                             (75, "solde_client_n"), (85, "corrections_ht"), (86, "corrections_ttc")):
            if cle == "0" and ligne in (85, 86):
                continue  # pas de formule dans la colonne 0 % de l'Excel
            v("Cadrage_CA", f"{cl}{ligne}", x[champ], f"Cadrage CA {cle} {champ}")
    for k, x in enumerate(ca["controles"]):
        v("Cadrage_CA", f"C{78 + k}", x["n1"], f"Cadrage CA {x['racine']} N-1")
        v("Cadrage_CA", f"D{78 + k}", x["n"], f"Cadrage CA {x['racine']} N")
        v("Cadrage_CA", f"E{78 + k}", x["ecart_n1"], f"Cadrage CA écart {x['racine']} N-1")
        v("Cadrage_CA", f"F{78 + k}", x["ecart_n"], f"Cadrage CA écart {x['racine']} N")

    # --- TVA : récapitulatif mois par mois
    recap = r["tva"]["recap"]
    lignes_recap = {"A1": 11, "A2": 12, "A3": 13, "A4": 14, "B2": 15, "B5": 16, "E1": 18, "E2": 19, "E3": 20, "E6": 21, "F1": 22,
                    "F6": 23, "F7": 24, "F8": 25, "08": 28, "08_taxe": 29, "09": 30, "09_taxe": 31, "9B": 32, "9B_taxe": 33,
                    "10": 34, "10_taxe": 35, "15": 36, "5B": 37, "16": 38, "17": 39, "18": 40, "19": 43, "20": 44, "21": 45,
                    "22": 46, "2C": 47, "23": 48, "25": 51, "27": 53, "28": 55}
    for k, colr in enumerate(recap["colonnes"]):
        cl = col("F", k)
        v("TVA_Récap_Interne", f"{cl}7", colr["libelle"], f"TVA période {k + 1}",
          valeur_excel=(depuis_serie(c.lire("TVA_Récap_Interne", f"{cl}7")).strftime("%m-%Y") if isinstance(c.lire("TVA_Récap_Interne", f"{cl}7"), float) else c.lire("TVA_Récap_Interne", f"{cl}7")))
        for code, ligne in lignes_recap.items():
            v("TVA_Récap_Interne", f"{cl}{ligne}", colr["valeurs"][code], f"TVA {colr['libelle']} ligne {code}")
    v("TVA_Récap_Interne", "AB55", recap["totaux"]["28"], "TVA total ligne 28")

    # --- TVA : cadrage sur le solde
    so = r["tva"]["solde"]
    for (cle, _), cl in zip(R.TAUX_CA[:4], COLS_CA[:4]):
        x = so["colonnes"][cle]
        for ligne, champ in ((7, "solde_client_n1"), (8, "tva_theorique_n1"), (9, "tva_reelle_n1"), (10, "ecart_n1"), (11, "signal_n1"),
                             (12, "ecart_ht_n1"), (13, "signal_ht_n1"), (15, "solde_client_n"), (16, "tva_theorique_n"),
                             (17, "tva_reelle_n"), (18, "ecart_n"), (19, "signal_n"), (20, "ecart_ht_n"), (21, "signal_ht_n")):
            v("TVA_Cadrage_Solde", f"{cl}{ligne}", x[champ], f"TVA solde {cle} {champ}")

    # --- TVA : cadrage sur les flux
    fl = r["tva"]["flux"]
    connu_flux = "Correction n°2 : l'Excel neutralise l'écart après régularisation des colonnes sans TVA (0 %, INTRA, EXTRA)"
    for (cle, _), cl in zip(R.TAUX_CA, COLS_FLUX):
        x = fl["colonnes"][cle]
        taxe = cle in R.TAUX_CA_TAXES
        for ligne, champ in ((7, "solde_client_n1"), (8, "facturation_ttc"), (9, "corrections_ttc"), (10, "solde_client_n"),
                             (11, "encaissements"), (12, "base_theorique")):
            v("TVA_Cadrage_Flux", f"{cl}{ligne}", x[champ], f"TVA flux {cle} {champ}")
        if taxe:
            v("TVA_Cadrage_Flux", f"{cl}19", x["ecart_solde_n"], f"TVA flux {cle} écart solde N")
            v("TVA_Cadrage_Flux", f"{cl}20", x["ecart_solde_n1"], f"TVA flux {cle} écart solde N-1")
            v("TVA_Cadrage_Flux", f"{cl}13", x["base_declaree"], f"TVA flux {cle} base déclarée")
            v("TVA_Cadrage_Flux", f"{cl}14", x["ecart"], f"TVA flux {cle} écart")
            v("TVA_Cadrage_Flux", f"{cl}17", x["ecart_apres_regul"], f"TVA flux {cle} écart après régul")
            v("TVA_Cadrage_Flux", f"{cl}21", x["difference"], f"TVA flux {cle} différence à justifier")
            v("TVA_Cadrage_Flux", f"{cl}22", x["signal_difference"], f"TVA flux {cle} signalisation")
        else:
            v("TVA_Cadrage_Flux", f"{cl}14", x["ecart"], f"TVA flux {cle} écart")
            v("TVA_Cadrage_Flux", f"{cl}17", x["ecart_apres_regul"], f"TVA flux {cle} écart après régul", connu=connu_flux)
    # La base déclarée doit aussi égaler la somme des mois (contrôle indépendant des totaux de l'Excel)
    nb = len(recap["colonnes"])
    def somme_excel(ligne):
        return sum((c.lire("TVA_Récap_Interne", f"{col('F', k)}{ligne}") or 0) for k in range(nb))
    v("TVA_Cadrage_Flux", "D13", fl["colonnes"]["20"]["base_declaree"], "Base 20 % déclarée = somme des mois de l'Excel",
      valeur_excel=somme_excel(28) - somme_excel(15) - somme_excel(14) - somme_excel(13) - somme_excel(12))
    v("TVA_Cadrage_Flux", "E13", fl["colonnes"]["10"]["base_declaree"], "Base 10 % déclarée = somme des mois de l'Excel", valeur_excel=somme_excel(32))
    v("TVA_Cadrage_Flux", "G13", fl["colonnes"]["5,5"]["base_declaree"], "Base 5,5 % déclarée = somme des mois de l'Excel", valeur_excel=somme_excel(30))

    # --- Résultat fiscal
    rf = r["fiscal"]
    ded_ant = s["fiscal"].get("deficit_anterieur") or 0
    connu_def = ("Correction n°6 : l'Excel impute le déficit antérieur au-delà du bénéfice"
                 if ded_ant and 0 < rf["avant_imputation"] < min(ded_ant, 1_000_000) else None)
    for adr, val, lib, cn in (("D7", rf["benefice"], "Bénéfice", None), ("D8", rf["reintegrations"]["is"], "IS", None),
                              ("D9", rf["reintegrations"]["amendes"], "Amendes", None), ("D10", rf["reintegrations"]["dons"], "Dons", None),
                              ("D19", rf["total_reintegrations"], "Réintégrations", None), ("E21", rf["deficit"], "Déficit", None),
                              ("E23", rf["deductions"]["smf"], "Dividende SMF", None), ("E32", rf["total_deductions"], "Déductions", None),
                              ("D34", rf["avant_imputation"], "Résultat avant imputation", None),
                              ("D39", rf["deficit_impute"], "Déficit imputé", connu_def), ("D41", rf["deficit_restant"], "Déficit restant", connu_def),
                              ("D43", rf["apres_imputation"], "Résultat fiscal", connu_def), ("C48", rf["taux_reduit"], "Taux réduit", None),
                              ("C49", rf["taux_normal"], "Taux normal", None), ("D48", rf["plafond_taux_reduit"], "Plafond taux réduit", None),
                              ("D49", rf["base_taux_normal"], "Base taux normal", connu_def), ("E48", rf["is_taux_reduit"], "IS 15 %", connu_def),
                              ("E49", rf["is_taux_normal"], "IS 25 %", connu_def), ("E50", rf["is_total"], "IS total", connu_def),
                              ("E52", rf["resultat_net_ajuste"], "Résultat net ajusté", connu_def)):
        v("Résultat_Fiscal", adr, val, f"Fiscal {lib}", connu=cn)

    # --- Emprunts et liasse
    em = r["emprunts"]
    for k, l in enumerate(em["lignes"]):
        v("Caché_Emprunts", f"D{10 + k}", l["crdu_n1"], f"Emprunt {l['compte']} N-1")
        v("Caché_Emprunts", f"E{10 + k}", l["crdu_n"], f"Emprunt {l['compte']} N")
    for adr, val in (("B24", em["souscrit"]), ("C24", em["rembourse"]), ("D24", em["montant_brut"]), ("E24", em["a_un_an"]),
                     ("F24", em["un_a_cinq_ans"]), ("G24", em["plus_de_cinq_ans"])):
        v("Caché_Emprunts", adr, val, f"Emprunts {adr}")
    li = r["liasse"]
    for adr, val, lib, cn in (("E7", li["ca"]["march_france"], "CA marchandises France", None),
                              ("E8", li["ca"]["march_inter"], "CA marchandises inter", None),
                              ("E9", li["ca"]["services_france"], "CA services France", None),
                              ("E10", li["ca"]["services_inter"], "CA services inter", None), ("E11", li["ca"]["total"], "CA total", None),
                              ("F11", li["ca"]["balance"], "CA balance", None), ("G11", li["ca"]["ecart"], "Écart CA", None),
                              ("E13", li["charges_exc"], "Charges exc.", None), ("E14", li["produits_exc"], "Produits exc.", None),
                              ("E16", li["emprunts"]["souscrit"], "Souscrit", None), ("E17", li["emprunts"]["rembourse"], "Remboursé", None),
                              ("E18", li["emprunts"]["montant_brut"], "Montant brut", None), ("E22", li["emprunts"]["total"], "Total emprunts", None),
                              ("D24", li["resultat"]["libelle"], "Libellé résultat", None), ("E24", li["resultat"]["comptable"], "Résultat comptable", None),
                              ("E27", li["resultat"]["deficit_impute"], "Déficit imputé", connu_def),
                              ("E28", li["resultat"]["fiscal"], "Résultat fiscal", connu_def), ("E30", li["deficit_reportable"], "Déficit reportable", connu_def),
                              ("E32", li["dividendes_distribues"], "Dividendes", None), ("E33", li["prelevements_reserves"], "Prélèvements réserves", None),
                              ("E35", li["tva_collectee"], "TVA collectée", None), ("E38", li["cvae"]["ca"], "CA CVAE", None),
                              ("F37", li["cvae"]["message_1330"], "1330", None), ("F38", li["cvae"]["message_1329"], "1329", None),
                              ("E44", li["frais_2067"]["remunerations"], "Rémunérations", None), ("E45", li["frais_2067"]["deplacements"], "Déplacements", None),
                              ("E46", li["frais_2067"]["restaurants"], "Restaurants", None), ("E47", li["frais_2067"]["cadeaux"], "Cadeaux", None),
                              ("F45", li["frais_2067"]["message_deplacements"], "Seuil déplacements", None),
                              ("F46", li["frais_2067"]["message_restaurants"], "Seuil restaurants", None),
                              ("F47", li["frais_2067"]["message_cadeaux"], "Seuil cadeaux", None),
                              ("E57", li["edi"]["resultat_avant_is"], "EDI résultat avant IS", connu_qp),
                              ("E58", li["edi"]["resultat_fiscal"], "EDI résultat fiscal", connu_def), ("E59", li["edi"]["is"], "EDI IS", connu_def),
                              ("E60", li["edi"]["resultat_net"], "EDI résultat net", None)):
        v("Liasse_fiscale", adr, val, f"Liasse {lib}", connu=cn)

    # --- TNS
    p = r["tns"]["provision"]
    for adr, k in (("C10", "annee"), ("C13", "plancher"), ("C14", "plafond"), ("C20", "excedent_per"), ("C23", "excedent_prevoyance"),
                   ("C33", "revenu_fiscal"), ("C34", "base_super_brut"), ("C35", "abattement"), ("C36", "base_sociale"),
                   ("C37", "cotisations_reglees"), ("C38", "remuneration_simulateur"), ("C43", "cfp"), ("C44", "csg_crds"),
                   ("C45", "csg_deductible_calc"), ("C46", "csg_non_deductible_calc"), ("C47", "cotisations_totales"),
                   ("C48", "taux_revenu_social"), ("C49", "taux_revenu_net"), ("C51", "csg_urssaf"), ("C52", "reconciliation_urssaf"),
                   ("E27", "cotisations_payees_hors_csg")):
        v("Caché_Provision_TNS", adr, p[k], f"TNS {k}", 1e-6 if k.startswith("taux") else .01)
    dr = r["tns"]["driti"]
    for adr, k in (("F12", "1GB"), ("F20", "DSCA"), ("F22", "DSDA"), ("F24", "DSEA"), ("F26", "DSAA"), ("F39", "madelins_excedent"),
                   ("F47", "csg_appelee"), ("F55", "per_deductible"), ("F57", "prevoyance_deductible")):
        v("Caché_Driti_TNS", adr, dr[k], f"DRITI {k}")
    pa = r["tns"]["pamc"]
    for adr, k in (("F16", "quote_part"), ("F18", "revenus_nets"), ("F46", "DSCS"), ("F48", "DSGA"), ("F50", "DSCR"), ("F52", "DSAR"),
                   ("F54", "DSCM")):
        v("Caché_Driti_PAMC", adr, pa[k], f"PAMC {k}", 1e-6 if k == "quote_part" else .01)
    ec = r["tns"]["ecritures"]
    v("Caché_Ecritures_TNS", "E15", ec["lignes"][0]["debit"], "Écriture cotisations")
    v("Caché_Ecritures_TNS", "F16", ec["lignes"][1]["credit"], "Écriture organisme")
    v("Caché_Ecritures_TNS", "E17", ec["lignes"][2]["debit"], "Écriture rémunération")
    v("Caché_Ecritures_TNS", "G20", ec["ecart"], "Écritures équilibrées")
    dm = r["tns"]["driti_manuelle"]
    for adr, k in (("F10", "1GB"), ("F18", "DSCA"), ("F20", "DSDA"), ("F22", "DSEA"), ("F24", "DSAA")):
        v("Driti_TNS_Manuelle", adr, dm[k], f"DRITI manuelle {k}")

    # --- IR et IFU
    irr = r["ir"]
    for f, x in (("IFU_Distrib_N_1", irr["ifu_n1"]), ("Caché_IFU_Distrib_N", irr["ifu_n"])):
        for adr, k in (("H13", "2DC"), ("H15", "2CG"), ("H17", "2BH"), ("H19", "2CK")):
            v(f, adr, x[k] if x["trouve"] else "Non trouvé", f"{f} {k}")
    el = irr["elements"]
    v("Aller à", "K20", el["bic"]["valeur"], "Revenu BIC", connu=connu_def)
    v("Aller à", "K21", el["lmp"]["valeur"], "Revenu LMP", connu=connu_def)
    v("Aller à", "K22", el["lmnp"]["valeur"], "Revenu LMNP", connu=connu_def)
    rc = irr["recap"]
    connu_ir = "Correction n°3 : l'Excel reporte l'indemnité RF en 5ND" if abs(el["indemnite_rf"]["valeur"] - el["indemnite_micro"]["valeur"]) > 0.005 else None
    for adr, k, cn in (("F13", "4BE", None), ("F27", "5ND", connu_ir), ("F37", "5KC", connu_def), ("F39", "bic_revenus", connu_def),
                       ("F41", "lmp_revenus", connu_def), ("F43", "5KF", connu_def), ("F45", "bic_deficits", connu_def),
                       ("F47", "lmp_deficits", connu_def), ("F57", "5NC", connu_def), ("F59", "5NF", connu_def),
                       ("F67", "5HY", connu_def), ("F75", "5NA", connu_def), ("F77", "5NY", connu_def)):
        v("Récap_IR", adr, rc[k], f"Récap IR {k}", connu=cn)

    # --- Social
    for k, x in enumerate(r["social"]["rapprochement"]):
        v("Cadrage_Social_SILAE", f"R{7 + k}", x["paie"] if x["paie"] is not None else "Non trouvé", f"SILAE paie {x['element']}")
        if k < 8:
            v("Cadrage_Social_SILAE", f"T{7 + k}", x["ecart"], f"SILAE écart {x['element']}")

    # --- Mail bilan
    ml = r["mail"]
    lignes_mail = {"ca": 7, "marge_globale": 8, "marge_globale_pct": 9, "personnel": 10, "personnel_pct": 11, "ebe": 12, "ebe_pct": 13,
                   "rcai": 14, "rcai_pct": 15, "is": 16, "resultat": 17, "resultat_pct": 18, "tresorerie": 19, "autre_tresorerie": 20,
                   "stocks": 21, "clients": 22, "fournisseurs": 23, "tva": 24, "bfre": 25, "is_solde": 26, "capitaux_propres": 27,
                   "capitaux_sur_capital": 28}
    for g in ml["groupes"]:
        for l in g["lignes"]:
            ligne = lignes_mail[l["cle"]]
            cn = connu_qp if l["cle"] in ("rcai", "rcai_pct", "resultat", "resultat_pct") else None
            tol = 1e-6 if l["pourcentage"] else .01
            v("Mail_bilan", f"E{ligne}", l["n"], f"Mail N {l['libelle']}", tol, connu=cn)
            v("Mail_bilan", f"F{ligne}", l["n1"], f"Mail N-1 {l['libelle']}", tol, connu=cn)
            if "var" in l:
                v("Mail_bilan", f"G{ligne}", l["var"], f"Mail variation {l['libelle']}", connu=cn)
                v("Mail_bilan", f"H{ligne}", l["var_pct"], f"Mail variation % {l['libelle']}", 1e-6, connu=cn)
    for k, e in enumerate(ml["echeances"]):
        v("Mail_bilan", f"E{34 + k}", e["montant"], f"Mail échéance {e['libelle']}")
        v("Mail_bilan", f"F{34 + k}", e["echeance"], f"Mail date {e['libelle']}")
    for k, dv in enumerate(ml["dividendes"]):
        v("Mail_bilan", f"C{42 + k}", dv["associe"], "Mail dividende associé")
        v("Mail_bilan", f"D{42 + k}", dv["brut"], "Mail dividende brut")
        v("Mail_bilan", f"E{42 + k}", dv["precompte_ir"], "Mail précompte IR")
        v("Mail_bilan", f"F{42 + k}", dv["precompte_ps"], "Mail précompte PS")
        v("Mail_bilan", f"G{42 + k}", dv["virement"], "Mail virement")
    return c


def executer(modele, graines, options=None):
    import pythoncom
    import win32com.client
    options = options or {}
    pythoncom.CoInitialize()
    xl = win32com.client.DispatchEx("Excel.Application")
    xl.Visible = False
    xl.DisplayAlerts = False
    xl.ScreenUpdating = False
    xl.EnableEvents = False
    xl.AskToUpdateLinks = False
    rapport = []
    dossier_tmp = tempfile.mkdtemp(prefix="parite_bilan_")
    try:
        for g in graines:
            d = scenarios.dossier(g, **options.get(g, {}))
            r = calculer(d)
            copie = os.path.join(dossier_tmp, f"parite_{g}.xlsm")
            shutil.copyfile(modele, copie)
            t0 = time.time()
            wb = xl.Workbooks.Open(copie, UpdateLinks=0)
            xl.Calculation = -4135  # manuel pendant l'écriture
            ecrire(wb, d)
            xl.CalculateFull()
            duree_excel = time.time() - t0
            t1 = time.time()
            calculer(d)
            duree_moteur = time.time() - t1
            c = comparer(wb, d, r)
            wb.Close(SaveChanges=False)
            rapport.append({"graine": g, "options": options.get(g, {}), "comptes": len(r["balance"]["lignes"]), "verifies": c.ok + len(c.ko) + len(c.connus),
                            "identiques": c.ok, "ecarts": c.ko, "ecarts_connus": c.connus,
                            "duree_excel_s": round(duree_excel, 1), "duree_moteur_ms": round(duree_moteur * 1000, 1)})
            print(f"Scénario {g} : {c.ok} identiques, {len(c.ko)} écarts, {len(c.connus)} écarts connus "
                  f"(Excel {duree_excel:.1f} s, moteur {duree_moteur * 1000:.0f} ms)", flush=True)
            for e in c.ko[:120]:
                print(f"   ÉCART {e['feuille']}!{e['cellule']} {e['libelle']} : Excel={e['excel']!r} moteur={e['moteur']!r}")
    finally:
        xl.Quit()
        shutil.rmtree(dossier_tmp, ignore_errors=True)
    return rapport


if __name__ == "__main__":
    modele = sys.argv[1]
    graines = [int(x) for x in sys.argv[2:]] or [1, 2, 3]
    # Graines spéciales : 101 = quote-part d'opérations en commun (655/755), 102 = gros déficit antérieur reportable
    options = {101: {"avec_qp_commun": True}, 102: {"deficit_anterieur": 500000.0}, 103: {"grand": True}}
    rapport = executer(modele, graines, options)
    sortie = os.path.join(ICI, "rapport_parite.json")
    with open(sortie, "w", encoding="utf-8") as fh:
        json.dump(rapport, fh, ensure_ascii=False, indent=1, default=str)
    print(f"\nRapport : {sortie}")
