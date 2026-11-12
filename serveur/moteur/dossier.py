"""Calcul complet d'un dossier bilan : toutes les feuilles, dans l'ordre de leurs dépendances, en une passe.

Entrée : le dossier (infos, balance importée, saisies). Sortie : un dictionnaire par feuille, plus les contrôles.
Aucune lecture ni écriture de fichier ici : le calcul est pur, donc testable et reproductible.
"""
from datetime import date

from . import balance, ca_tva, capitaux, fiscal, ir, questionnaires, referentiel, sig, social, synthese, tns
from .outils import arrondi, ajouter_mois, lire_date, nombre, nul

PARAMETRES_DEFAUT = {"taux_cotis_tns_dividendes": 0.25}


def _dates(infos):
    cloture = lire_date(infos.get("cloture")) or date(date.today().year - 1, 12, 31)
    debut = lire_date(infos.get("debut_exercice"))
    if not debut:
        debut = date.fromordinal(ajouter_mois(cloture, -12).toordinal() + 1)
    return debut, cloture


def calculer(dossier):
    infos = dossier.get("infos") or {}
    s = dossier.get("saisies") or {}
    param = dict(PARAMETRES_DEFAUT)
    for k, v in (dossier.get("parametres") or {}).items():
        if k in PARAMETRES_DEFAUT and v not in (None, ""):
            param[k] = nombre(v, PARAMETRES_DEFAUT[k])
    debut, cloture = _dates(infos)

    bg = balance.construire(dossier.get("balance") or [], s.get("commentaires"))
    res_n, res_n1 = balance.resultat(bg, "n"), balance.resultat(bg, "n1")
    total_n, total_n1 = sum(r["n"] for r in bg), sum(r["n1"] for r in bg)

    sig_ = sig.calculer(bg)
    revision = s.get("revision") if isinstance(s.get("revision"), dict) else {}
    cycles = []
    for cle, titre, filtre in referentiel.CYCLES:
        lignes = []
        for r in balance.extraire(bg, filtre):
            rv = revision.get(r["compte"]) or {}
            lignes.append({**{k: r[k] for k in ("compte", "libelle", "n", "n1", "var", "commentaire")},
                           "statut": rv.get("statut", ""), "note": rv.get("commentaire", "")})
        cycles.append({"cle": cle, "titre": titre, "racines": referentiel.CYCLES_RACINES[cle], "lignes": lignes,
                       "observations": (s.get("observations") or {}).get(cle, ""),
                       "valides": sum(1 for l in lignes if l["statut"] == "Validé"),
                       "total_n": sum(l["n"] for l in lignes), "total_n1": sum(l["n1"] for l in lignes)})

    cap = capitaux.capitaux(bg, res_n, res_n1, s.get("capitaux"))
    agon1 = capitaux.ago_n1(cap, res_n1, s.get("ago_n1"), param)
    agon = capitaux.ago_n(bg, res_n, res_n1, s.get("ago_n"), param)

    ca = ca_tva.cadrage_ca(bg, s.get("cadrage_ca"))
    recap = ca_tva.recap_tva(dossier.get("recap_tva"), debut, cloture, s.get("tva"))
    solde = ca_tva.cadrage_solde(bg, ca, s.get("tva_solde"))
    flux = ca_tva.cadrage_flux(bg, ca, recap, solde, s.get("tva_flux"))

    rf = fiscal.resultat_fiscal(bg, res_n, cloture, infos.get("debut_activite"), s.get("fiscal"))
    emp = fiscal.emprunts(bg, cloture, s.get("emprunts"))
    liasse = fiscal.liasse(bg, sig_, rf, cap, ca_tva.ventilation_liasse(ca), emp, ca, s.get("liasse"))

    prov = tns.provision(cloture, s.get("tns"))
    dr = tns.driti(prov)
    tns_ = {"provision": prov, "driti": dr, "pamc": tns.pamc(prov, dr, s.get("pamc")),
            "ecritures": tns.ecritures(prov, (s.get("tns") or {}).get("comptes")),
            "driti_manuelle": tns.driti_manuelle(s.get("driti_manuelle"))}

    el = ir.elements(infos, rf["apres_imputation"])
    ifu_s = s.get("ifu") or {}
    ir_ = {"elements": el, "recap": ir.recap_ir(el), "ifu_n1": ir.ifu(agon1, ifu_s.get("associe_n1")),
           "ifu_n": ir.ifu(agon["repartition"], ifu_s.get("associe_n")),
           "annee": int(infos.get("annee_ir") or cloture.year)}

    soc = social.cadrage(dossier.get("journal_paie"), s.get("social"))
    mail = synthese.mail(bg, sig_, cap, agon, cloture, s.get("mail"))
    quest = {nom: {"definition": d, "reponses": s.get(f"quest_{nom}") or {}, "avancement": questionnaires.avancement(d, s.get(f"quest_{nom}"))}
             for nom, d in (("lab", questionnaires.LAB), ("revision", questionnaires.REVISION), ("bouclage", questionnaires.BOUCLAGE))}

    resultats = {
        "infos": {**infos, "debut_exercice": debut.isoformat(), "cloture": cloture.isoformat()},
        "balance": {"lignes": bg, "resultat_n": res_n, "resultat_n1": res_n1,
                    "libelle_n": balance.libelle_resultat(res_n, "N"), "libelle_n1": balance.libelle_resultat(res_n1, "N-1"),
                    "total_n": total_n, "total_n1": total_n1},
        "cycles": cycles, "sig": sig_, "capitaux": cap, "ago_n1": agon1, "ago_n": agon,
        "cadrage_ca": ca, "tva": {"recap": recap, "solde": solde, "flux": flux},
        "fiscal": rf, "emprunts": emp, "liasse": liasse, "tns": tns_, "ir": ir_, "social": soc, "mail": mail,
        "questionnaires": quest, "parametres": param,
    }
    resultats["controles"] = controles(resultats)
    return resultats


