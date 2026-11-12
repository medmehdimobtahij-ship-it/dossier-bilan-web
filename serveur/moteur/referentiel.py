"""Les tables de référence du dossier bilan, reprises telles quelles du classeur Excel métier d'origine (non publié).

Chaque table indique la feuille d'origine. Les écarts volontaires avec l'Excel sont signalés « CORRECTION » et
décrits dans docs/ECARTS_EXCEL.md.
"""

# ---------------------------------------------------------------------------------------------------------------
# Rubriques du SIG par racine de compte (feuille cachée Caché_Mapping, tableau MAP).
# Un compte de classe 6 ou 7 est rangé sous la rubrique de sa racine à 2 chiffres, sinon 3, sinon 4 (dans cet ordre).
# Les libellés gardent leurs espaces finaux d'origine : ce sont des clés.
# ---------------------------------------------------------------------------------------------------------------
VENTES_MARCH = "Ventes de marchandises "
COUT_MARCH = "Coût d'achat des marchandises vendues"
PROD_VENDUE = "Production vendue "
PROD_STOCKEE = "Production stockée ou Déstockage de production "
PROD_IMMO = "Production immobilisée "
AUTRES_CONSO_MARGE = "Autres consommations comprises dans la marge globale"
AUTRES_CONSO_TIERS = "Autres consommation de l'exercice en provenance des tiers"
SUBVENTIONS = "Subventions"
IMPOTS_TAXES = "Impôts, taxes et versements assimilés "
PERSONNEL = "Charges de personnel "
REPRISES = "Reprises sur amortissements, dépréciations et provisions "
DOTATIONS = "Dotations aux amortissements, aux dépréciations et aux provisions"
QP_SUBV = "Quote-part des subventions d’investissement virée au résultat de l’exercice"
PRODUITS_CESSIONS = "Produits des cessions d’immobilisations incorporelles et corporelles"
VNC_CEDEES = "Valeurs comptables des immobilisations incorporelles et corporelles cédées "
AUTRES_PRODUITS = "Autres produits"
AUTRES_CHARGES = "Autres charges"
# CORRECTION n°1 : l'Excel range 755 et 655 sous un même libellé, que le SIG lit deux fois (en + et en -).
# Ici, la quote-part bénéficiaire (755) et la quote-part déficitaire (655) ont chacune leur rubrique.
QP_COMMUN_PRODUIT = "Quote-part de résultat sur opérations faites en commun (bénéfice attribué)"
QP_COMMUN_CHARGE = "Quote-part de résultat sur opérations faites en commun (perte supportée)"
PRODUITS_FIN = "Produits financiers"
CHARGES_FIN = "Charges financières "
PRODUITS_EXC = "Produits exceptionnels"
CHARGES_EXC = "Charges exceptionnelles "
PARTICIPATION = "Participation des salariés"
IMPOTS_BENEF = "Impôts sur les bénéfices"

_MAP = [
    (VENTES_MARCH, ["707", "7097"]),
    (COUT_MARCH, ["607", "6037", "6097"]),
    (PROD_VENDUE, ["700", "701", "702", "703", "704", "705", "706", "708", "7090", "7091", "7092", "7093", "7094",
                   "7095", "7096", "7098", "7099"]),
    (PROD_STOCKEE, ["71"]),
    (PROD_IMMO, ["72"]),
    (AUTRES_CONSO_MARGE, ["600", "601", "602", "604", "605", "606", "608", "6030", "6031", "6032", "6033", "6034",
                          "6035", "6036", "6038", "6039", "6090", "6091", "6092", "6093", "6094", "6095", "6096",
                          "6098", "6099"]),
    (AUTRES_CONSO_TIERS, ["61", "62"]),
    (SUBVENTIONS, ["74"]),
    (IMPOTS_TAXES, ["63"]),
    (PERSONNEL, ["64"]),
    (REPRISES, ["781"]),
    (DOTATIONS, ["681"]),
    (QP_SUBV, ["747"]),
    (PRODUITS_CESSIONS, ["757"]),
    (VNC_CEDEES, ["657"]),
    (AUTRES_PRODUITS, ["751", "752", "753", "754", "756", "758", "759"]),
    (AUTRES_CHARGES, ["651", "652", "653", "654", "656", "658", "659"]),
    (QP_COMMUN_PRODUIT, ["755"]),
    (QP_COMMUN_CHARGE, ["655"]),
    (PRODUITS_FIN, ["76", "786"]),
    (CHARGES_FIN, ["66", "686"]),
    (PRODUITS_EXC, ["77", "787"]),
    (CHARGES_EXC, ["67", "687"]),
    (PARTICIPATION, ["691"]),
    (IMPOTS_BENEF, ["690", "692", "693", "694", "695", "696", "697", "698", "699"]),
]
MAP = {racine: libelle for libelle, racines in _MAP for racine in racines}
RANG = {libelle: i + 1 for i, (libelle, _) in enumerate(_MAP)}


