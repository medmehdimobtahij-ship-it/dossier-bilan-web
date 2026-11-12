"""Déclaration de revenus du dirigeant : Récap_IR, IFU_Distrib_N_1, Caché_IFU_Distrib_N et les éléments de la
feuille « Aller à » (indemnités, revenus BIC / LMP / LMNP)."""
from .outils import egal, nombre


def elements(infos, resultat_fiscal_apres):
    """« Aller à » I17:K22 : un revenu BIC, LMP ou LMNP vaut le résultat fiscal si la case est à OUI."""
    i = infos or {}

    def oui(cle):
        return egal(i.get(cle), "OUI")
    return {
        "indemnite_rf": {"concerne": oui("concerne_indemnite_rf"), "valeur": nombre(i.get("indemnite_rf"))},
        "indemnite_micro": {"concerne": oui("concerne_indemnite_micro"), "valeur": nombre(i.get("indemnite_micro"))},
        "bic": {"concerne": oui("concerne_bic"), "valeur": resultat_fiscal_apres if oui("concerne_bic") else 0.0},
        "lmp": {"concerne": oui("concerne_lmp"), "valeur": resultat_fiscal_apres if oui("concerne_lmp") else 0.0},
        "lmnp": {"concerne": oui("concerne_lmnp"), "valeur": resultat_fiscal_apres if oui("concerne_lmnp") else 0.0},
    }


def recap_ir(el):
    """Récap_IR. CORRECTION n°3 : l'Excel reporte l'indemnité « revenus fonciers » dans la case micro-LMNP (5ND) ;
    ici, la case 5ND reçoit l'indemnité micro-LMNP."""
    bic, lmp, lmnp = el["bic"]["valeur"], el["lmp"]["valeur"], el["lmnp"]["valeur"]
    r = {
        "4BE": el["indemnite_rf"]["valeur"],
        "5ND": el["indemnite_micro"]["valeur"],
        "bic_revenus": bic if bic > 0 else 0.0, "lmp_revenus": lmp if lmp > 0 else 0.0,
        "bic_deficits": -bic if bic < 0 else 0.0, "lmp_deficits": -lmp if lmp < 0 else 0.0,
        "5NA": lmnp if lmnp > 0 else 0.0, "5NY": -lmnp if lmnp < 0 else 0.0,
    }
    r["5KC"] = r["bic_revenus"] + r["lmp_revenus"]
    r["5KF"] = r["bic_deficits"] + r["lmp_deficits"]
    r["5NC"] = r["bic_revenus"]
    r["5NF"] = r["bic_deficits"]
    r["5HY"] = r["5NC"]
    r["sections"] = {"indemnite_rf": el["indemnite_rf"]["concerne"], "indemnite_micro": el["indemnite_micro"]["concerne"],
                     "bic": el["bic"]["concerne"] or el["lmp"]["concerne"], "lmnp": el["lmnp"]["concerne"]}
    return r


def ifu(repartition, associe):
    """Cases 2DC, 2CG, 2BH, 2CK de l'associé choisi, d'après la répartition des dividendes de l'AG."""
    for a in repartition["associes"]:
        if egal(a["nom"], associe):
            return {"associe": a["nom"], "trouve": True, "2DC": a["retenu"], "2CG": a["base_cotis"], "2BH": a["base_ps"],
                    "2CK": a["precompte"]}
    return {"associe": associe or "", "trouve": False, "2DC": None, "2CG": None, "2BH": None, "2CK": None}