def controles(r):
    """Les contrôles bloquants ou à regarder, affichés en tête du dossier. niveau : ok / alerte / erreur."""
    c = []
    b = r["balance"]

    def ajout(cle, titre, ok, detail, niveau_ko="erreur", feuille=None):
        c.append({"cle": cle, "titre": titre, "niveau": "ok" if ok else niveau_ko, "detail": detail, "feuille": feuille})

    if not b["lignes"]:
        ajout("balance_vide", "Balance importée", False, "Aucune balance : importez-la depuis Pennylane ou depuis un fichier.",
              feuille="import")
        return c
    ajout("equilibre_n", "Balance N équilibrée", nul(arrondi(b["total_n"], 2)), f"Écart : {b['total_n']:.2f} €", feuille="balance")
    ajout("equilibre_n1", "Balance N-1 équilibrée", nul(arrondi(b["total_n1"], 2)), f"Écart : {b['total_n1']:.2f} €", feuille="balance")
    ecart_sig = r["sig"]["n"]["resultat"] - b["resultat_n"]
    nr = r["sig"]["non_ranges"]
    ajout("sig_resultat", "Résultat du SIG = résultat de la balance", nul(arrondi(ecart_sig, 2)),
          f"Écart N : {ecart_sig:.2f} €" + (f" — comptes hors SIG : {', '.join(x['compte'] for x in nr[:8])}" if nr else ""),
          feuille="sig")
    ecart_sig1 = r["sig"]["n1"]["resultat"] - b["resultat_n1"]
    ajout("sig_resultat_n1", "Résultat du SIG N-1 = résultat de la balance N-1", nul(arrondi(ecart_sig1, 2)),
          f"Écart N-1 : {ecart_sig1:.2f} €", feuille="sig")
    aff = r["capitaux"]["affectation"]
    ajout("affectation_n1", "Affectation du résultat N-1 justifiée", not aff["alerte"],
          f"Reste à détailler : {aff['a_detailler']:.2f} €", "alerte", feuille="capitaux")
    non_aff = r["capitaux"]["lignes"]
    a_affecter = [l for l in non_aff if l["alerte"]]
    ajout("resultat_affecte", "Comptes 120 / 129 soldés", not a_affecter, "Le résultat doit être affecté", "alerte", feuille="capitaux")
    na = r["cadrage_ca"]["non_affectes"]
    ajout("ca_taux", "Taux de TVA renseigné pour chaque compte de CA", not na,
          f"{len(na)} compte(s) 70 sans taux : {', '.join(x['compte'] for x in na[:6])}", "alerte", feuille="cadrage_ca")
    cl = [x for x in r["cadrage_ca"]["controles"] if not (nul(x["ecart_n"]) and nul(x["ecart_n1"]))]
    ajout("ca_clients", "Soldes clients du cadrage = balance", not cl,
          "; ".join(f"{x['racine']} : écart N {x['ecart_n']:.2f} / N-1 {x['ecart_n1']:.2f}" for x in cl), "alerte", feuille="cadrage_ca")
    recap = r["tva"]["recap"]
    ajout("tva_recap", "Récapitulatif TVA complet", not recap["mois_manquants"],
          f"Mois sans déclaration : {', '.join(recap['mois_manquants'])}" if recap["mois_manquants"] else "", "alerte", feuille="tva")
    flux_ko = [k for k, v in r["tva"]["flux"]["colonnes"].items() if v["signal_difference"] != "ok" and (v["base_theorique"] or v["base_declaree"])]
    ajout("tva_flux", "Cadrage TVA sur les flux", not flux_ko, f"Écart à justifier sur : {', '.join(flux_ko)}", "alerte", feuille="tva")
    liasse_ca = r["liasse"]["ca"]
    ajout("liasse_ca", "Ventilation du CA pour la liasse = CA de la balance", nul(arrondi(liasse_ca["ecart"], 2)),
          f"Écart : {liasse_ca['ecart']:.2f} € (type Marchandises/Services ou taux manquant)", "alerte", feuille="cadrage_ca")
    nb = sum(len(cy["lignes"]) for cy in r["cycles"])
    val = sum(cy["valides"] for cy in r["cycles"])
    ajout("revision", "Comptes révisés", nb == 0 or val == nb, f"{val} / {nb} comptes validés", "alerte", feuille="revision")
    return c