def rubrique_sig(compte):
    """Rubrique du SIG d'un compte (colonne SIG de Bal_Comparative), ou None hors classes 6 et 7 / racine inconnue."""
    if compte[:1] not in ("6", "7"):
        return None
    for n in (2, 3, 4):
        if compte[:n] in MAP:
            return MAP[compte[:n]]
    return None


# ---------------------------------------------------------------------------------------------------------------
# Structure de la feuille SIG : (signe, libellé, nature). Nature « bloc » = somme des comptes de la rubrique
# (signe + : -solde, signe - : +solde) ; « total » = formule de cumul. Les cumuls sont dans sig.py.
# ---------------------------------------------------------------------------------------------------------------
SIG_BLOCS_PRODUITS = {VENTES_MARCH, PROD_VENDUE, PROD_STOCKEE, PROD_IMMO, SUBVENTIONS, REPRISES, QP_SUBV,
                      PRODUITS_CESSIONS, AUTRES_PRODUITS, QP_COMMUN_PRODUIT, PRODUITS_FIN, PRODUITS_EXC}

# ---------------------------------------------------------------------------------------------------------------
# Feuilles de révision par cycle (macro Clearbalance, Module2) : comptes retenus selon leur début.
# ---------------------------------------------------------------------------------------------------------------
CYCLES = [
    ("attente", "Comptes d'attente et de régularisation", lambda c: c[:2] in ("47", "58")),
    ("treso", "Trésorerie", lambda c: c[:1] == "5" and c[:2] != "58"),
    ("courants", "Comptes courants", lambda c: c[:2] in ("45", "46")),
    ("emprunts", "Emprunts", lambda c: c[:2] == "16" or c[:3] == "661"),
    ("social", "Social", lambda c: c[:2] in ("64", "42", "43")),
    ("etat", "État", lambda c: c[:2] in ("44", "69", "63")),
    ("ce", "Charges externes", lambda c: c[:2] in ("60", "61", "62")),
    ("immos", "Immobilisations", lambda c: c[:1] == "2" or c[:3] == "681"),
    ("cp", "Capitaux propres", lambda c: c[:1] == "1" and c[:2] not in ("16", "15")),
]
CYCLES_RACINES = {
    "attente": "47, 58", "treso": "5 (hors 58)", "courants": "45, 46", "emprunts": "16, 661", "social": "42, 43, 64",
    "etat": "44, 63, 69", "ce": "60, 61, 62", "immos": "2, 681", "cp": "1 (hors 15, 16)",
}
STATUTS_REVISION = ["", "Validé", "À justifier", "En attente client", "Anomalie", "Non significatif"]

