"""Capitaux propres, affectation du résultat N-1 et assemblées générales (feuilles Capitaux, AGO_N_1, AGO_N,
Caché_Données)."""
from . import referentiel as R
from .balance import libelle_resultat, somme
from .outils import div, egal, nombre


def capitaux(bg, res_n, res_n1, saisies):
    """Feuille Capitaux."""
    lignes = []
    for racine, libelle in R.CAPITAUX:
        n1, n = somme(bg, racine, "n1"), somme(bg, racine, "n")
        lignes.append({"racine": racine, "libelle": f"{racine} - {libelle}", "n1": n1, "var": n - n1, "n": n,
                       "alerte": "Le résultat doit être affecté" if racine in ("120", "129") and n != 0 else ""})
    par = {l["racine"]: l for l in lignes}

    # Affectation du résultat N-1 : les variations des réserves de l'exercice
    s = saisies or {}
    autres = [nombre(s.get("dividendes")), nombre(s.get("compte_exploitant")), nombre(s.get("autres_1")),
              nombre(s.get("autres_2")), nombre(s.get("autres_3"))]
    aff = {
        "resultat_n1": res_n1,
        "reserve_legale": par["1061"]["var"], "reserve_statutaire": par["1063"]["var"],
        "reserves_reglementees": par["1064"]["var"], "autres_reserves": par["1068"]["var"],
        "report_a_nouveau": sum(par[r]["var"] for r in ("110", "119", "120", "129")),
    }
    aff["a_detailler"] = sum(aff.values()) - sum(autres)
    aff["libelle_resultat"] = libelle_resultat(res_n1, "N-1")
    aff["dividendes"], aff["compte_exploitant"] = autres[0], autres[1]
    aff["alerte"] = "" if abs(aff["a_detailler"]) < 0.001 else "Affecter ce montant selon l'affectation réalisée"

    def continuite(col, res):
        hors_resultat = -sum(l[col] for l in lignes)
        total = hors_resultat + res
        capital = -par["101"][col]
        return {"hors_resultat": hors_resultat, "resultat": res, "total": total, "capital": capital,
                "rapport": div(total, capital)}

    return {"lignes": lignes, "affectation": aff, "continuite_n1": continuite("n1", res_n1),
            "continuite_n": continuite("n", res_n)}


def _associes(liste):
    out = []
    for i in range(R.NB_ASSOCIES):
        a = (liste[i] if i < len(liste or []) else None) or {}
        out.append({
            "nom": a.get("nom") or f"Associé {i + 1}", "qualite": a.get("qualite") or "", "dispense": a.get("dispense") or "",
            "regime": a.get("regime") or "", "parts": nombre(a.get("parts")), "force": nombre(a.get("force")),
            "qp": nombre(a.get("qp")), "cc_moyen": nombre(a.get("cc_moyen")),
        })
    return out


def _base_ps(a, retenu, qp, res_n1):
    """Dividende soumis aux prélèvements sociaux (case 2BH)."""
    if egal(a["qualite"], "PM"):
        return 0.0
    if egal(a["regime"], "TNS"):
        return retenu if 0.1 * qp > retenu else 0.1 * qp
    if egal(a["regime"], "NON TNS"):
        return retenu
    if egal(a["regime"], "EI IS"):
        return retenu if 0.1 * res_n1 > retenu else 0.1 * res_n1
    return 0.0  # régime non renseigné : SI.CONDITIONS sans réponse -> 0


def repartition(dividendes, associes, taux_ps, taux_cotis_tns, res_n1, capital_et_primes=None):
    """Répartition d'un dividende entre les associés (AGO_N_1 lignes 6 à 29, AGO_N lignes 35 à 59).

    capital_et_primes : -(101 + 104) au bilan N, pour calculer la quote-part TNS (AGO_N). Sans lui (AGO_N_1),
    la quote-part est celle saisie.
    """
    total_parts = sum(a["parts"] for a in associes)
    lignes = []
    for a in associes:
        pct = div(a["parts"], total_parts)
        affecte = pct * dividendes
        retenu = affecte if a["force"] == 0 else a["force"]
        if capital_et_primes is None:
            qp = a["qp"]
        else:
            qp = pct * capital_et_primes + a["cc_moyen"] if egal(a["regime"], "TNS") else 0.0
        pm = egal(a["qualite"], "PM")
        base_ps = _base_ps(a, retenu, qp, res_n1)
        base_cotis = 0.0 if pm else retenu - base_ps
        ps = 0.0 if pm else base_ps * taux_ps
        precompte = 0.0 if (egal(a["dispense"], "Dispensé") or pm) else 0.128 * retenu
        retenue = ps + precompte
        cotis = base_cotis * taux_cotis_tns
        eco_is = cotis * 0.25
        cout = retenue + cotis - eco_is
        lignes.append({
            "nom": a["nom"], "qualite": a["qualite"], "dispense": a["dispense"], "regime": a["regime"], "parts": a["parts"],
            "pct": pct, "affecte": affecte, "force": a["force"], "retenu": retenu, "cc_moyen": a["cc_moyen"], "qp": qp,
            "base_ps": base_ps, "base_cotis": base_cotis, "ps": ps, "precompte": precompte, "retenue": retenue,
            "retenue_pct": div(retenue, retenu), "net": retenu - retenue, "cotis_tns": cotis, "economie_is": eco_is,
            "cout": cout, "cout_pct": div(cout, retenu),
        })
    return {"dividendes": dividendes, "total_parts": total_parts, "associes": lignes}


