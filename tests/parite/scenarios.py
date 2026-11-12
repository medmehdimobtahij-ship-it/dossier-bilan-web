"""Dossiers fictifs pour comparer le moteur à l'Excel : balance équilibrée et saisies de toutes les feuilles.

Les montants sont tirés au hasard (graine fixe : un scénario se rejoue à l'identique). Aucune donnée client.
Options pour déclencher, ou non, les défauts connus de l'Excel (voir docs/ECARTS_EXCEL.md).
"""
import random
from datetime import date

COMPTES_BILAN = [
    ("101000", "Capital social", -1, (1000, 50000)), ("104000", "Primes d'émission", -1, (0, 20000)),
    ("105000", "Écarts de réévaluation", -1, (0, 5000)), ("106100", "Réserve légale", -1, (0, 4000)),
    ("106300", "Réserves statutaires", -1, (0, 3000)), ("106400", "Réserves réglementées", -1, (0, 2000)),
    ("106800", "Autres réserves", -1, (0, 60000)), ("110000", "Report à nouveau créditeur", -1, (0, 30000)),
    ("119000", "Report à nouveau débiteur", 1, (0, 10000)), ("131000", "Subventions d'équipement", -1, (0, 8000)),
    ("145000", "Amortissements dérogatoires", -1, (0, 3000)), ("164100", "Emprunt BNP", -1, (10000, 90000)),
    ("164200", "Emprunt CIC", -1, (5000, 40000)), ("168800", "Intérêts courus", -1, (0, 900)),
    ("205000", "Logiciels", 1, (1000, 9000)), ("218300", "Matériel informatique", 1, (2000, 30000)),
    ("275000", "Dépôts et cautionnements", 1, (0, 4000)), ("281830", "Amort. matériel informatique", -1, (500, 15000)),
    ("310000", "Stock matières", 1, (0, 20000)), ("370000", "Stock marchandises", 1, (0, 40000)),
    ("401000", "Fournisseurs", -1, (2000, 60000)), ("408100", "Fournisseurs factures non parvenues", -1, (0, 8000)),
    ("411000", "Clients", 1, (3000, 90000)), ("416000", "Clients douteux", 1, (0, 6000)),
    ("419100", "Avances reçues", -1, (0, 7000)), ("421000", "Rémunérations dues", -1, (0, 9000)),
    ("431000", "URSSAF", -1, (0, 12000)), ("437000", "Autres organismes sociaux", -1, (0, 4000)),
    ("438600", "Organismes sociaux charges à payer", -1, (0, 5000)), ("444000", "État impôt sur les bénéfices", -1, (0, 20000)),
    ("445510", "TVA à décaisser", -1, (0, 15000)), ("445660", "TVA déductible", 1, (0, 9000)),
    ("445670", "Crédit de TVA", 1, (0, 4000)), ("445710", "TVA collectée 20 %", -1, (1000, 30000)),
    ("445711", "TVA collectée 10 %", -1, (0, 6000)), ("445712", "TVA collectée 5,5 %", -1, (0, 2000)),
    ("445800", "TVA à régulariser", -1, (0, 1500)), ("455000", "Associés comptes courants", -1, (0, 40000)),
    ("467000", "Autres débiteurs ou créditeurs", 1, (0, 3000)), ("471000", "Compte d'attente", 1, (0, 2500)),
    ("486000", "Charges constatées d'avance", 1, (0, 5000)), ("487000", "Produits constatés d'avance", -1, (0, 6000)),
    ("512100", "Banque BNP", 1, (0, 1)), ("512200", "Banque CIC", 1, (0, 40000)), ("530000", "Caisse", 1, (0, 800)),
    ("580000", "Virements internes", 1, (0, 500)),
]
COMPTES_GESTION = [
    ("601000", "Achats matières premières", 1, (0, 40000)), ("603700", "Variation stock marchandises", 1, (-8000, 8000)),
    ("604000", "Achats d'études et prestations", 1, (0, 30000)), ("606100", "Fournitures non stockables", 1, (500, 6000)),
    ("606400", "Fournitures administratives", 1, (100, 2000)), ("607000", "Achats de marchandises", 1, (0, 90000)),
    ("609700", "RRR obtenus sur marchandises", 1, (-3000, 0)), ("613200", "Locations immobilières", 1, (3000, 24000)),
    ("615600", "Maintenance", 1, (0, 4000)), ("616000", "Assurances", 1, (500, 5000)), ("622600", "Honoraires", 1, (1000, 9000)),
    ("623400", "Cadeaux à la clientèle", 1, (0, 4500)), ("623800", "Dons", 1, (0, 1500)), ("625100", "Voyages et déplacements", 1, (0, 18000)),
    ("625700", "Réceptions", 1, (0, 8000)), ("626000", "Frais postaux et télécom", 1, (300, 3000)), ("627000", "Services bancaires", 1, (100, 1500)),
    ("631000", "Taxes sur salaires", 1, (0, 3000)), ("635110", "CFE", 1, (200, 3000)), ("641000", "Salaires", 1, (0, 120000)),
    ("644000", "Rémunération du gérant", 1, (0, 60000)), ("645000", "Charges sociales", 1, (0, 50000)),
    ("646000", "Cotisations TNS", 1, (0, 20000)), ("651000", "Redevances logiciels", 1, (0, 2000)),
    ("657000", "VNC des immobilisations cédées", 1, (0, 5000)), ("658200", "Amendes", 1, (0, 800)),
    ("661100", "Intérêts des emprunts", 1, (100, 4000)), ("671000", "Charges exceptionnelles", 1, (0, 3000)),
    ("681120", "Dotations aux amortissements", 1, (500, 12000)), ("686000", "Dotations financières", 1, (0, 1000)),
    ("687250", "Dotations amortissements dérogatoires", 1, (0, 1500)), ("695000", "Impôt sur les bénéfices", 1, (0, 25000)),
    ("701000", "Ventes de produits finis", -1, (0, 80000)), ("706000", "Prestations de services", -1, (20000, 300000)),
    ("706100", "Prestations intracommunautaires", -1, (0, 30000)), ("706200", "Prestations export", -1, (0, 20000)),
    ("707000", "Ventes de marchandises", -1, (0, 150000)), ("707100", "Ventes de marchandises 5,5 %", -1, (0, 20000)),
    ("708800", "Autres produits annexes", -1, (0, 9000)), ("709700", "RRR accordés sur marchandises", -1, (-2000, 0)),
    ("713500", "Variation stocks produits", -1, (-5000, 5000)), ("721000", "Production immobilisée", -1, (0, 6000)),
    ("740000", "Subventions d'exploitation", -1, (0, 8000)), ("751000", "Redevances perçues", -1, (0, 1500)),
    ("757000", "Produits de cession", -1, (0, 7000)), ("758000", "Produits divers", -1, (0, 900)),
    ("761000", "Produits de participations", -1, (0, 2000)), ("771000", "Produits exceptionnels", -1, (0, 4000)),
    ("781100", "Reprises sur amortissements", -1, (0, 3000)), ("786000", "Reprises financières", -1, (0, 700)),
    ("787250", "Reprises amortissements dérogatoires", -1, (0, 900)), ("791000", "Transferts de charges", -1, (0, 2500)),
]
QP_COMMUN = [("655000", "Quote-part de perte en commun", 1, (100, 3000)), ("755000", "Quote-part de bénéfice en commun", -1, (100, 3000))]


