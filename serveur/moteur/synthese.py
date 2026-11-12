"""Chiffres clés et mail de bilan (feuille Mail_bilan)."""
from datetime import date

from .balance import somme
from .outils import ajouter_mois, date_fr, div, lire_date


def _indicateurs(bg, sig, cap, col):
    v = sig[col]
    d = {
        "ca": v["ca"], "marge_globale": v["marge_globale"] - v["prod_immo"], "personnel": -v["personnel"],
        "ebe": v["ebe"], "rcai": v["rcai"], "is": -v["impots_benef"], "resultat": v["resultat"],
        "tresorerie": somme(bg, "512", col),
        "stocks": somme(bg, "3", col), "clients": somme(bg, "41", col), "fournisseurs": somme(bg, "40", col),
        "tva": somme(bg, ("44567", "44583", "44551"), col),
        "is_solde": somme(bg, "444", col),
    }
    d["autre_tresorerie"] = somme(bg, "5", col) - d["tresorerie"]
    d["bfre"] = d["stocks"] + d["clients"] + d["fournisseurs"] + d["tva"]
    k = "continuite_n" if col == "n" else "continuite_n1"
    d["capitaux_propres"] = cap[k]["total"]
    d["capitaux_sur_capital"] = div(cap[k]["total"], cap[k]["capital"])
    for cle in ("marge_globale", "personnel", "ebe", "rcai", "resultat"):
        d[cle + "_pct"] = div(d[cle], d["ca"])
    return d


LIGNES = [
    ("P&L", [("ca", "Chiffre d'affaires (HT)"), ("marge_globale", "Marge globale"), ("marge_globale_pct", "en % du CA"),
             ("personnel", "Staff cost"), ("personnel_pct", "en % du CA"), ("ebe", "EBITDA"), ("ebe_pct", "en % du CA"),
             ("rcai", "Résultat courant avant impôts"), ("rcai_pct", "en % du CA"), ("is", "Impôts sur les sociétés"),
             ("resultat", "Résultat de l'exercice"), ("resultat_pct", "en % du CA")]),
    ("Cash", [("tresorerie", "Trésorerie sur les comptes"), ("autre_tresorerie", "Autres éléments de trésorerie")]),
    ("BFRE", [("stocks", "Stocks"), ("clients", "Créances clients"), ("fournisseurs", "Dettes fournisseurs"),
              ("tva", "Dette / créance TVA"), ("bfre", "BFR d'exploitation")]),
    ("Autre", [("is_solde", "Dette / créance IS"), ("capitaux_propres", "Capitaux propres"),
               ("capitaux_sur_capital", "en % du capital social")]),
]
SANS_VARIATION = {"marge_globale_pct", "personnel_pct", "ebe_pct", "rcai_pct", "resultat_pct", "capitaux_sur_capital"}


def echeance_cloture(cloture):
    """Échéance de l'IS et de la CA12 : 15 mai N+1 pour une clôture en décembre, sinon 15 jours + 3 mois."""
    if cloture.month == 12:
        return f"15/05/{cloture.year + 1}"
    return date_fr(ajouter_mois(date.fromordinal(cloture.toordinal() + 15), 3))


def mail(bg, sig, cap, ago, cloture, saisies):
    s = saisies or {}
    n, n1 = _indicateurs(bg, sig, cap, "n"), _indicateurs(bg, sig, cap, "n1")
    groupes = []
    for titre, lignes in LIGNES:
        rows = []
        for cle, libelle in lignes:
            row = {"cle": cle, "libelle": libelle, "n": n[cle], "n1": n1[cle], "pourcentage": cle in SANS_VARIATION or cle.endswith("_pct")}
            if cle not in SANS_VARIATION:
                row["var"] = n[cle] - n1[cle]
                row["var_pct"] = div(row["var"], n1[cle])
            rows.append(row)
        groupes.append({"titre": titre, "lignes": rows})

    inclure = {k: s.get(k, True) for k in ("inclure_is", "inclure_tva", "inclure_flat_tax")}
    rep = ago["repartition"]["associes"]
    flat_tax = -sum(a["ps"] + a["precompte"] for a in rep)
    date_paiement = lire_date(ago.get("date_paiement"))
    echeances = [
        {"libelle": "Solde impôt sur les sociétés", "montant": n["is_solde"] if inclure["inclure_is"] else 0.0, "inclus": inclure["inclure_is"]},
        {"libelle": "Solde de TVA (CA12)", "montant": n["tva"] if inclure["inclure_tva"] else 0.0, "inclus": inclure["inclure_tva"]},
        {"libelle": "Flat-tax sur dividendes", "montant": flat_tax if inclure["inclure_flat_tax"] else 0.0, "inclus": inclure["inclure_flat_tax"]},
    ]
    for i, e in enumerate(echeances):
        if not e["montant"]:
            e["echeance"] = ""
        elif i < 2:
            e["echeance"] = echeance_cloture(cloture)
        else:
            e["echeance"] = date_fr(date(date_paiement.year + (date_paiement.month == 12), date_paiement.month % 12 + 1, 15)) if date_paiement else ""
    dividendes = [{"associe": a["nom"], "brut": a["retenu"], "precompte_ir": a["precompte"], "precompte_ps": a["ps"],
                   "virement": a["net"], "date": date_fr(date_paiement) if date_paiement else ""}
                  for a in rep if not a["nom"].startswith("Associé")]
    return {"date_n": date_fr(cloture), "date_n1": date_fr(date(cloture.year - 1, cloture.month, min(cloture.day, 28)) if (cloture.month, cloture.day) == (2, 29) else date(cloture.year - 1, cloture.month, cloture.day)),
            "groupes": groupes, "echeances": echeances, "dividendes": dividendes, "inclure": inclure}
