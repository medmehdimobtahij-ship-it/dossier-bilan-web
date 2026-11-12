"""Résultat fiscal et IS (feuille Résultat_Fiscal), emprunts (Caché_Emprunts), aide à la liasse (Liasse_fiscale)."""
from .balance import somme
from .outils import arrondi, datedif_mois, egal, fin_de_mois, lire_date, nombre

PLAFOND_TAUX_REDUIT = 42500
PLAFOND_DEFICIT = 1_000_000

REINTEGRATIONS = [
    ("tvs", "Taxe sur les véhicules de sociétés"), ("loyers_cb", "Loyers non déductibles crédit-bail"),
    ("taxe_bureaux_payee", "Taxe sur les bureaux payée"), ("abandon", "Abandon de créance non déductible consenti"),
    ("sci_ir", "Résultat SCI à l'IR"), ("amort_lmnp", "Amortissements LMNP"), ("divers_reint", "Divers à détailler"),
]
DEDUCTIONS = [
    ("taxe_bureaux_facturee", "Taxe sur les bureaux facturée"), ("subventions_exo", "Subventions exonérées"),
    ("rmf", "Retour à meilleure fortune non imposable"), ("ci_famille", "Crédit d'impôt famille"),
    ("cir", "Crédit d'impôt recherche"), ("divers_ded_1", "Divers à détailler"), ("divers_ded_2", "Divers à détailler"),
    ("divers_ded_3", "Divers à détailler"),
]


def _auto_ou_saisi(saisi, auto):
    """Les lignes « à saisir pour modification » : la saisie l'emporte si elle est renseignée et non nulle."""
    v = nombre(saisi)
    return auto if v == 0 else v


def imputation_deficit(resultat_avant, deficit_anterieur):
    """Déficit antérieur imputable sur l'exercice (art. 209 I du CGI).

    CORRECTION n°6 : l'Excel impute min(déficit ; 1 M€) même quand le bénéfice est plus petit, ce qui crée un
    résultat fiscal négatif et fait disparaître le déficit restant. L'imputation est plafonnée au bénéfice :
    1 M€ + 50 % de la fraction du bénéfice qui dépasse 1 M€.
    """
    if resultat_avant <= 0 or deficit_anterieur <= 0:
        return 0.0, 0.0
    plafond = resultat_avant if resultat_avant <= PLAFOND_DEFICIT else PLAFOND_DEFICIT + 0.5 * (resultat_avant - PLAFOND_DEFICIT)
    return min(deficit_anterieur, plafond), plafond


def resultat_fiscal(bg, res_n, cloture, debut_activite, saisies):
    s = saisies or {}
    benefice = res_n if res_n > 0 else 0.0
    deficit = res_n if res_n < 0 else 0.0
    is_ = _auto_ou_saisi(s.get("is_force"), somme(bg, "695"))
    amendes = _auto_ou_saisi(s.get("amendes_force"), somme(bg, "6582"))
    dons = _auto_ou_saisi(s.get("dons_force"), somme(bg, "6238"))
    reint = {"is": is_, "amendes": amendes, "dons": dons, **{k: nombre(s.get(k)) for k, _ in REINTEGRATIONS}}
    total_reint = sum(reint.values())

    taux_qp_smf = nombre(s.get("taux_qp_smf"), 0.05)
    dividende_smf = nombre(s.get("dividende_smf"))
    ded = {k: nombre(s.get(k)) for k, _ in DEDUCTIONS}
    ded["smf"] = dividende_smf * (1 - taux_qp_smf)
    total_ded = sum(ded.values())

    avant = benefice + deficit - total_ded + total_reint
    deficit_anterieur = nombre(s.get("deficit_anterieur"))
    impute, plafond = imputation_deficit(avant, deficit_anterieur)
    apres = avant - impute

    soumise = not egal(s.get("soumise_is"), "NON")
    taux_reduit = (0.15 if not egal(s.get("taux_reduit"), "NON") else 0.0) if soumise else 0.0
    taux_normal = 0.25 if soumise else 0.0
    debut = lire_date(debut_activite)
    if taux_reduit == 0:
        plafond_reduit = 0.0
    elif not debut:
        plafond_reduit = float(PLAFOND_TAUX_REDUIT)
    else:  # premier exercice : plafond au prorata des mois (mois entamé compté au trentième)
        mois = datedif_mois(debut, cloture) + (fin_de_mois(debut).day - debut.day + 1) / 30
        plafond_reduit = mois * PLAFOND_TAUX_REDUIT / 12
    base_normale = arrondi(apres - plafond_reduit, 0) if (taux_normal and apres > plafond_reduit) else 0.0
    if apres > 0:
        is_reduit = (plafond_reduit if apres > plafond_reduit else apres) * taux_reduit
    else:
        is_reduit = 0.0
    is_normal = taux_normal * base_normale
    is_total = arrondi(is_reduit + is_normal, 0)
    return {
        "benefice": benefice, "deficit": deficit, "reintegrations": reint, "total_reintegrations": total_reint,
        "deductions": ded, "dividende_smf": dividende_smf, "taux_qp_smf": taux_qp_smf, "total_deductions": total_ded,
        "avant_imputation": avant, "deficit_anterieur": deficit_anterieur, "plafond_imputation": plafond,
        "deficit_impute": impute, "deficit_restant": deficit_anterieur - impute, "apres_imputation": apres,
        "soumise_is": soumise, "taux_reduit": taux_reduit, "taux_normal": taux_normal, "plafond_taux_reduit": plafond_reduit,
        "base_taux_normal": base_normale, "is_taux_reduit": is_reduit, "is_taux_normal": is_normal, "is_total": is_total,
        "resultat_net_ajuste": benefice + is_ - is_total + deficit,
        "intitule": "Calcul de l'impôt sur les sociétés" if soumise else "Non soumise à l'impôt sur les sociétés",
    }