def _montant(rng, sens, bornes, proba_zero=0.15):
    lo, hi = bornes
    if hi <= 1 or rng.random() < proba_zero:
        return 0.0
    return round(sens * rng.uniform(lo, hi), 2)


def _sous_comptes(rng, nombre_):
    """Sous-comptes en plus (grosse balance) : charges et produits détaillés, immobilisations, tiers."""
    racines = [("6063", 1), ("6135", 1), ("6156", 1), ("6181", 1), ("6227", 1), ("6236", 1), ("6256", 1), ("6281", 1), ("6311", 1),
               ("6354", 1), ("6411", 1), ("6451", 1), ("6475", 1), ("6611", 1), ("6681", 1), ("6718", 1), ("6811", 1), ("7061", -1),
               ("7062", -1), ("7083", -1), ("7588", -1), ("7681", -1), ("7718", -1), ("2154", 1), ("2182", 1), ("2184", 1),
               ("2813", -1), ("2815", -1), ("4011", -1), ("4111", 1), ("4386", -1), ("4687", -1)]
    vus, out = set(), []
    while len(out) < nombre_:
        r, sens = rng.choice(racines)
        compte = r + f"{rng.randint(0, 99):02d}"
        if compte in vus:
            continue
        vus.add(compte)
        out.append((compte, f"Sous-compte {compte}", sens, (0, 6000)))
    return out


