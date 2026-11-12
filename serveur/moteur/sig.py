"""Soldes intermédiaires de gestion (feuille SIG).

Chaque ligne a une valeur N, N-1, le % du chiffre d'affaires, la variation et, pour les rubriques, le détail des comptes.
"""
from . import referentiel as R
from .balance import somme
from .outils import div


def _bloc(bg, libelle, col):
    """Montant d'une rubrique : produits en positif (signe + : -solde), charges en positif (signe - : +solde)."""
    s = sum(r[col] for r in bg if r["sig"] == libelle)
    return -s if libelle in R.SIG_BLOCS_PRODUITS else s


def _valeurs(bg, col):
    v = {}
    v["ca"] = -somme(bg, "70", col)
    v["ventes_march"] = -(somme(bg, "707", col) + somme(bg, "7097", col))
    v["cout_march"] = somme(bg, "607", col) + somme(bg, ("6037", "6097"), col)
    v["marge_commerciale"] = v["ventes_march"] - v["cout_march"]
    v["prod_vendue"] = _bloc(bg, R.PROD_VENDUE, col)
    v["prod_stockee"] = _bloc(bg, R.PROD_STOCKEE, col)
    v["prod_immo"] = _bloc(bg, R.PROD_IMMO, col)
    v["production"] = v["prod_vendue"] + v["prod_stockee"] + v["prod_immo"]
    v["marge_et_production"] = v["marge_commerciale"] + v["production"]
    v["autres_conso_marge"] = _bloc(bg, R.AUTRES_CONSO_MARGE, col)
    v["marge_globale"] = v["marge_et_production"] - v["autres_conso_marge"]
    v["autres_conso_tiers"] = _bloc(bg, R.AUTRES_CONSO_TIERS, col)
    v["valeur_ajoutee"] = v["marge_globale"] - v["autres_conso_tiers"]
    v["subventions"] = _bloc(bg, R.SUBVENTIONS, col)
    v["impots_taxes"] = _bloc(bg, R.IMPOTS_TAXES, col)
    v["personnel"] = _bloc(bg, R.PERSONNEL, col)
    v["ebe"] = v["valeur_ajoutee"] + v["subventions"] - v["impots_taxes"] - v["personnel"]
    v["reprises"] = _bloc(bg, R.REPRISES, col)
    v["dotations"] = _bloc(bg, R.DOTATIONS, col)
    v["qp_subv"] = _bloc(bg, R.QP_SUBV, col)
    v["produits_cessions"] = _bloc(bg, R.PRODUITS_CESSIONS, col)
    v["vnc_cedees"] = _bloc(bg, R.VNC_CEDEES, col)
    v["autres_produits"] = _bloc(bg, R.AUTRES_PRODUITS, col)
    v["autres_charges"] = _bloc(bg, R.AUTRES_CHARGES, col)
    v["rex"] = (v["ebe"] + v["reprises"] - v["dotations"] + v["qp_subv"] + v["produits_cessions"] - v["vnc_cedees"]
                + v["autres_produits"] - v["autres_charges"])
    v["qp_commun_produit"] = _bloc(bg, R.QP_COMMUN_PRODUIT, col)
    v["qp_commun_charge"] = _bloc(bg, R.QP_COMMUN_CHARGE, col)
    v["produits_fin"] = _bloc(bg, R.PRODUITS_FIN, col)
    v["charges_fin"] = _bloc(bg, R.CHARGES_FIN, col)
    v["rcai"] = v["rex"] + v["qp_commun_produit"] - v["qp_commun_charge"] + v["produits_fin"] - v["charges_fin"]
    v["produits_exc"] = _bloc(bg, R.PRODUITS_EXC, col)
    v["charges_exc"] = _bloc(bg, R.CHARGES_EXC, col)
    v["rexc"] = v["produits_exc"] - v["charges_exc"]
    v["participation"] = _bloc(bg, R.PARTICIPATION, col)
    v["impots_benef"] = _bloc(bg, R.IMPOTS_BENEF, col)
    v["resultat"] = v["rcai"] + v["rexc"] - v["participation"] - v["impots_benef"]
    return v


