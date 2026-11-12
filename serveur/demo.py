"""Mode démo : trois dossiers fictifs complets, créés au premier lancement avec BILAN_DEMO=1.

Les sociétés, les associés et tous les montants sont INVENTÉS. Les balances sont construites pour être cohérentes :
  - N-1 et N équilibrées (la banque absorbe l'écart) ;
  - le résultat N-1 est affecté dans les capitaux propres de N (réserve légale, autres réserves, dividendes, report) ;
  - l'IS de chaque exercice est calculé sur le résultat avant impôt ;
  - la TVA collectée et les déclarations mensuelles sont déduites du chiffre d'affaires et des soldes clients.
Aucun appel réseau : en démo, Pennylane et le connecteur ComptaZap sont désactivés.
"""
from datetime import date

import stockage
from moteur.outils import arrondi


def _is(resultat_avant_is):
    """IS de démo : 15 % jusqu'à 42 500 €, 25 % au-delà (PME éligible au taux réduit), arrondi à l'euro."""
    if resultat_avant_is <= 0:
        return 0.0
    return float(arrondi(0.15 * min(resultat_avant_is, 42500) + 0.25 * max(0.0, resultat_avant_is - 42500), 0))


def _construire(spec):
    """Balance N et N-1 cohérente à partir d'une description de société (montants positifs, sens donné par la classe)."""
    lignes = {}

    def ajout(compte, libelle, n1, n):
        l = lignes.setdefault(compte, {"compte": compte, "libelle": libelle, "solde_n1": 0.0, "solde_n": 0.0})
        l["solde_n1"] = round(l["solde_n1"] + n1, 2)
        l["solde_n"] = round(l["solde_n"] + n, 2)

    # Gestion : charges au débit (+), produits au crédit (-)
    for compte, libelle, n1, n in spec["gestion"]:
        sens = -1 if compte[0] == "7" else 1
        ajout(compte, libelle, sens * n1, sens * n)
    avant_is = {k: -sum(l[k] for l in lignes.values()) for k in ("solde_n1", "solde_n")}
    impot = {k: _is(v) for k, v in avant_is.items()}
    ajout("695000", "Impôt sur les bénéfices", impot["solde_n1"], impot["solde_n"])
    resultat_n1 = avant_is["solde_n1"] - impot["solde_n1"]

    # Bilan hors capitaux propres et banque : montants déjà signés (débit +, crédit -)
    for compte, libelle, n1, n in spec["bilan"]:
        ajout(compte, libelle, n1, n)
    ajout("444000", "État - impôt sur les bénéfices", -round(impot["solde_n1"] * 0.3, 2), -round(impot["solde_n"] * 0.3, 2))

    # TVA collectée sur encaissements : cohérente avec le solde client TTC (feuille de cadrage sur le solde)
    cl = spec["clients_20"]
    ajout("445710", "TVA collectée 20 %", -round(cl[0] / 1.2 * 0.2, 2), -round(cl[1] / 1.2 * 0.2, 2))
    ajout("411000", "Clients", cl[0], cl[1])

    # Capitaux propres : N-1 donnés, N = N-1 + affectation du résultat N-1
    c = spec["capitaux_n1"]
    capital, rl, autres, ran = c["capital"], c["reserve_legale"], c["autres_reserves"], c["report"]
    dot_rl = max(0.0, min(round(0.05 * resultat_n1, 2), 0.1 * capital - rl))
    aff = spec["affectation_n1"]
    reste = round(resultat_n1 - dot_rl - aff["autres_reserves"] - aff["dividendes"], 2)
    ajout("101300", "Capital souscrit, appelé, versé", -capital, -capital)
    ajout("106100", "Réserve légale", -rl, -(rl + dot_rl))
    ajout("106800", "Autres réserves", -autres, -(autres + aff["autres_reserves"]))
    ajout("110000", "Report à nouveau créditeur", -ran, -(ran + reste))

    # Banque : absorbe l'écart de chaque colonne
    ajout("512000", "Banque", 0.0, 0.0)
    for col in ("solde_n1", "solde_n"):
        lignes["512000"][col] = round(lignes["512000"][col] - sum(l[col] for l in lignes.values()), 2)
    balance = sorted((l for l in lignes.values() if l["solde_n"] or l["solde_n1"]), key=lambda l: l["compte"])
    return balance, resultat_n1, dot_rl