# ---------------------------------------------------------------------------------------------------------------
# Capitaux propres (feuille Capitaux, tableau KP) et assemblée générale (AGO_N).
# ---------------------------------------------------------------------------------------------------------------
CAPITAUX = [
    ("101", "Capital"), ("104", "Primes liées au capital social"), ("105", "Écarts de réévaluation"),
    ("1061", "Réserve légale"), ("1063", "Réserves statutaires ou contractuelles"), ("1064", "Réserves réglementées"),
    ("1068", "Autres réserves"), ("110", "Report à nouveau (solde créditeur)"), ("119", "Report à nouveau (solde débiteur)"),
    ("120", "Résultat de l'exercice (bénéfice)"), ("129", "Résultat de l'exercice (perte)"),
    ("13", "Subventions d'investissement"), ("14", "Provisions réglementées"),
]
CAPITAUX_AGO = [r for r in CAPITAUX if r[0] != "105"]  # AGO_N ne reprend pas les écarts de réévaluation

NB_ASSOCIES = 6
REGIMES_DIVIDENDE = ["", "TNS", "NON TNS", "EI IS"]
QUALITES_ASSOCIE = ["", "PP", "PM"]

# ---------------------------------------------------------------------------------------------------------------
# Plafond annuel de la Sécurité sociale (CORRECTION n°5 : l'Excel le fige à 47 100 €, valeur 2025).
# ---------------------------------------------------------------------------------------------------------------
PASS = {2023: 43992, 2024: 46368, 2025: 47100, 2026: 48060}


def pass_annee(annee):
    if annee in PASS:
        return PASS[annee]
    return PASS[max(a for a in PASS if a <= annee)] if annee > min(PASS) else PASS[min(PASS)]


# ---------------------------------------------------------------------------------------------------------------
# TVA : colonnes de taux du cadrage (Cadrage_CA, lignes 35) et lignes de la CA3 reprises dans TVA_Récap_Interne.
# ---------------------------------------------------------------------------------------------------------------
TAUX_CA = [("20", 20.0), ("10", 10.0), ("8,5", 8.5), ("5,5", 5.5), ("0", 0.0), ("INTRA", None), ("EXTRA", None)]
TAUX_CA_TAXES = ["20", "10", "8,5", "5,5"]
TYPES_CA = ["", "Marchandises", "Services"]

CA3_BASES = ["A1", "A2", "A3", "A4", "B2", "B5", "E1", "E2", "E3", "E6", "F1", "F6", "F7", "F8"]
CA3_TAXABLES = [("08", 0.2), ("09", 0.055), ("9B", 0.1), ("10", 0.085)]
CA3_TAXE_DUE = ["15", "5B", "18"]
CA3_DEDUCTIBLE = ["19", "20", "21", "22", "2C"]
CA3_LIBELLES = {
    "A1": "Ventes, prestations de services", "A2": "Autres opérations imposables",
    "A3": "Achats de prestations de services intracommunautaires", "A4": "Importations (autres que produits pétroliers)",
    "B2": "Acquisitions intracommunautaires", "B5": "Régularisations (opérations taxées)",
    "E1": "Exportations hors UE", "E2": "Autres opérations non imposables", "E3": "Ventes à distance B to C",
    "E6": "Importations sous régime fiscal suspensif", "F1": "Acquisitions intracommunautaires (non taxées)",
    "F6": "Achats en franchise", "F7": "Ventes par un assujetti non établi en France", "F8": "Régularisations (non taxées)",
    "08": "Taux normal 20 %", "09": "Taux réduit 5,5 %", "9B": "Taux réduit 10 %", "10": "DOM 8,5 %",
    "15": "TVA antérieurement déduite à reverser", "5B": "Sommes à ajouter (acompte congés)",
    "16": "Total TVA brute due", "17": "Dont TVA sur acquisitions intracommunautaires", "18": "Dont TVA à destination de Monaco",
    "19": "TVA déductible sur immobilisations", "20": "TVA déductible sur autres biens et services",
    "21": "Autre TVA à déduire", "22": "Report du crédit de la déclaration précédente",
    "2C": "Sommes à imputer (acompte congés)", "23": "Total TVA déductible", "25": "Crédit de TVA",
    "26": "Remboursement demandé", "27": "Crédit à reporter", "28": "TVA nette due",
}

MOIS_FR = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6, "juillet": 7,
           "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12}
