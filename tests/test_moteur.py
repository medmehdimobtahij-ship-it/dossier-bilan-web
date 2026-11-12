"""Tests du moteur, sans Excel : invariants comptables, règles reprises de l'Excel et corrections de ses défauts.

    python -m pytest tests

La parité complète avec l'Excel se vérifie à part (tests/parite/excel_parite.py, poste Windows avec Excel).
"""
import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "serveur"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "parite"))

from moteur import calculer  # noqa: E402
from moteur.balance import construire  # noqa: E402
from moteur.ca_tva import periodes  # noqa: E402
from moteur.fiscal import imputation_deficit  # noqa: E402
from moteur.outils import arrondi, datedif_mois, nombre  # noqa: E402
from moteur.referentiel import rubrique_sig  # noqa: E402
import scenarios  # noqa: E402


def dossier(lignes, saisies=None, **infos):
    return {"infos": {"cloture": "2025-12-31", **infos}, "balance": [
        {"compte": c, "libelle": l, "solde_n": n, "solde_n1": n1} for c, l, n, n1 in lignes], "saisies": saisies or {}}


SIMPLE = [("101000", "Capital", -10000, -10000), ("512000", "Banque", 25000, 12000), ("401000", "Fournisseurs", -3000, -2000),
          ("706000", "Prestations", -50000, -40000), ("626000", "Télécom", 8000, 6000), ("641000", "Salaires", 20000, 24000)]


# ---------------------------------------------------------------- outils
def test_arrondi_comme_excel():
    assert arrondi(2.5) == 3 and arrondi(-2.5) == -3 and arrondi(0.125, 2) == 0.13
    assert arrondi(1000 * 0.055) == 55


def test_nombre_accepte_les_formats_francais():
    assert nombre("1 234,56") == 1234.56 and nombre("1.234,56") == 1234.56 and nombre("-") == 0 and nombre("12 €") == 12


def test_datedif():
    assert datedif_mois(date(2025, 3, 15), date(2025, 12, 31)) == 9
    assert datedif_mois(date(2025, 3, 31), date(2025, 4, 30)) == 0


# ---------------------------------------------------------------- balance
def test_balance_resultat_et_equilibre():
    r = calculer(dossier(SIMPLE))
    assert r["balance"]["resultat_n"] == pytest.approx(22000)
    assert r["balance"]["resultat_n1"] == pytest.approx(10000)
    assert r["sig"]["n"]["resultat"] == pytest.approx(r["balance"]["resultat_n"])
    assert next(c for c in r["controles"] if c["cle"] == "sig_resultat")["niveau"] == "ok"


def test_doublons_additionnes():
    """Correction n°7 : un compte présent deux fois est additionné (l'Excel décalait ses colonnes)."""
    bg = construire([{"compte": "512000", "libelle": "Banque", "solde_n": 100, "solde_n1": 0},
                     {"compte": 512000.0, "libelle": "", "solde_n": 50, "solde_n1": 20}])
    assert len(bg) == 1 and bg[0]["n"] == 150 and bg[0]["n1"] == 20


def test_rubriques_sig():
    assert rubrique_sig("706000").strip() == "Production vendue"
    assert rubrique_sig("709700").strip() == "Ventes de marchandises"
    assert rubrique_sig("603700") == "Coût d'achat des marchandises vendues"
    assert rubrique_sig("401000") is None
    assert rubrique_sig("791000") is None  # transferts de charges : absents du tableau de l'Excel (question ouverte)


def test_qp_operations_en_commun_comptees_une_fois():
    """Correction n°1 : 755 et 655 n'entrent qu'une fois dans le résultat courant."""
    r = calculer(dossier(SIMPLE + [("755000", "QP bénéfice", -1000, 0), ("655000", "QP perte", 300, 0), ("512100", "Banque 2", 700, 0)]))
    assert r["sig"]["n"]["qp_commun_produit"] == 1000 and r["sig"]["n"]["qp_commun_charge"] == 300
    assert r["sig"]["n"]["resultat"] == pytest.approx(r["balance"]["resultat_n"])


def test_cycles():
    r = calculer(dossier(SIMPLE + [("471000", "Attente", 0, 0), ("580000", "Virements", 10, 0), ("512100", "Banque 2", -10, 0)]))
    par = {c["cle"]: [l["compte"] for l in c["lignes"]] for c in r["cycles"]}
    assert par["attente"] == ["471000", "580000"]
    assert par["treso"] == ["512000", "512100"]
    assert par["cp"] == ["101000"]
    assert par["ce"] == ["626000"]


