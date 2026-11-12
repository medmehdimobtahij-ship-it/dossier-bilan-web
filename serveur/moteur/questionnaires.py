"""Questionnaires du dossier (feuilles Quest_Lab, Quest_Révision, Quest_Bouclage). Le texte est celui de l'Excel."""

LAB = {
    "titre": "Questionnaire d'acceptation - maintien",
    "reponses": ["", "Oui", "Non", "NA"],
    "reponses_risque": ["", "Faible", "Modéré", "Élevé"],
    "sections": [
        ("Prise de connaissance", "oui_non", [
            "Le cabinet a-t-il rencontré le client pour prendre connaissance de ses besoins et découvrir l'entreprise ?",
            "Joindre au dossier une présentation de l'entité (plaquette, notes prises lors de l'entretien avec le client, budgets ou tableaux de bord…)",
        ]),
        ("Analyse des risques du client", "risque", [
            "Activité",
            "Caractéristiques juridiques (structure juridique, détenteurs du capital, dirigeants de l'entité…)",
            "Système d'information (fiabilité, conformité par rapport à la législation, sécurité…)",
            "Organisation comptable (existence et importance de la fonction comptable, qualification du personnel comptable, nature et qualité des travaux pris en charge…)",
            "Historique fiscal et social du client (contrôles fiscaux, contrôles Urssaf…)",
        ]),
        ("Analyse des besoins du client : les informations suivantes ont-elles été collectées ?", "oui_non", [
            "La répartition des travaux comptables entre le client et le cabinet",
            "Le volume d'écritures comptables",
            "Les spécificités comptables, fiscales et sociales relatives à l'activité et pouvant nécessiter des travaux approfondis ou spécifiques : valorisation, détermination de provisions, etc.",
            "Les délais spécifiques à respecter (demande particulière du client…)",
        ]),
        ("Analyse de la faisabilité de la mission", "oui_non", [
            "Le cabinet est-il indépendant vis-à-vis du client ?",
            "Le cabinet a-t-il la compétence pour réaliser cette mission ?",
            "Le cabinet dispose-t-il des moyens adéquats pour assurer cette mission dans de bonnes conditions (notamment de délai) ?",
        ]),
        ("Analyse des dispositions de la loi anti-blanchiment", "oui_non", [
            "Le questionnaire sur la lutte anti-blanchiment a-t-il été complété ?",
        ]),
        ("Lettre au confrère", "oui_non", [
            "Le client fait-il déjà appel aux services d'un professionnel de l'expertise comptable ?",
            "…la lettre au confrère (article 163 du Code de déontologie intégré au décret du 30 mars 2012 relatif à l'exercice de l'activité d'expertise comptable) a-t-elle été envoyée ?",
            "…existe-t-il une opposition à notre entrée en fonction ou des remarques ont-elles été formulées par le confrère ?",
        ]),
    ],
    "decisions": ["je décide d'accepter la mission de présentation", "je décide de refuser la mission de présentation",
                  "je décide de maintenir la mission de présentation", "je décide de ne pas maintenir la mission de présentation"],
    "attestation": ("Après avoir pris connaissance des réponses formulées sur cette page, compte tenu de la connaissance que "
                    "j'ai acquise de l'entité et notamment des zones et des niveaux de risque identifiés dans le cadre de "
                    "l'analyse ci-dessus,"),
}