def _recap_tva(spec, annee):
    """Déclarations CA3 mensuelles : base 20 % = encaissements HT, taux réduits = ventes au comptant.
    Chaque base annuelle est répartie selon la saisonnalité, le dernier mois absorbant les arrondis."""
    cl = spec["clients_20"]
    ca = {t: sum(n for compte, _, _, n in spec["gestion"] if compte.startswith("70") and spec["taux_ca"].get(compte, "20") == t)
          for t in ("20", "10", "5,5", "INTRA")}
    base_20 = ca["20"] - spec.get("pca_n1", 0) + spec.get("pca_n", 0) + (cl[0] - cl[1]) / 1.2
    annuel = {"08": base_20, "9B": ca["10"], "09": ca["5,5"], "E2": ca["INTRA"], "20": spec["tva_deductible_annuelle"],
              "A1": base_20 + ca["10"] + ca["5,5"]}
    poids = [x / sum(spec["saisonnalite"]) for x in spec["saisonnalite"]]
    recap = {f"{annee}-{m:02d}": {} for m in range(1, 13)}
    for code, total in annuel.items():
        if not total:
            continue
        mois = [round(total * p) for p in poids[:-1]]
        mois.append(round(total) - sum(mois))
        for m, v in enumerate(mois, 1):
            recap[f"{annee}-{m:02d}"][code] = {"base": v}
    return recap


def _repondre(nb_sections_points, reponse="Oui"):
    return {f"{i}.{j}": {"fait": True, "reponse": reponse} for i, nb in enumerate(nb_sections_points) for j in range(nb)}


def _saisies(spec, balance, cloture):
    comptes = {l["compte"] for l in balance}
    cl = spec["clients_20"]
    colonnes = {"20": {"client_411_n1": cl[0], "client_411_n": cl[1], "pca_n": spec.get("pca_n", 0), "pca_n1": spec.get("pca_n1", 0)}}
    s = {
        "cadrage_ca": {"comptes": {c: {"taux": spec["taux_ca"].get(c, "20"), "type": spec["type_ca"].get(c, "Services")}
                                   for c in comptes if c.startswith("70")}, "colonnes": colonnes},
        "tva_solde": {"types": {"445710": "20"}},
        "tva_flux": {"INTRA": {"base_declaree": sum(n for c, _, _, n in spec["gestion"] if spec["taux_ca"].get(c) == "INTRA")}},
        "capitaux": {"dividendes": spec["affectation_n1"]["dividendes"]},
        "ago_n1": {"taux_ps": 0.172, "associes": spec["associes_n1"]},
        "ago_n": {"taux_ps": 0.186, **spec["ago_n"], "associes": spec["associes_n"], "date_paiement": f"{cloture.year + 1}-06-30"},
        "fiscal": {"soumise_is": "OUI", "taux_reduit": "Oui", "tvs": spec.get("tvs", 0)},
        "emprunts": spec.get("emprunts", {}),
        "liasse": {"mono_etablissement": True, "siren_cabinet": "000000000"},
        "mail": {"inclure_is": True, "inclure_tva": True, "inclure_flat_tax": True},
        "ifu": {"associe_n1": spec["associes_n1"][0]["nom"], "associe_n": spec["associes_n"][0]["nom"]},
        "revision": spec.get("revision", {}),
        "observations": spec.get("observations", {}),
        "quest_lab": _repondre([2, 5, 4, 3], "Oui"),
    }
    if spec.get("tns"):
        s["tns"] = {"mois_cloture": cloture.month, **spec["tns"]}
    if spec.get("social"):
        s["social"] = spec["social"]
    return s