# (clé, signe affiché, libellé, rubrique du détail ou None, niveau : 0 rubrique, 1 solde intermédiaire)
LIGNES = [
    ("ca", "", "Chiffre d'affaires", None, 1),
    ("ventes_march", "+", "Ventes de marchandises", R.VENTES_MARCH, 0),
    ("cout_march", "-", "Coût d'achat des marchandises vendues", R.COUT_MARCH, 0),
    ("marge_commerciale", "=", "Marge commerciale", None, 1),
    ("prod_vendue", "+", "Production vendue", R.PROD_VENDUE, 0),
    ("prod_stockee", "+", "Production stockée ou déstockage", R.PROD_STOCKEE, 0),
    ("prod_immo", "+", "Production immobilisée", R.PROD_IMMO, 0),
    ("production", "=", "Production de l'exercice", None, 1),
    ("marge_et_production", "+", "Marge commerciale + production de l'exercice", None, 1),
    ("autres_conso_marge", "-", "Autres consommations comprises dans la marge globale", R.AUTRES_CONSO_MARGE, 0),
    ("marge_globale", "=", "Marge globale", None, 1),
    ("autres_conso_tiers", "-", "Autres consommations en provenance des tiers", R.AUTRES_CONSO_TIERS, 0),
    ("valeur_ajoutee", "=", "Valeur ajoutée", None, 1),
    ("subventions", "+", "Subventions d'exploitation", R.SUBVENTIONS, 0),
    ("impots_taxes", "-", "Impôts, taxes et versements assimilés", R.IMPOTS_TAXES, 0),
    ("personnel", "-", "Charges de personnel", R.PERSONNEL, 0),
    ("ebe", "=", "Excédent brut d'exploitation", None, 1),
    ("reprises", "+", "Reprises sur amortissements, dépréciations et provisions", R.REPRISES, 0),
    ("dotations", "-", "Dotations aux amortissements, dépréciations et provisions", R.DOTATIONS, 0),
    ("qp_subv", "+", "Quote-part des subventions d'investissement virée au résultat", R.QP_SUBV, 0),
    ("produits_cessions", "+", "Produits des cessions d'immobilisations", R.PRODUITS_CESSIONS, 0),
    ("vnc_cedees", "-", "Valeurs comptables des immobilisations cédées", R.VNC_CEDEES, 0),
    ("autres_produits", "+", "Autres produits", R.AUTRES_PRODUITS, 0),
    ("autres_charges", "-", "Autres charges", R.AUTRES_CHARGES, 0),
    ("rex", "=", "Résultat d'exploitation", None, 1),
    ("qp_commun_produit", "+", "Quote-part de résultat sur opérations en commun (bénéfice)", R.QP_COMMUN_PRODUIT, 0),
    ("qp_commun_charge", "-", "Quote-part de résultat sur opérations en commun (perte)", R.QP_COMMUN_CHARGE, 0),
    ("produits_fin", "+", "Produits financiers", R.PRODUITS_FIN, 0),
    ("charges_fin", "-", "Charges financières", R.CHARGES_FIN, 0),
    ("rcai", "=", "Résultat courant avant impôts", None, 1),
    ("produits_exc", "+", "Produits exceptionnels", R.PRODUITS_EXC, 0),
    ("charges_exc", "-", "Charges exceptionnelles", R.CHARGES_EXC, 0),
    ("rexc", "=", "Résultat exceptionnel", None, 1),
    ("participation", "-", "Participation des salariés", R.PARTICIPATION, 0),
    ("impots_benef", "-", "Impôts sur les bénéfices", R.IMPOTS_BENEF, 0),
    ("resultat", "=", "Résultat de l'exercice", None, 1),
]


def _detail(bg, rubrique, ca_n, ca_n1):
    """Comptes d'une rubrique, dans le sens de la rubrique (produits et charges en positif)."""
    signe = -1 if rubrique in R.SIG_BLOCS_PRODUITS else 1
    lignes = []
    for r in sorted((r for r in bg if r["sig"] == rubrique), key=lambda r: f"{r['compte']} - {r['libelle']}".casefold()):
        n, n1 = signe * r["n"], signe * r["n1"]
        lignes.append({"compte": r["compte"], "libelle": r["libelle"], "n": n, "pct_n": div(n, ca_n), "n1": n1,
                       "pct_n1": div(n1, ca_n1), "var": n - n1, "var_pct": div(n - n1, n1)})
    return lignes


def calculer(bg):
    vn, vn1 = _valeurs(bg, "n"), _valeurs(bg, "n1")
    lignes = []
    for cle, signe, libelle, rubrique, niveau in LIGNES:
        n, n1 = vn[cle], vn1[cle]
        lignes.append({
            "cle": cle, "signe": signe, "libelle": libelle, "niveau": niveau, "n": n, "n1": n1,
            "pct_n": div(n, vn["ca"]), "pct_n1": div(n1, vn1["ca"]), "var": n - n1, "var_pct": div(n - n1, n1),
            "detail": _detail(bg, rubrique, vn["ca"], vn1["ca"]) if rubrique else None,
        })
    non_ranges = [r for r in bg if r["compte"][:1] in ("6", "7") and not r["sig"] and (r["n"] or r["n1"])]
    return {"n": vn, "n1": vn1, "lignes": lignes, "non_ranges": non_ranges}
