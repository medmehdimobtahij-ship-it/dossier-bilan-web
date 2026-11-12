"""Gérant majoritaire TNS : provision des cotisations, DRITI, PAMC et écritures (feuilles cachées Caché_Provision_TNS,
Caché_Driti_TNS, Caché_Driti_PAMC, Caché_Ecritures_TNS, et la feuille Driti_TNS_Manuelle)."""
from datetime import date

from .outils import arrondi, div, fin_de_mois, nombre
from .referentiel import pass_annee

CHAMPS = ["per", "plafond_retraite", "prevoyance", "plafond_prevoyance", "dividendes_cotis", "csg_non_deductible",
          "csg_deductible", "cotisations_payees", "cotisations_remboursees", "avantages_nature", "remuneration",
          "cotisations_urssaf"]


def _excedent(montant, plafond):
    """Part des cotisations facultatives au-delà du plafond de déduction (0 si le plafond n'est pas renseigné)."""
    if plafond == 0:
        return 0.0
    return montant - plafond if montant > plafond else 0.0


def provision(cloture, saisies):
    s = saisies or {}
    v = {k: nombre(s.get(k)) for k in CHAMPS}
    annee = cloture.year
    mois_cloture = int(nombre(s.get("mois_cloture"), cloture.month)) or cloture.month
    pass_ = nombre(s.get("pass"), pass_annee(annee))
    plancher, plafond = 0.0176 * pass_, pass_ * 1.3
    excedent_per = _excedent(v["per"], v["plafond_retraite"])
    excedent_prev = _excedent(v["prevoyance"], v["plafond_prevoyance"])
    revenu_fiscal = v["remuneration"] + v["avantages_nature"] + excedent_per + excedent_prev + v["csg_non_deductible"]
    base_super_brut = (v["per"] + v["prevoyance"] + v["dividendes_cotis"] + v["cotisations_payees"]
                       - v["cotisations_remboursees"] + v["avantages_nature"] + v["remuneration"])
    abattement = 0.26 * base_super_brut
    abattement = plancher if abattement < plancher else (plafond if abattement > plafond else abattement)
    base_sociale = base_super_brut - abattement
    remu_nette_simulateur = v["remuneration"] + v["avantages_nature"] + v["dividendes_cotis"] + excedent_per + excedent_prev
    cfp = arrondi(0.0025 * pass_, 0)
    csg = arrondi(0.097 * base_sociale, 0)
    csg_ded = arrondi(base_sociale * 0.068, 0)
    total = v["cotisations_urssaf"] + cfp + csg
    csg_urssaf = (remu_nette_simulateur + v["cotisations_urssaf"]) * 1.029 * 0.097
    return {
        **v, "nom": s.get("nom") or "", "annee": annee, "mois_cloture": mois_cloture, "pass": pass_, "plancher": plancher,
        "plafond": plafond, "excedent_per": excedent_per, "excedent_prevoyance": excedent_prev,
        "revenu_fiscal": revenu_fiscal, "base_super_brut": base_super_brut, "abattement": abattement,
        "base_sociale": base_sociale, "cotisations_reglees": v["cotisations_payees"] - v["cotisations_remboursees"],
        "remuneration_simulateur": remu_nette_simulateur, "cfp": cfp, "csg_crds": csg, "csg_deductible_calc": csg_ded,
        "csg_non_deductible_calc": csg - csg_ded, "cotisations_totales": total, "taux_revenu_social": div(total, base_super_brut),
        "taux_revenu_net": div(total, remu_nette_simulateur), "csg_urssaf": csg_urssaf,
        "reconciliation_urssaf": csg_urssaf + cfp + v["cotisations_urssaf"],
        "cotisations_payees_hors_csg": v["cotisations_payees"] - v["csg_non_deductible"],
    }