# ---------------------------------------------------------------------------------------------------------------
# Les trois sociétés fictives
# ---------------------------------------------------------------------------------------------------------------
SOCIETES = [
    {
        "nom": "EXEMPLE CONSEIL SAS (fictif)", "forme": "SAS", "siren": "999000001",
        "gestion": [
            ("706000", "Prestations de services", 412000, 468500), ("706100", "Prestations intracommunautaires", 38000, 52400),
            ("708800", "Autres produits annexes", 4200, 3900), ("740000", "Subventions d'exploitation", 0, 6000),
            ("604000", "Sous-traitance", 61000, 74800), ("606100", "Fournitures non stockables", 3100, 3350),
            ("613200", "Locations immobilières", 28800, 30000), ("616000", "Assurances", 3900, 4150),
            ("622600", "Honoraires", 9200, 8700), ("625100", "Voyages et déplacements", 14800, 17900),
            ("626000", "Frais postaux et télécommunications", 4100, 4300), ("627000", "Services bancaires", 980, 1040),
            ("631000", "Taxe sur les salaires", 2100, 2400), ("635110", "CFE", 1850, 1920),
            ("641000", "Salaires", 168000, 181000), ("645000", "Charges de sécurité sociale", 71000, 76500),
            ("661100", "Intérêts des emprunts", 2300, 1900), ("681120", "Dotations aux amortissements", 7400, 8100),
            ("671000", "Charges exceptionnelles", 0, 1200),
        ],
        "bilan": [
            ("205000", "Logiciels", 12000, 12000), ("218300", "Matériel informatique", 21000, 26500),
            ("280500", "Amortissements logiciels", -8000, -10400), ("281830", "Amortissements matériel informatique", -9800, -15500),
            ("275000", "Dépôts et cautionnements", 7200, 7200), ("164100", "Emprunt bancaire", -42000, -31500),
            ("401000", "Fournisseurs", -23400, -27100), ("421000", "Rémunérations dues", -11800, -12900),
            ("431000", "Sécurité sociale", -16900, -18300), ("445510", "TVA à décaisser", -6100, -7300),
            ("445660", "TVA déductible sur ABS", 1900, 2300), ("455000", "Associés - comptes courants", -15000, -12000),
            ("486000", "Charges constatées d'avance", 2600, 2900),
        ],
        "clients_20": (61200.0, 73800.0),
        "taux_ca": {"706100": "INTRA", "708800": "20"}, "type_ca": {},
        "tva_deductible_annuelle": 19500, "saisonnalite": [8, 8, 9, 9, 8, 8, 6, 4, 9, 10, 10, 11],
        "capitaux_n1": {"capital": 20000, "reserve_legale": 1200, "autres_reserves": 38000, "report": 14500},
        "affectation_n1": {"autres_reserves": 10000, "dividendes": 30000},
        "associes_n1": [
            {"nom": "Alice Exemple", "qualite": "PP", "regime": "NON TNS", "parts": 600},
            {"nom": "Bruno Fictif", "qualite": "PP", "regime": "NON TNS", "parts": 300},
            {"nom": "Holding Démo SAS", "qualite": "PM", "regime": "", "parts": 100},
        ],
        "ago_n": {"autres_reserves": 15000, "dividendes": 40000},
        "associes_n": [
            {"nom": "Alice Exemple", "qualite": "PP", "regime": "NON TNS", "parts": 600},
            {"nom": "Bruno Fictif", "qualite": "PP", "regime": "NON TNS", "parts": 300, "dispense": "Dispensé"},
            {"nom": "Holding Démo SAS", "qualite": "PM", "regime": "", "parts": 100},
        ],
        "emprunts": {"164100": {"crdu_n_plus_1": 20800, "crdu_n_plus_5": 0}},
        "social": {"provision_cp": 14200, "compta": {"Brut": 181000, "Cotisations URSSAF": 52000, "Retraite": 15400,
                                                      "Prévoyance + mutuelle": 4800, "Cfp + taxe d'apprentissage": 2650}},
        "revision": {"512000": {"statut": "Validé", "commentaire": "Rapprochement bancaire au 31/12 sans suspens."},
                     "411000": {"statut": "Validé", "commentaire": "Balance âgée obtenue, pas de créance douteuse."},
                     "401000": {"statut": "À justifier", "commentaire": "Deux factures de décembre à rapprocher."},
                     "455000": {"statut": "En attente client", "commentaire": "Convention de compte courant demandée."},
                     "164100": {"statut": "Validé", "commentaire": "Tableau d'amortissement de la banque."}},
        "observations": {"treso": "Trésorerie confortable, aucun découvert sur l'exercice."},
    },
    {
        "nom": "BOULANGERIE FICTIVE DU CENTRE SARL (fictif)", "forme": "SARL", "siren": "999000002",
        "gestion": [
            ("707000", "Ventes de marchandises", 96000, 101500), ("701100", "Ventes de pain (5,5 %)", 268000, 281000),
            ("701200", "Ventes de pâtisseries (5,5 %)", 112000, 121500), ("701300", "Ventes à consommer sur place (10 %)", 41000, 47800),
            ("601000", "Achats de matières premières", 118000, 127500), ("607000", "Achats de marchandises", 58000, 61200),
            ("603700", "Variation des stocks de marchandises", -1200, 800), ("606100", "Énergie", 21000, 24600),
            ("613200", "Loyer du local", 30000, 30600), ("615600", "Maintenance des fours", 4800, 5300),
            ("616000", "Assurances", 3600, 3750), ("622600", "Honoraires", 5400, 5600),
            ("627000", "Services bancaires et commissions CB", 3900, 4300), ("635110", "CFE", 1400, 1450),
            ("641000", "Salaires", 142000, 151000), ("644000", "Rémunération du gérant", 36000, 38000),
            ("645000", "Charges de sécurité sociale", 48500, 51700), ("646000", "Cotisations personnelles du gérant", 13800, 14600),
            ("661100", "Intérêts des emprunts", 3900, 3300), ("681120", "Dotations aux amortissements", 16800, 17200),
            ("771000", "Produits exceptionnels", 0, 1500),
        ],
        "bilan": [
            ("215400", "Matériel de boulangerie", 128000, 134000), ("218100", "Agencements", 46000, 46000),
            ("281540", "Amortissements matériel", -61000, -74800), ("281810", "Amortissements agencements", -18400, -22800),
            ("370000", "Stock de marchandises", 6400, 5600), ("164100", "Emprunt matériel", -78000, -64500),
            ("401000", "Fournisseurs", -19800, -21300), ("421000", "Rémunérations dues", -9100, -9600),
            ("431000", "Sécurité sociale", -12600, -13300), ("437000", "Autres organismes sociaux", -3100, -3300),
            ("445510", "TVA à décaisser", -4900, -5400), ("445660", "TVA déductible sur ABS", 2100, 2350),
            ("455000", "Compte courant du gérant", -22000, -18000), ("530000", "Caisse", 1800, 2100),
        ],
        "clients_20": (1200.0, 1800.0),
        "taux_ca": {"701100": "5,5", "701200": "5,5", "701300": "10", "707000": "20"},
        "type_ca": {"707000": "Marchandises"},
        "tva_deductible_annuelle": 24800, "saisonnalite": [8, 8, 9, 9, 9, 8, 7, 6, 8, 9, 9, 12],
        "capitaux_n1": {"capital": 8000, "reserve_legale": 800, "autres_reserves": 12000, "report": 5200},
        "affectation_n1": {"autres_reserves": 0, "dividendes": 8000},
        "associes_n1": [{"nom": "Claire Exemple", "qualite": "PP", "regime": "TNS", "parts": 700, "qp": 18000},
                        {"nom": "David Démo", "qualite": "PP", "regime": "NON TNS", "parts": 300}],
        "ago_n": {"dividendes": 12000},
        "associes_n": [{"nom": "Claire Exemple", "qualite": "PP", "regime": "TNS", "parts": 700, "cc_moyen": 20000},
                       {"nom": "David Démo", "qualite": "PP", "regime": "NON TNS", "parts": 300}],
        "emprunts": {"164100": {"crdu_n_plus_1": 50400, "crdu_n_plus_5": 0}},
        "tns": {"nom": "Claire Exemple", "remuneration": 38000, "per": 2400, "plafond_retraite": 6500, "prevoyance": 1300,
                "plafond_prevoyance": 3800, "cotisations_payees": 14600, "csg_deductible": 2900, "csg_non_deductible": 1250,
                "cotisations_urssaf": 15100, "comptes": {}},
        "social": {"provision_cp": 9800, "compta": {"Brut": 151000, "Cotisations URSSAF": 41800, "Retraite": 9900,
                                                     "Prévoyance + mutuelle": 3200}},
        "revision": {"512000": {"statut": "Validé", "commentaire": "Relevé bancaire de décembre pointé."},
                     "530000": {"statut": "Anomalie", "commentaire": "Caisse créditrice en cours d'exercice : à revoir avec le gérant."},
                     "370000": {"statut": "Validé", "commentaire": "Inventaire physique au 31/12 reçu."}},
    },
    {
        "nom": "STUDIO NUMÉRIQUE IMAGINAIRE SAS (fictif)", "forme": "SAS", "siren": "999000003",
        "gestion": [
            ("706000", "Développement d'applications", 186000, 154000), ("706200", "Maintenance et hébergement", 42000, 47500),
            ("604000", "Sous-traitance", 52000, 61000), ("613200", "Coworking", 14400, 15600),
            ("615600", "Licences logicielles", 9800, 11200), ("622600", "Honoraires", 6100, 6400),
            ("623400", "Cadeaux clientèle", 900, 1400), ("625700", "Réceptions", 1800, 2600),
            ("626000", "Télécommunications", 2300, 2450), ("641000", "Salaires", 74000, 88000),
            ("645000", "Charges de sécurité sociale", 31500, 37800), ("681120", "Dotations aux amortissements", 3900, 4600),
            ("761000", "Produits financiers", 300, 650),
        ],
        "bilan": [
            ("218300", "Matériel informatique", 16500, 21000), ("281830", "Amortissements matériel informatique", -7200, -11800),
            ("401000", "Fournisseurs", -14200, -18800), ("421000", "Rémunérations dues", -5600, -6400),
            ("431000", "Sécurité sociale", -7800, -9100), ("445510", "TVA à décaisser", -3800, -2100),
            ("445660", "TVA déductible sur ABS", 1500, 1700), ("487000", "Produits constatés d'avance", -9000, -6000),
        ],
        "clients_20": (38400.0, 29400.0), "pca_n1": 9000, "pca_n": 6000,
        "taux_ca": {}, "type_ca": {},
        "tva_deductible_annuelle": 17500, "saisonnalite": [9, 9, 9, 8, 8, 8, 7, 5, 9, 9, 9, 10],
        "capitaux_n1": {"capital": 5000, "reserve_legale": 500, "autres_reserves": 0, "report": 22000},
        "affectation_n1": {"autres_reserves": 0, "dividendes": 15000},
        "associes_n1": [{"nom": "Émile Imaginaire", "qualite": "PP", "regime": "NON TNS", "parts": 500},
                        {"nom": "Fanny Inventée", "qualite": "PP", "regime": "NON TNS", "parts": 500}],
        "ago_n": {"dividendes": 0},
        "associes_n": [{"nom": "Émile Imaginaire", "qualite": "PP", "regime": "NON TNS", "parts": 500},
                       {"nom": "Fanny Inventée", "qualite": "PP", "regime": "NON TNS", "parts": 500}],
        "revision": {"487000": {"statut": "À justifier", "commentaire": "Contrats de maintenance facturés d'avance : détail à obtenir."}},
    },
]