# ---------------------------------------------------------------- fiscal
@pytest.mark.parametrize("benefice,deficit,impute", [
    (10_000, 50_000, 10_000),            # le déficit ne peut pas dépasser le bénéfice (correction n°6)
    (800_000, 300_000, 300_000),
    (1_500_000, 2_000_000, 1_250_000),   # 1 M€ + 50 % de 500 k€
    (-5_000, 50_000, 0),
    (20_000, 0, 0),
])
def test_imputation_deficit(benefice, deficit, impute):
    assert imputation_deficit(benefice, deficit)[0] == pytest.approx(impute)


def test_is_taux_reduit_et_normal():
    r = calculer(dossier(SIMPLE, {"fiscal": {"soumise_is": "OUI", "taux_reduit": "Oui"}}))
    rf = r["fiscal"]
    assert rf["apres_imputation"] == pytest.approx(22000)
    assert rf["is_total"] == pytest.approx(3300)  # 22 000 x 15 %
    r = calculer(dossier(SIMPLE + [("706100", "Prestations 2", -100000, 0), ("512100", "Banque 2", 100000, 0)], {"fiscal": {"taux_reduit": "Oui"}}))
    assert r["fiscal"]["is_total"] == pytest.approx(42500 * 0.15 + (122000 - 42500) * 0.25)


def test_is_premier_exercice_prorata():
    """Formule de l'Excel : mois entiers + jours du premier mois / 30 (juillet-décembre = 5 + 31/30 mois)."""
    d = dossier(SIMPLE, {"fiscal": {"taux_reduit": "Oui"}}, debut_activite="2025-07-01")
    assert calculer(d)["fiscal"]["plafond_taux_reduit"] == pytest.approx((5 + 31 / 30) * 42500 / 12)


def test_deficit_restant_preserve():
    r = calculer(dossier(SIMPLE, {"fiscal": {"deficit_anterieur": 50000}}))
    assert r["fiscal"]["deficit_impute"] == pytest.approx(22000)
    assert r["fiscal"]["deficit_restant"] == pytest.approx(28000)
    assert r["fiscal"]["apres_imputation"] == pytest.approx(0)
    assert r["ir"]["recap"]["5KF"] == 0


# ---------------------------------------------------------------- capitaux et AG
def test_reserve_legale_a_doter():
    lignes = [("101000", "Capital", -10000, -10000), ("106100", "Réserve légale", -200, -200), ("512000", "Banque", 60200, 30200),
              ("706000", "Prestations", -50000, -20000)]
    ag = calculer(dossier(lignes))["ago_n"]["affectation"]
    assert ag["signal_reserve_legale"] == "Réserve à doter"
    assert ag["reserve_legale"] == pytest.approx(800)  # 10 % du capital moins la réserve déjà dotée, dans la limite de 5 % du résultat
    assert ag["ran_crediteur"] == pytest.approx(50000 - 800)


def test_situation_apres_ag_garde_subventions():
    """Correction n°8 : les comptes 13 et 14 restent dans les capitaux propres après l'AG."""
    lignes = SIMPLE + [("131000", "Subventions", -5000, -5000), ("512100", "Banque 2", 5000, 5000)]
    ag = calculer(dossier(lignes))["ago_n"]
    l13 = next(l for l in ag["lignes"] if l["racine"] == "13")
    assert l13["apres_ag"] == -5000 and l13["variation_ag"] == 0


def test_dividendes_taux_unique():
    """Correction n°4 : même taux de cotisations TNS pour tous les associés."""
    s = {"capitaux": {"dividendes": 10000}, "ago_n1": {"associes": [
        {"nom": "A", "qualite": "PP", "regime": "NON TNS", "parts": 50}, {"nom": "B", "qualite": "PP", "regime": "TNS", "parts": 50, "qp": 1000}]}}
    rep = calculer(dossier(SIMPLE, s))["ago_n1"]["associes"]
    assert rep[0]["retenu"] == 5000 and rep[0]["base_ps"] == 5000 and rep[0]["base_cotis"] == 0
    assert rep[1]["base_ps"] == 100 and rep[1]["base_cotis"] == 4900
    assert rep[1]["cotis_tns"] == pytest.approx(4900 * 0.25)
    assert rep[0]["precompte"] == pytest.approx(640)


# ---------------------------------------------------------------- TVA
def test_periodes_exercice_decale():
    p = periodes(date(2024, 7, 1), date(2025, 6, 30))
    assert len(p) == 12 and p[0] == date(2024, 7, 1) and p[-1] == date(2025, 6, 1)