def ago_n1(cap, res_n1, saisies, param):
    """Assemblée générale N-1 : répartition des dividendes votés sur le résultat N-1 (dividendes de la feuille Capitaux).

    CORRECTION n°4 : l'Excel applique 25 % de cotisations TNS au 1er associé et 40 % aux 5 autres (formule
    recopiée de travers). Un seul taux, réglable dans les paramètres, s'applique ici à tous.
    """
    s = saisies or {}
    return repartition(cap["affectation"]["dividendes"], _associes(s.get("associes")), nombre(s.get("taux_ps"), 0.172),
                       param["taux_cotis_tns_dividendes"], res_n1)


def ago_n(bg, res_n, res_n1, saisies, param):
    """Assemblée générale à tenir sur le résultat N (AGO_N et Caché_Données)."""
    s = saisies or {}
    lignes = []
    for racine, libelle in R.CAPITAUX_AGO:
        lignes.append({"racine": racine, "libelle": f"{racine} - {libelle}", "n1": somme(bg, racine, "n1"),
                       "n": somme(bg, racine, "n")})
    par = {l["racine"]: l for l in lignes}

    def situation(col, res):
        total = -(sum(l[col] for l in lignes) - res)
        return {"resultat": -res, "total": total, "rapport": div(total, -par["101"][col])}

    sit_n1, sit_n = situation("n1", res_n1), situation("n", res_n)

    # Affectation du résultat N
    distribuable = res_n - sum(par[r]["n"] for r in ("1068", "110", "119", "120", "129"))
    if distribuable > 0:
        libelle_distrib = "Total distribuable"
    elif distribuable < 0:
        libelle_distrib = "Situation négative"
    else:
        libelle_distrib = "Equilibre"
    if -par["1061"]["n"] >= 0.1 * -par["101"]["n"]:
        signal_rl = "Réserve dotée en totalité"
    else:
        signal_rl = "Réserve à doter" if libelle_distrib == "Total distribuable" else ""

    rl_theorique = -par["101"]["n"] * 0.1
    rl_actuelle = -par["1061"]["n"]
    rl_reste = rl_theorique - rl_actuelle
    rl_5pct = rl_theorique if 0.05 * res_n > rl_theorique else 0.05 * res_n
    rl_a_doter = 0.0 if distribuable < rl_5pct else (rl_reste if rl_reste < rl_5pct else rl_5pct)

    saisi = {k: nombre(s.get(k)) for k in ("reserve_statutaire", "reserves_reglementees", "autres_reserves", "dividendes",
                                            "compte_courant")}
    reserve_legale = rl_a_doter if signal_rl == "Réserve à doter" else 0.0
    affectees = reserve_legale + sum(saisi.values())
    reste = distribuable - affectees
    affectation = {"distribuable": distribuable, "libelle_distribuable": libelle_distrib, "reserve_legale": reserve_legale,
                   **saisi, "ran_crediteur": max(reste, 0.0), "ran_debiteur": min(reste, 0.0),
                   "libelle_resultat": libelle_resultat(res_n, "N"), "signal_reserve_legale": signal_rl,
                   "reserve_legale_calcul": {"theorique": rl_theorique, "actuelle": rl_actuelle, "reste": rl_reste,
                                             "cinq_pourcent": rl_5pct, "a_doter": rl_a_doter}}
    ordre = ["reserve_legale", "reserve_statutaire", "reserves_reglementees", "autres_reserves", "dividendes",
             "compte_courant", "ran_crediteur", "ran_debiteur"]
    cumul, progressif = distribuable, {}
    for k in ordre:
        cumul -= affectation[k]
        progressif[k] = cumul
    affectation["reste_progressif"] = progressif

    # Situation après l'assemblée (colonne SITU POST AG)
    # CORRECTION n°8 : l'Excel oublie les subventions d'investissement (13) et les provisions réglementées (14).
    apres = {r: 0.0 for r in par}
    apres["101"], apres["104"] = par["101"]["n"], par["104"]["n"]
    apres["1061"] = par["1061"]["n"] - affectation["reserve_legale"]
    apres["1063"] = par["1063"]["n"] - affectation["reserve_statutaire"]
    apres["1064"] = par["1064"]["n"] - affectation["reserves_reglementees"]
    apres["1068"] = -affectation["autres_reserves"]
    apres["110"] = -affectation["ran_crediteur"]
    apres["119"] = -affectation["ran_debiteur"]
    apres["13"], apres["14"] = par["13"]["n"], par["14"]["n"]
    for l in lignes:
        l["apres_ag"] = apres[l["racine"]]
        l["variation_ag"] = apres[l["racine"]] - l["n"]
    total_apres = -sum(apres.values())
    variation_resultat = res_n  # la ligne résultat (-RésultatN) disparaît après l'AG
    post = {"total": total_apres, "rapport": div(total_apres, -apres["101"]),
            "variation_total": -(sum(l["variation_ag"] for l in lignes) + variation_resultat)}

    cap_primes = -(par["101"]["n"] + par["104"]["n"])
    rep = repartition(affectation["dividendes"], _associes(s.get("associes")), nombre(s.get("taux_ps"), 0.186),
                      param["taux_cotis_tns_dividendes"], res_n1, capital_et_primes=cap_primes)
    return {"lignes": lignes, "situation_n1": sit_n1, "situation_n": sit_n, "affectation": affectation, "apres_ag": post,
            "repartition": rep, "date_paiement": s.get("date_paiement") or ""}