CLOTURE = date(2025, 12, 31)


def dossiers():
    """Les dossiers de démo au format du moteur (utilisé par les tests et par semer())."""
    out = []
    for spec in SOCIETES:
        balance, _, _ = _construire(spec)
        out.append({
            "nom": spec["nom"], "siren": spec["siren"],
            "infos": {"cabinet": "CABINET EXEMPLE", "client": spec["nom"], "forme": spec["forme"], "annee_ir": CLOTURE.year,
                      "debut_exercice": date(CLOTURE.year, 1, 1).isoformat(), "cloture": CLOTURE.isoformat()},
            "balance": balance, "saisies": _saisies(spec, balance, CLOTURE), "recap_tva": _recap_tva(spec, CLOTURE.year),
            "journal_paie": _journal_paie(spec),
        })
    return out


def _journal_paie(spec):
    soc = spec.get("social")
    if not soc:
        return []
    brut = soc["compta"]["Brut"]
    return [{"code": "", "libelle": "Brut", "salarial": brut, "patronal": 0},
            {"code": "SS001", "libelle": "Maladie", "salarial": 0, "patronal": round(brut * 0.13, 2)},
            {"code": "SS003", "libelle": "Vieillesse déplafonnée", "salarial": round(brut * 0.004, 2), "patronal": round(brut * 0.0202, 2)},
            {"code": "CH001", "libelle": "Assurance chômage", "salarial": 0, "patronal": round(brut * 0.0405, 2)},
            {"code": "AA201", "libelle": "Retraite complémentaire T1", "salarial": round(brut * 0.0401, 2), "patronal": round(brut * 0.0601, 2)},
            {"code": "PR001", "libelle": "Prévoyance", "salarial": round(brut * 0.008, 2), "patronal": round(brut * 0.015, 2)},
            {"code": "TC001", "libelle": "Formation professionnelle", "salarial": 0, "patronal": round(brut * 0.01, 2)}]


def semer(qui="Démo"):
    """Crée les dossiers de démo si la base est vide. Retourne le nombre de dossiers créés."""
    if stockage.lister(archives=True):
        return 0
    for d in dossiers():
        i = d["infos"]
        nid = stockage.creer(d["nom"], i["debut_exercice"], i["cloture"], qui, d["siren"], "", i, d["saisies"], {})
        stockage.modifier(nid, {"balance": d["balance"], "recap_tva": d["recap_tva"], "journal_paie": d["journal_paie"],
                                "source_balance": "Démo (fictif)", "balance_importee_le": stockage.maintenant()},
                          qui, action=f"Balance de démonstration ({len(d['balance'])} comptes)")
    return len(SOCIETES)