def balance(rng, avec_qp_commun=False, grand=False):
    comptes = COMPTES_BILAN + COMPTES_GESTION + (QP_COMMUN if avec_qp_commun else []) + (_sous_comptes(rng, 260) if grand else [])
    lignes = []
    for compte, libelle, sens, bornes in comptes:
        n, n1 = _montant(rng, sens, bornes), _montant(rng, sens, bornes)
        if compte in ("120000", "129000"):
            continue
        lignes.append({"compte": compte, "libelle": libelle, "solde_n": n, "solde_n1": n1})
    # 120 en N (résultat N-1 non encore affecté, une fois sur trois)
    if rng.random() < 0.33:
        lignes.append({"compte": "120000", "libelle": "Résultat de l'exercice (bénéfice)", "solde_n": round(-rng.uniform(1000, 9000), 2), "solde_n1": 0.0})
    # Équilibre : la banque BNP absorbe l'écart
    for col in ("solde_n", "solde_n1"):
        ecart = round(sum(l[col] for l in lignes), 2)
        b = next(l for l in lignes if l["compte"] == "512100")
        b[col] = round(b[col] - ecart, 2)
    return [l for l in lignes if l["solde_n"] or l["solde_n1"]]


def saisies(rng, lignes, deficit_anterieur=0.0):
    comptes = {l["compte"] for l in lignes}
    c70 = sorted(c for c in comptes if c.startswith("70"))
    taux = {"701000": "20", "706000": "20", "706100": "INTRA", "706200": "EXTRA", "707000": "20", "707100": "5,5",
            "708800": "10", "709700": "20"}
    types = {"701000": "Marchandises", "707000": "Marchandises", "707100": "Marchandises", "709700": "Marchandises"}
    cadrage_ca = {"comptes": {c: {"taux": taux.get(c, "20"), "type": types.get(c, "Services")} for c in c70}, "colonnes": {}}
    for cle in ("20", "10", "8,5", "5,5", "0", "INTRA", "EXTRA"):
        cadrage_ca["colonnes"][cle] = {k: round(rng.uniform(0, 3000), 2) if rng.random() < 0.4 else 0.0
                                       for k in ("fae_n1", "aae_n1", "pca_n1", "fae_n", "aae_n", "pca_n", "cessions", "debours",
                                                 "client_411_n1", "client_416_n1", "client_4191_n1", "client_411_n",
                                                 "client_416_n", "client_4191_n", "pertes", "produits_exc")}

    def associes(n, avec_qp):
        out = []
        for i in range(n):
            out.append({"nom": f"Associé test {i + 1}", "qualite": rng.choice(["PP", "PP", "PM"]),
                        "dispense": rng.choice(["", "Dispensé"]), "regime": rng.choice(["TNS", "NON TNS", "EI IS"]),
                        "parts": rng.randint(1, 500), "force": round(rng.uniform(100, 5000), 2) if rng.random() < 0.2 else 0,
                        "qp": round(rng.uniform(0, 30000), 2) if avec_qp else 0,
                        "cc_moyen": round(rng.uniform(0, 20000), 2) if not avec_qp else 0})
        return out
    types_4457 = {c: rng.choice(["20", "10", "5,5"]) for c in comptes if c.startswith("4457")}
    emprunts = {c: {"crdu_n_plus_1": round(rng.uniform(0, 30000), 2), "crdu_n_plus_5": round(rng.uniform(0, 8000), 2),
                    "souscrit": round(rng.uniform(0, 20000), 2) if rng.random() < 0.3 else 0} for c in comptes if c.startswith("164")}
    return {
        "capitaux": {"dividendes": round(rng.uniform(0, 15000), 2), "compte_exploitant": 0, "autres_1": round(rng.uniform(0, 500), 2),
                     "autres_2": 0, "autres_3": 0},
        "ago_n1": {"taux_ps": 0.172, "associes": associes(rng.randint(1, 4), True)},
        "ago_n": {"taux_ps": 0.186, "reserve_statutaire": round(rng.uniform(0, 1000), 2), "reserves_reglementees": 0,
                  "autres_reserves": round(rng.uniform(0, 5000), 2), "dividendes": round(rng.uniform(0, 20000), 2),
                  "compte_courant": 0, "associes": associes(rng.randint(1, 4), False), "date_paiement": "2026-06-15"},
        "cadrage_ca": cadrage_ca,
        "tva_solde": {"types": types_4457},
        "tva_flux": {cle: {"regularisation": round(rng.uniform(-500, 500), 2) if rng.random() < 0.5 else 0,
                           "base_declaree": round(rng.uniform(0, 20000), 2) if cle in ("0", "INTRA", "EXTRA") else 0}
                     for cle in ("20", "10", "8,5", "5,5", "0", "INTRA", "EXTRA")},
        "fiscal": {"tvs": round(rng.uniform(0, 2000), 2), "loyers_cb": 0, "divers_reint": round(rng.uniform(0, 800), 2),
                   "taxe_bureaux_facturee": 0, "dividende_smf": round(rng.uniform(0, 5000), 2) if rng.random() < 0.3 else 0,
                   "taux_qp_smf": 0.05, "cir": round(rng.uniform(0, 3000), 2) if rng.random() < 0.3 else 0,
                   "deficit_anterieur": deficit_anterieur, "soumise_is": "OUI", "taux_reduit": rng.choice(["Oui", "Non"])},
        "emprunts": emprunts,
        "liasse": {"mono_etablissement": rng.random() < 0.7, "siren_cabinet": "000000000"},
        "tns": {"nom": "Gérant test", "mois_cloture": 12, "pass": 47100, "per": round(rng.uniform(0, 8000), 2),
                "plafond_retraite": round(rng.uniform(0, 6000), 2), "prevoyance": round(rng.uniform(0, 4000), 2),
                "plafond_prevoyance": round(rng.uniform(0, 3000), 2), "dividendes_cotis": round(rng.uniform(0, 5000), 2),
                "csg_non_deductible": round(rng.uniform(0, 2000), 2), "csg_deductible": round(rng.uniform(0, 4000), 2),
                "cotisations_payees": round(rng.uniform(0, 15000), 2), "cotisations_remboursees": round(rng.uniform(0, 1000), 2),
                "avantages_nature": round(rng.uniform(0, 3000), 2), "remuneration": round(rng.uniform(0, 60000), 2),
                "cotisations_urssaf": round(rng.uniform(0, 15000), 2)},
        "pamc": {"ca_total": round(rng.uniform(50000, 200000), 2), "honoraires_snir": round(rng.uniform(10000, 50000), 2)},
        "driti_manuelle": {k: round(rng.uniform(0, 5000), 2) for k in ("remuneration", "avantages_nature", "madelins_excedent",
                                                                       "csg_non_deductible", "cotisations_payees", "csg_appelee",
                                                                       "cotisations_remboursees", "per_deductible",
                                                                       "prevoyance_deductible", "dividendes_cotis")},
        "ifu": {"associe_n1": "Associé test 1", "associe_n": "Associé test 1"},
        "social": {"provision_cp": round(rng.uniform(0, 5000), 2),
                   "compta": {e: round(rng.uniform(0, 50000), 2) for e in ("Brut", "Avantages en nature", "Indemnités de rupture",
                                                                           "Cfp + taxe d'apprentissage", "Prévoyance + mutuelle",
                                                                           "Retraite", "Tickets restaurants", "Cotisations URSSAF")}},
        "mail": {"inclure_is": True, "inclure_tva": rng.random() < 0.7, "inclure_flat_tax": True},
        "tva": {"remboursements": {}},
    }


