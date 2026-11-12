"""Import de fichiers (Excel .xlsx ou texte .csv / collé depuis Excel) : balance, récapitulatif TVA Pennylane, journal de paie.

Les colonnes sont reconnues par leur intitulé, pas par leur position : l'export peut venir de Pennylane, d'un autre
logiciel, ou de l'ancien onglet BalanceP de l'Excel.
"""
import csv
import io
import re
import unicodedata

from moteur.outils import nombre
from moteur.referentiel import MOIS_FR


class ErreurImport(Exception):
    pass


def _simplifier(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def lire_tableau(contenu, nom_fichier=""):
    """Le fichier en liste de lignes (listes de cellules). xlsx : première feuille non vide ; sinon texte."""
    if nom_fichier.lower().endswith((".xlsx", ".xlsm")) or contenu[:2] == b"PK":
        import openpyxl
        try:
            wb = openpyxl.load_workbook(io.BytesIO(contenu), data_only=True, read_only=True)
        except Exception as e:  # fichier abîmé ou protégé
            raise ErreurImport(f"Fichier Excel illisible ({e.__class__.__name__}).") from e
        for ws in wb.worksheets:
            lignes = [list(r) for r in ws.iter_rows(values_only=True)]
            if any(any(c not in (None, "") for c in l) for l in lignes):
                return lignes
        raise ErreurImport("Le fichier Excel est vide.")
    if isinstance(contenu, bytes):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                texte = contenu.decode(enc)
                break
            except UnicodeDecodeError:
                continue
    else:
        texte = contenu
    if not texte.strip():
        raise ErreurImport("Le fichier est vide.")
    echantillon = texte[:5000]
    sep = "\t" if "\t" in echantillon else (";" if echantillon.count(";") >= echantillon.count(",") else ",")
    return [l for l in csv.reader(io.StringIO(texte), delimiter=sep)]


def _trouver_entete(lignes, reconnaitre, minimum=2):
    for i, l in enumerate(lignes[:40]):
        cols = reconnaitre([_simplifier(c) for c in l])
        if len([v for v in cols.values() if v is not None]) >= minimum:
            return i, cols
    return None, None


# ---------------------------------------------------------------------------------------------------------------
# Balance
# ---------------------------------------------------------------------------------------------------------------
def _colonnes_balance(entetes):
    def premiere(*motifs, exclure=()):
        for j, e in enumerate(entetes):
            if any(re.search(m, e) for m in motifs) and not any(re.search(x, e) for x in exclure):
                return j
        return None
    return {
        "compte": premiere(r"^(n )?(numero|num|n|no)( de)?( compte)?$", r"^compte$", r"^numero de compte", r"^n compte", r"^account", r"^number$"),
        "libelle": premiere(r"^libelle", r"^intitule", r"^label", r"^nom du compte", r"^designation"),
        "solde_n1": premiere(r"solde n 1", r"n 1$", r"precedent", r"anterieur"),
        "solde_n": premiere(r"^solde n$", r"^solde$", r"^solde (fin|final|cloture)", r"^balance$", r"solde n(?! 1)", exclure=(r"n 1",)),
        "debit": premiere(r"^(total )?debits?$", r"^mouvements? debit", r"^debit"),
        "credit": premiere(r"^(total )?credits?$", r"^mouvements? credit", r"^credit"),
        "solde_debiteur": premiere(r"solde debiteur"),
        "solde_crediteur": premiere(r"solde crediteur"),
    }


def balance(contenu, nom_fichier="", colonne_cible="les_deux"):
    """Lignes [{compte, libelle, solde_n, solde_n1}] d'un fichier de balance.

    Formats reconnus : « Numéro / Libellé / Solde N / Solde N-1 » (ancien onglet BalanceP), « Compte / Libellé /
    Débit / Crédit », « Solde débiteur / Solde créditeur », ou « Compte / Libellé / Solde ».
    colonne_cible : 'n' ou 'n1' quand le fichier ne contient qu'un exercice.
    """
    lignes = lire_tableau(contenu, nom_fichier)
    i, cols = _trouver_entete(lignes, _colonnes_balance)
    if i is None or cols["compte"] is None:
        raise ErreurImport("Colonnes introuvables : il faut au moins « Compte » (ou « Numéro ») et un solde ou débit/crédit.")
    out = []
    for l in lignes[i + 1:]:
        def cel(k):
            j = cols.get(k)
            return l[j] if j is not None and j < len(l) else None
        compte = cel("compte")
        if compte in (None, ""):
            continue
        if isinstance(compte, float) and compte.is_integer():
            compte = int(compte)
        compte = str(compte).strip().replace(" ", "")
        if not re.match(r"^[0-9]", compte) or _simplifier(compte).startswith("total"):
            continue  # lignes de total ou de titre
        if cols["solde_n"] is not None or cols["solde_n1"] is not None:
            sn, sn1 = nombre(cel("solde_n")), nombre(cel("solde_n1"))
        elif cols["solde_debiteur"] is not None:
            sn, sn1 = nombre(cel("solde_debiteur")) - nombre(cel("solde_crediteur")), 0.0
        elif cols["debit"] is not None:
            sn, sn1 = nombre(cel("debit")) - nombre(cel("credit")), 0.0
        else:
            raise ErreurImport("Aucune colonne de solde ni de débit / crédit.")
        if colonne_cible == "n1" and cols["solde_n1"] is None:
            sn, sn1 = 0.0, sn
        out.append({"compte": compte, "libelle": str(cel("libelle") or "").strip(), "solde_n": round(sn, 2), "solde_n1": round(sn1, 2)})
    if not out:
        raise ErreurImport("Aucune ligne de compte trouvée sous l'en-tête.")
    return out


def fusionner(n, n1):
    """Réunit une balance N et une balance N-1 importées séparément."""
    par = {}
    for l in n:
        par.setdefault(l["compte"], {"compte": l["compte"], "libelle": l["libelle"], "solde_n": 0.0, "solde_n1": 0.0})["solde_n"] += l["solde_n"]
    for l in n1:
        o = par.setdefault(l["compte"], {"compte": l["compte"], "libelle": l["libelle"], "solde_n": 0.0, "solde_n1": 0.0})
        o["solde_n1"] += l["solde_n1"] or l["solde_n"]
    return [par[k] for k in sorted(par)]


# ---------------------------------------------------------------------------------------------------------------
# Récapitulatif des déclarations de TVA (export Pennylane : une ligne par case, deux colonnes par mois)
# ---------------------------------------------------------------------------------------------------------------
def _mois(texte):
    """'Janvier 2025' / '01/2025' / '2025-01' / date -> 'AAAA-MM', sinon None."""
    if texte is None:
        return None
    if hasattr(texte, "year"):
        return f"{texte.year}-{texte.month:02d}"
    t = _simplifier(texte)
    m = re.match(r"^([a-z]+) (\d{4})$", t)
    if m and m.group(1) in {_simplifier(k) for k in MOIS_FR}:
        num = next(v for k, v in MOIS_FR.items() if _simplifier(k) == m.group(1))
        return f"{m.group(2)}-{num:02d}"
    m = re.match(r"^(\d{1,2}) (\d{4})$", t) or re.match(r"^(\d{4}) (\d{1,2})$", t)
    if m:
        a, b = m.groups()
        return f"{a}-{int(b):02d}" if len(a) == 4 else f"{b}-{int(a):02d}"
    return None


def recap_tva(contenu, nom_fichier=""):
    """{'AAAA-MM': {code: {'base': x, 'taxe': y}}} depuis l'export « Récapitulatif des déclarations » de Pennylane."""
    lignes = lire_tableau(contenu, nom_fichier)
    for i, l in enumerate(lignes[:40]):
        mois = [(j, _mois(c)) for j, c in enumerate(l)]
        mois = [(j, m) for j, m in mois if m]
        if len(mois) >= 2:
            entete, colonnes = i, mois
            break
    else:
        raise ErreurImport("Aucune colonne de mois trouvée (ex. « Janvier 2025 »).")
    # Deux colonnes par mois : la première « Base HT », la seconde « Taxe due »
    vus, roles = {}, {}
    for j, m in colonnes:
        vus[m] = vus.get(m, 0) + 1
        roles[j] = (m, "base" if vus[m] == 1 else "taxe")
    col_code = None
    for i in range(entete + 1, min(entete + 30, len(lignes))):
        for j, c in enumerate(lignes[i]):
            if isinstance(c, str) and re.match(r"^[A-Z]?[0-9][0-9A-Z]?$|^[A-Z][0-9]$", c.strip()):
                col_code = j
                break
        if col_code is not None:
            break
    if col_code is None:
        raise ErreurImport("Colonne des numéros de ligne (A1, 08, 9B…) introuvable.")
    recap = {}
    for l in lignes[entete + 1:]:
        if col_code >= len(l) or l[col_code] in (None, ""):
            continue
        code = str(l[col_code]).strip()
        if isinstance(l[col_code], (int, float)):
            code = f"{int(l[col_code]):02d}"
        for j, (m, role) in roles.items():
            if j < len(l) and l[j] not in (None, "", "-"):
                recap.setdefault(m, {}).setdefault(code, {})[role] = nombre(l[j])
    if not recap:
        raise ErreurImport("Aucun montant trouvé dans le récapitulatif.")
    return recap


# ---------------------------------------------------------------------------------------------------------------
# Journal de paie (SILAE)
# ---------------------------------------------------------------------------------------------------------------
def journal_paie(contenu, nom_fichier=""):
    """[{code, libelle, salarial, patronal}] d'un journal de paie (colonnes Code, Libellé, Salarial, Patronal)."""
    lignes = lire_tableau(contenu, nom_fichier)

    def reconnaitre(e):
        def premiere(*motifs):
            return next((j for j, x in enumerate(e) if any(re.search(m, x) for m in motifs)), None)
        return {"code": premiere(r"^code"), "libelle": premiere(r"^libelle", r"^rubrique"),
                "salarial": premiere(r"^salarial$", r"^montant salarial", r"^part salariale"),
                "patronal": premiere(r"^patronal$", r"^montant patronal", r"^part patronale")}
    i, cols = _trouver_entete(lignes, reconnaitre, 3)
    if i is None:
        raise ErreurImport("Colonnes introuvables : Code, Libellé, Salarial, Patronal.")
    out = []
    for l in lignes[i + 1:]:
        def cel(k):
            j = cols.get(k)
            return l[j] if j is not None and j < len(l) else None
        lib = cel("libelle")
        if lib in (None, ""):
            continue
        out.append({"code": str(cel("code") or "").strip(), "libelle": str(lib).strip(),
                    "salarial": nombre(cel("salarial")), "patronal": nombre(cel("patronal"))})
    return out