def driti(p):
    """Les cases de la déclaration de revenus et de la DRITI tirées de la provision (Caché_Driti_TNS)."""
    d = {
        "remuneration": p["remuneration"], "avantages_nature": p["avantages_nature"],
        "madelins_excedent": p["excedent_per"] + p["excedent_prevoyance"], "csg_non_deductible": p["csg_non_deductible"],
        "cotisations_payees": p["cotisations_payees"], "csg_appelee": p["csg_non_deductible"] + p["csg_deductible"],
        "cotisations_remboursees": p["cotisations_remboursees"], "per_deductible": p["per"] - p["excedent_per"],
        "prevoyance_deductible": p["prevoyance"] - p["excedent_prevoyance"], "dividendes_cotis": p["dividendes_cotis"],
    }
    d["1GB"] = d["remuneration"] + d["csg_non_deductible"] + d["madelins_excedent"] + d["avantages_nature"]
    d["DSCA"] = d["cotisations_payees"] - d["csg_appelee"]
    d["DSDA"] = d["cotisations_remboursees"]
    d["DSEA"] = d["per_deductible"] + d["prevoyance_deductible"]
    d["DSAA"] = d["dividendes_cotis"]
    return d


def pamc(p, d, saisies):
    """Praticiens et auxiliaires médicaux conventionnés (Caché_Driti_PAMC)."""
    s = saisies or {}
    ca_total, snir = nombre(s.get("ca_total")), nombre(s.get("honoraires_snir"))
    qp = div(snir, ca_total)
    revenus = d["1GB"] + d["DSAA"]
    return {"ca_total": ca_total, "honoraires_snir": snir, "quote_part": qp, "revenus_nets": revenus,
            "DSCS": ca_total, "DSGA": revenus * qp, "DSCR": revenus - revenus * qp,
            "DSAR": d["DSEA"] * qp, "DSCM": d["DSEA"] - d["DSEA"] * qp}


def ecritures(p, comptes=None):
    """Écritures de provision à passer à la clôture (Caché_Ecritures_TNS). Comptes réglables."""
    c = {"cotisations": "646200", "organisme": "438600", "remuneration": "644000", "compte_courant": "455000", **(comptes or {})}
    jour = fin_de_mois(date(p["annee"], min(max(p["mois_cloture"], 1), 12), 1))
    cotis = p["cotisations_urssaf"] + p["csg_deductible_calc"] + p["csg_non_deductible_calc"] + p["cfp"]
    nom, an = p["nom"], p["annee"]
    lignes = [
        {"date": jour.isoformat(), "compte": c["cotisations"], "libelle": f"TNS - Cotisations sociales {an} - {nom}", "debit": cotis, "credit": 0.0},
        {"date": jour.isoformat(), "compte": c["organisme"], "libelle": f"TNS - Cotisations {an} - {nom}", "debit": 0.0, "credit": cotis},
        {"date": jour.isoformat(), "compte": c["remuneration"], "libelle": f"TNS - Rémunération {an} - {nom}", "debit": p["remuneration"], "credit": 0.0},
        {"date": jour.isoformat(), "compte": c["compte_courant"], "libelle": f"TNS - Rémunération {an} - {nom}", "debit": 0.0, "credit": p["remuneration"]},
    ]
    td, tc = sum(l["debit"] for l in lignes), sum(l["credit"] for l in lignes)
    return {"lignes": lignes, "total_debit": td, "total_credit": tc, "ecart": td - tc}


def driti_manuelle(saisies):
    """Driti_TNS_Manuelle : les mêmes cases, saisies à la main."""
    s = saisies or {}
    v = {k: nombre(s.get(k)) for k in ("remuneration", "avantages_nature", "madelins_excedent", "csg_non_deductible",
                                        "cotisations_payees", "csg_appelee", "cotisations_remboursees", "per_deductible",
                                        "prevoyance_deductible", "dividendes_cotis")}
    v["1GB"] = v["remuneration"] + v["csg_non_deductible"] + v["madelins_excedent"] + v["avantages_nature"]
    v["DSCA"] = v["cotisations_payees"] - v["csg_appelee"]
    v["DSDA"] = v["cotisations_remboursees"]
    v["DSEA"] = v["per_deductible"] + v["prevoyance_deductible"]
    v["DSAA"] = v["dividendes_cotis"]
    return v