REVISION = {
    "titre": "Questionnaire de révision",
    "reponses": ["A faire", "NA"],
    "sections": [
        ("Contrôles d'ensemble", [
            "S'assurer que les comptes d'attente sont soldés",
            "S'assurer que les comptes de virements internes sont soldés",
            "Contrôler par sondages que les enregistrements comptables s'appuient sur une pièce justificative et que l'imputation comptable est correcte (si la comptabilité est tenue par le client)",
            "Contrôler la cohérence des principaux ratios par rapport à ceux de l'exercice précédent",
        ]),
        ("Trésorerie", [
            "Contrôler l'état de rapprochement de caisse",
            "Contrôler par épreuve l'absence de soldes créditeurs en caisse au cours de l'exercice",
            "Contrôler l'état de rapprochement de banque",
            "Contrôler l'état des valeurs mobilières avec la comptabilité",
            "Contrôler les tableaux d'amortissement des emprunts avec la comptabilité",
            "Obtenir l'accord des associés sur leur compte courant",
        ]),
        ("Achats", [
            "Analyser les principaux comptes d'achats afin de détecter d'éventuelles anomalies qui pourraient justifier des contrôles complémentaires",
            "Contrôler les comptes des fournisseurs débiteurs",
            "Contrôler la cohérence du ratio fournisseurs",
            "Contrôler la correcte séparation des exercices",
            "Contrôler la concordance entre la comptabilité et les contrats et échéanciers pour crédit-bail, loyer, assurances…",
            "S'assurer que les comptes de charges ne contiennent pas des biens susceptibles de constituer des immobilisations",
        ]),
        ("Ventes", [
            "Contrôler par épreuve le dénouement en N+1 de certaines créances clients significatives",
            "Contrôler les créances douteuses et leur dépréciation",
            "Contrôler la cohérence du ratio crédit clients",
            "Contrôler la correcte séparation des exercices",
            "Contrôler les comptes clients créditeurs",
        ]),
        ("Stocks", [
            "Obtenir du client un état récapitulatif daté et signé",
            "Contrôler, par épreuves, l'application de la méthode de valorisation annoncée et de dépréciation",
            "Contrôler la cohérence du montant des en-cours avec la facturation de l'exercice suivant",
        ]),
        ("Immobilisations", [
            "Contrôler la concordance avec l'état des immobilisations et des amortissements",
            "Contrôler les mouvements des immobilisations financières",
        ]),
        ("Personnel", [
            "Contrôler le rapprochement entre les salaires comptabilisés et la DADS/DSN",
            "Contrôler les soldes des dettes fiscales et sociales avec les déclarations de la dernière période",
            "Apprécier le taux global de charges sociales",
        ]),
        ("État", [
            "Contrôler le rapprochement du chiffre d'affaires déclaré en TVA avec la comptabilité",
            "Contrôler le calcul du résultat fiscal et de l'IS",
        ]),
        ("Capitaux propres et provisions", [
            "Vérifier l'affectation du résultat N-1",
            "Obtenir l'accord de l'exploitant sur son compte le cas échéant (compte 108)",
            "Vérifier la bonne application des décisions des assemblées",
            "Apprécier, avec le client, les risques et l'opportunité de certaines provisions",
        ]),
    ],
}

BOUCLAGE = {
    "titre": "Questionnaire de bouclage",
    "reponses": ["A faire", "NA"],
    "sections": [
        ("Documents comptables, juridiques et fiscaux", [
            "Dossier de travail (balance définitive + feuilles maîtresses)",
            "Comptes annuels définitifs",
            "Liasse fiscale définitive",
            "Documents juridiques liés à l'approbation des comptes annuels",
        ]),
        ("Autres éléments", [
            "Lettre de mission signée",
            "Questionnaire d'acceptation ou du maintien de la mission",
            "Questionnaire des obligations anti-blanchiment",
            "Examen de cohérence et de vraisemblance (si mission de présentation des comptes)",
            "Conclusions sur les travaux effectués et attestation (ou rapport si présence d'un commissaire aux comptes)",
            "Liste des points en suspens de l'exercice",
            "Liste des points en suspens à suivre en N+1",
            "Note de synthèse",
            "Compte-rendu au client",
            "Rapports du commissaire aux comptes (le cas échéant)",
        ]),
    ],
}


def avancement(definition, reponses):
    """Nombre de points traités (case « fait » cochée ou NA) sur le total."""
    reponses = reponses or {}
    total = fait = 0
    for i, section in enumerate(definition["sections"]):
        for j, _ in enumerate(section[-1]):
            total += 1
            r = reponses.get(f"{i}.{j}") or {}
            if r.get("fait") or r.get("statut") == "NA" or r.get("reponse"):
                fait += 1
    return {"fait": fait, "total": total}