def test_recap_tva_et_flux():
    s = {"cadrage_ca": {"comptes": {"706000": {"taux": "20", "type": "Services"}}}}
    d = dossier(SIMPLE, s)
    d["recap_tva"] = {f"2025-{m:02d}": {"08": {"base": 50000 / 12}} for m in range(1, 13)}
    r = calculer(d)
    assert r["tva"]["recap"]["totaux"]["08"] == pytest.approx(50000)
    fl = r["tva"]["flux"]["colonnes"]["20"]
    assert fl["base_declaree"] == pytest.approx(50000)
    assert fl["base_theorique"] == pytest.approx(50000)
    assert fl["signal"] == "ok"


def test_flux_sans_tva_regularisation():
    """Correction n°2 : la régularisation d'une colonne sans TVA s'ajoute à l'écart au lieu de le neutraliser."""
    s = {"tva_flux": {"INTRA": {"base_declaree": 1000, "regularisation": 200}}}
    fl = calculer(dossier(SIMPLE, s))["tva"]["flux"]["colonnes"]["INTRA"]
    assert fl["ecart"] == 1000 and fl["ecart_apres_regul"] == 1200 and fl["signal_apres"] == "excès"


def test_liasse_lit_tous_les_comptes_70():
    """Correction n°9 : la ventilation du CA lit tous les comptes 70, pas seulement les 13 premiers."""
    lignes = [(f"7060{i:02d}", f"Prestations {i}", -1000, 0) for i in range(20)] + [("512000", "Banque", 20000, 0)]
    s = {"cadrage_ca": {"comptes": {f"7060{i:02d}": {"taux": "20", "type": "Services"} for i in range(20)}}}
    li = calculer(dossier(lignes, s))["liasse"]["ca"]
    assert li["services_france"] == pytest.approx(20000) and li["ecart"] == pytest.approx(0)


# ---------------------------------------------------------------- IR, TNS, social
def test_recap_ir_case_5nd():
    """Correction n°3 : la case 5ND reçoit l'indemnité micro-LMNP."""
    r = calculer(dossier(SIMPLE, concerne_indemnite_micro="OUI", indemnite_rf=100, indemnite_micro=700))
    assert r["ir"]["recap"]["5ND"] == 700 and r["ir"]["recap"]["4BE"] == 100


def test_pass_selon_annee():
    """Correction n°5 : le PASS suit l'année de clôture."""
    assert calculer(dossier(SIMPLE))["tns"]["provision"]["pass"] == 47100
    d = dossier(SIMPLE)
    d["infos"]["cloture"] = "2026-12-31"
    assert calculer(d)["tns"]["provision"]["pass"] == 48060


def test_ecritures_tns_equilibrees():
    r = calculer(dossier(SIMPLE, {"tns": {"remuneration": 30000, "cotisations_urssaf": 9000}}))
    assert r["tns"]["ecritures"]["ecart"] == pytest.approx(0)


def test_social_regroupement_organismes():
    d = dossier(SIMPLE)
    d["journal_paie"] = [{"code": "", "libelle": "Brut", "salarial": 40000}, {"code": "SS001", "libelle": "Maladie", "patronal": 3000},
                         {"code": "CH001", "libelle": "Chômage", "patronal": 1000}, {"code": "XX1", "libelle": "?", "patronal": 5}]
    so = calculer(d)["social"]
    urssaf = next(x for x in so["rapprochement"] if x["element"] == "Cotisations URSSAF")
    assert urssaf["paie"] == 4000 and so["codes_a_parametrer"] == ["XX"]


# ---------------------------------------------------------------- robustesse
def test_dossier_vide_ne_plante_pas():
    r = calculer({"infos": {}, "balance": [], "saisies": {}})
    assert r["controles"][0]["cle"] == "balance_vide"


def test_saisies_abimees_ne_plantent_pas():
    s = {"revision": [], "fiscal": {"tvs": "abc"}, "capitaux": {"dividendes": None}, "ago_n": {"associes": [None, {"parts": "x"}]}}
    calculer(dossier(SIMPLE, s))


@pytest.mark.parametrize("graine", range(1, 31))
def test_scenarios_invariants(graine):
    """Sur 30 dossiers fictifs : balance équilibrée, SIG cohérent, totaux de TVA et écritures équilibrées."""
    d = scenarios.dossier(graine)
    r = calculer(d)
    b = r["balance"]
    assert abs(b["total_n"]) < 0.01 and abs(b["total_n1"]) < 0.01
    hors_sig = sum(-x["n"] for x in r["sig"]["non_ranges"])
    assert r["sig"]["n"]["resultat"] + hors_sig == pytest.approx(b["resultat_n"], abs=0.01)
    t = r["tva"]["recap"]
    assert t["totaux"].get("16", 0) == pytest.approx(sum(c["valeurs"]["16"] for c in t["colonnes"]))
    assert r["tns"]["ecritures"]["ecart"] == pytest.approx(0)
    assert r["fiscal"]["deficit_restant"] >= 0
