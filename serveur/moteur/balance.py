"""La balance comparative (feuilles BalanceP, Caché_Intermédiaire et Bal_Comparative, tableau BG).

Convention des soldes, comme l'Excel : solde = débit - crédit (un produit ou une dette est négatif).
"""
from .outils import arrondi, div, nombre
from .referentiel import RANG, rubrique_sig


def normaliser_compte(v):
    """Le numéro de compte en texte : 401000.0 -> '401000', ' 512 100 ' -> '512100'."""
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip().replace(" ", "")


def construire(lignes, commentaires=None):
    """Balance comparative à partir des lignes importées [{compte, libelle, solde_n, solde_n1}].

    CORRECTION n°7 : un compte présent deux fois (ex. balance N et N-1 juxtaposées) est additionné.
    L'Excel décalait les colonnes (FILTRE garde les doublons, RECHERCHEV ne lit que le premier).
    """
    commentaires = commentaires or {}
    par_compte = {}
    for l in lignes:
        c = normaliser_compte(l.get("compte"))
        if not c:
            continue
        r = par_compte.get(c)
        if r is None:
            r = par_compte[c] = {"compte": c, "libelle": str(l.get("libelle") or "").strip().upper(), "n": 0.0, "n1": 0.0}
        elif not r["libelle"]:
            r["libelle"] = str(l.get("libelle") or "").strip().upper()
        r["n"] += nombre(l.get("solde_n"))
        r["n1"] += nombre(l.get("solde_n1"))

    bg = []
    for c in sorted(par_compte, key=str.casefold):
        r = par_compte[c]
        n, n1 = arrondi(r["n"], 2), arrondi(r["n1"], 2)
        var = n - n1
        var_pct = div(var, n1)
        sig = rubrique_sig(c)
        bg.append({
            "compte": c, "libelle": r["libelle"], "n": n, "n1": n1,
            "var": 0.0 if var == 0 else var, "var_pct": var_pct, "var_pct_abs": abs(var_pct),
            "commentaire": commentaires.get(c, ""),
            "sig": sig, "rang": RANG.get(sig) if sig else None,
            "mouvemente": not (arrondi(n1, 2) == 0 and arrondi(n, 2) == 0),
        })
    return bg


def somme(bg, prefixes, col="n"):
    """Somme des soldes des comptes qui commencent par l'un des préfixes."""
    if isinstance(prefixes, str):
        prefixes = (prefixes,)
    return sum(r[col] for r in bg if r["compte"].startswith(tuple(prefixes)))


def resultat(bg, col="n"):
    """Résultat de l'exercice = -(somme des classes 6 et 7) (Bal_Comparative E4 / F4)."""
    return -somme(bg, ("6", "7"), col)


def libelle_resultat(r, suffixe):
    if r < 0:
        return f"Déficit {suffixe}"
    return f"Bénéfice {suffixe}" if r > 0 else f"Résultat {suffixe}"


def extraire(bg, filtre):
    """Les lignes de la balance retenues par un filtre sur le numéro de compte, triées par compte."""
    return [r for r in bg if filtre(r["compte"])]