def recap_tva(rng, annee):
    recap = {}
    for m in range(1, 13):
        if rng.random() < 0.08:
            continue  # un mois sans déclaration
        lignes = {}
        for code in ("A1", "A2", "A3", "B2", "E1", "E2", "F2", "F6", "08", "09", "9B", "19", "20", "22"):
            if rng.random() < 0.6:
                lignes[code] = {"base": round(rng.uniform(0, 25000)), "taxe": "-"}
        for code in ("15", "5B", "18"):
            if rng.random() < 0.15:
                lignes[code] = {"base": "-", "taxe": round(rng.uniform(0, 400))}
        recap[f"{annee}-{m:02d}"] = lignes
    return recap


def journal_paie(rng):
    lignes = [{"code": "", "libelle": "Salaire de base", "salarial": round(rng.uniform(20000, 60000), 2), "patronal": 0},
              {"code": "", "libelle": "Brut", "salarial": round(rng.uniform(30000, 80000), 2), "patronal": 0},
              {"code": "A01.b", "libelle": "Avantage véhicule", "salarial": round(rng.uniform(0, 3000), 2), "patronal": 0},
              {"code": "J10", "libelle": "Indemnité de rupture", "salarial": round(rng.uniform(0, 5000), 2), "patronal": 0}]
    for code, lib in (("SS001", "Maladie"), ("SS003", "Vieillesse déplafonnée"), ("CH001", "Assurance chômage"),
                      ("AA201", "Retraite TU1"), ("PR001", "Prévoyance cadre"), ("TR", "Titres-restaurant"),
                      ("TC001", "Formation professionnelle"), ("ZZ999", "Rubrique inconnue")):
        lignes.append({"code": code, "libelle": lib, "salarial": round(rng.uniform(0, 3000), 2), "patronal": round(rng.uniform(0, 9000), 2)})
    return lignes


def dossier(graine, cloture=date(2025, 12, 31), avec_qp_commun=False, deficit_anterieur=0.0, grand=False):
    rng = random.Random(graine)
    lignes = balance(rng, avec_qp_commun, grand)
    return {
        "infos": {"cabinet": "CABINET EXEMPLE", "client": f"Client test {graine}", "forme": "SAS",
                  "debut_exercice": date(cloture.year, 1, 1).isoformat(), "cloture": cloture.isoformat(), "annee_ir": cloture.year,
                  "concerne_indemnite_rf": "NON", "concerne_indemnite_micro": "NON", "concerne_bic": rng.choice(["OUI", "NON"]),
                  "concerne_lmp": "NON", "concerne_lmnp": rng.choice(["OUI", "NON"]), "indemnite_rf": 1200, "indemnite_micro": 1200},
        "balance": lignes, "saisies": saisies(rng, lignes, deficit_anterieur),
        "recap_tva": recap_tva(rng, cloture.year), "journal_paie": journal_paie(rng),
    }