def emprunts(bg, cloture, saisies):
    """Caché_Emprunts : capital restant dû des 164 et échéancier pour la liasse."""
    s = saisies or {}
    lignes = []
    for r in bg:
        if r["compte"][:3] == "164":
            sc = s.get(r["compte"]) or {}
            lignes.append({"compte": r["compte"], "libelle": r["libelle"], "crdu_n1": -r["n1"], "crdu_n": -r["n"],
                           "crdu_n_plus_1": nombre(sc.get("crdu_n_plus_1")), "crdu_n_plus_5": nombre(sc.get("crdu_n_plus_5")),
                           "souscrit": nombre(sc.get("souscrit"))})
    t = {k: sum(l[k] for l in lignes) for k in ("crdu_n1", "crdu_n", "crdu_n_plus_1", "crdu_n_plus_5", "souscrit")}
    annee = cloture.year
    return {
        "annee": annee, "lignes": lignes, "totaux": t,
        "souscrit": t["souscrit"], "rembourse": t["crdu_n1"] - t["crdu_n"] + t["souscrit"], "montant_brut": t["crdu_n"],
        "a_un_an": t["crdu_n"] - t["crdu_n_plus_5"] - (t["crdu_n_plus_1"] - t["crdu_n_plus_5"]),
        "un_a_cinq_ans": t["crdu_n_plus_1"] - t["crdu_n_plus_5"], "plus_de_cinq_ans": t["crdu_n_plus_5"],
    }


def liasse(bg, sig, rf, cap, ca_vent, emp, ca, saisies):
    """Liasse_fiscale : les montants à reporter et les seuils à vérifier."""
    s = saisies or {}
    ca_70 = -somme(bg, "70")
    remu = somme(bg, "644")
    deplacements, restaurants, cadeaux = somme(bg, "6251"), somme(bg, "6257"), somme(bg, "6234")
    total_ca = sum(ca_vent.values())
    var_1068 = cap["affectation"]["autres_reserves"]
    tva_collectee = sum(ca["colonnes"][k]["tva_ca"] + ca["colonnes"][k]["tva_autres"] for k in ("20", "10", "8,5", "5,5"))
    mono = bool(s.get("mono_etablissement"))
    if ca_70 >= 500000:
        cvae = "AD - 1329 CVAE à payer"
    elif 152500 < ca_70 < 500000:
        cvae = "AD - Feuillet à remplir"
    else:
        cvae = "DI - CA inférieur à 152 500, cocher néant, Pas de 1329"
    res_n = rf["benefice"] + rf["deficit"]  # résultat de la balance (RésultatN), pas celui du SIG
    return {
        "ca": {**ca_vent, "total": total_ca, "balance": ca_70, "ecart": total_ca - ca_70},
        "charges_exc": sig["n"]["charges_exc"], "produits_exc": sig["n"]["produits_exc"],
        "emprunts": {"souscrit": emp["souscrit"], "rembourse": emp["rembourse"], "montant_brut": emp["montant_brut"],
                     "a_un_an": emp["a_un_an"], "un_a_cinq_ans": emp["un_a_cinq_ans"], "plus_de_cinq_ans": emp["plus_de_cinq_ans"],
                     "total": emp["a_un_an"] + emp["un_a_cinq_ans"] + emp["plus_de_cinq_ans"]},
        "resultat": {"libelle": "Résultat net comptable" if rf["benefice"] + rf["deficit"] == 0 else
                     ("Bénéfice comptable" if rf["benefice"] > 0 else "Déficit comptable"),
                     "comptable": rf["benefice"] + rf["deficit"], "reintegrations": rf["total_reintegrations"],
                     "deductions": rf["total_deductions"], "deficit_impute": rf["deficit_impute"],
                     "fiscal": rf["total_reintegrations"] - rf["total_deductions"] - rf["deficit_impute"] + rf["benefice"] + rf["deficit"],
                     "fiscal_apres_imputation": rf["apres_imputation"]},
        "deficit_reportable": rf["deficit_restant"],
        "dividendes_distribues": cap["affectation"]["dividendes"],
        "prelevements_reserves": var_1068 if var_1068 > 0 else 0.0,
        "tva_collectee": tva_collectee,
        "cvae": {"mono_etablissement": mono, "message_1330": "DI - Dispensée de 1330" if mono else
                 "AD - Présence de plusieurs établissements, 1330 à produire", "ca": ca_70, "message_1329": cvae},
        "frais_2067": {"remunerations": remu, "deplacements": deplacements, "restaurants": restaurants, "cadeaux": cadeaux,
                       "message_deplacements": "Sup à 15K > 2067 à produire" if deplacements >= 15000 else "Voir autres",
                       "message_restaurants": "Sup à 6,1K > 2067 à produire" if restaurants >= 6100 else "Voir autres",
                       "message_cadeaux": "Sup à 3K > 2067 à produire" if cadeaux >= 3000 else "Voir autres"},
        "remuneration_gerant": remu, "siren_cabinet": s.get("siren_cabinet") or "",
        "edi": {"resultat_avant_is": sig["n"]["resultat"] + sig["n"]["impots_benef"], "resultat_fiscal": rf["apres_imputation"],
                "is": rf["is_total"], "resultat_net": res_n},
        "verifie": s.get("verifie") or {},
    }
