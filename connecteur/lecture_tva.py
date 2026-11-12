"""Lecture des déclarations de TVA CA3 (formulaire 3310-CA3) téléchargées par ComptaZap depuis impots.gouv.

Le PDF d'impots.gouv contient du vrai texte : chaque case est une ligne qui commence par son numéro (A1, 08, 9B, 28…),
la base HT est dans la colonne du milieu, la taxe (ou le montant seul) dans la colonne de droite. On repère donc les
mots par leur position, jamais par leur ordre dans le texte (un taux « 20 » ou un renvoi « lignes 08 à 5B » ne doit
pas être pris pour un montant).

Contrôle : la case 28 (TVA nette due) ou 25 (crédit de TVA, avant remboursement demandé) lue doit égaler le montant
que ComptaZap a enregistré pour la déclaration. Une déclaration qui ne passe pas ce contrôle est signalée, jamais utilisée en silence.
"""
import re

CODE = re.compile(r"^(?:[A-F][0-9]|0[89]|9B|1[0-9]|2[0-9]|2[A-E]|5B|T[1-7C]|TD|P[12]|I[1-6]|X[1-5]|Y[1-6]|Z[1-5]|AA|AB|3[0-2])$")
TAXABLES = {"08", "09", "9B", "10", "11", "T1", "T2", "TC", "T3", "T4", "T5", "T6", "T7", "P1", "P2", "I1", "I2", "I3", "I4", "I5", "I6"}
DEDUCTIBLES = {"19", "20", "21", "22", "2C"}
TAXE_DUE = {"15", "5B", "18"}
X_CODE_MAX = 45          # les numéros de case sont dans la marge gauche
X_MONTANTS_MIN = 380     # les montants commencent après le libellé
X_DROITE_MIN = 495       # colonne de droite (taxe, ou montant seul)
ECART_LIGNE = 3.5        # tolérance verticale pour dire « même ligne »


class ErreurLecture(Exception):
    pass


def _nombre(mots):
    """Les groupes de chiffres d'une colonne, dans l'ordre, en un entier : « 20 » « 093 » -> 20093."""
    txt = "".join(m for m in mots)
    txt = txt.replace(" ", "").replace("\xa0", "")
    negatif = txt.startswith("-")
    chiffres = re.sub(r"[^\d,]", "", txt).split(",")[0]
    if not chiffres:
        return None
    v = int(chiffres)
    return -v if negatif else v


CODE_CA12 = re.compile(r"^(?:[0-9]{2}|[0-9][A-Z]|[A-Z]{2}|[A-Z][0-9])$")
X_CODE_MAX_CA12 = 60     # quelques lignes de la CA12 (28, 33) sont en retrait


def lire_cases(pages, motif=CODE, x_code_max=X_CODE_MAX):
    """pages : pour chaque page, la liste des mots (x0, y0, x1, y1, texte). Renvoie {case: {"base": v, "droite": v}}."""
    cases = {}
    for mots in pages:
        codes = [(x0, y0, t) for x0, y0, x1, y1, t in mots if x0 < x_code_max and motif.match(t)]
        for _, yc, code in codes:
            base, droite = [], []
            for x0, y0, x1, y1, t in sorted(mots, key=lambda m: m[0]):
                if abs(y0 - yc) > ECART_LIGNE or x0 < X_MONTANTS_MIN:
                    continue
                if not re.fullmatch(r"-?[\d \xa0.,]+", t):
                    continue
                (droite if x0 >= X_DROITE_MIN else base).append(t)
            v = {}
            if base:
                v["base"] = _nombre(base)
            if droite:
                v["droite"] = _nombre(droite)
            if v and code not in cases:
                cases[code] = v
    return cases


def neant(texte):
    """Déclaration « néant » : la case de la première page est cochée (X seul sur sa ligne)."""
    return bool(re.search(r"déclaration\s*«\s*néant\s*»[^\n]*\n\s*X\s*\n", texte, re.I))


def vers_recap(cases):
    """Les cases au format du récapitulatif (même découpage que l'export Pennylane) : {code: {"base": x, "taxe": y}}."""
    out = {}
    for code, v in cases.items():
        if code == "acomptes":
            continue
        if code in TAXABLES:
            d = {}
            if v.get("base") is not None:
                d["base"] = v["base"]
            if v.get("droite") is not None:
                d["taxe"] = v["droite"]
        elif code in TAXE_DUE:
            d = {"taxe": v.get("droite", v.get("base"))}
        else:  # opérations (A1…F9), TVA déductible (19 à 2C) et totaux : colonne « Base HT » du récapitulatif
            d = {"base": v.get("droite", v.get("base"))}
        if any(x is not None for x in d.values()):
            out[code] = d
    return out


# CA12 (3517-S-CA12, déclaration annuelle) -> cases équivalentes de la CA3, pour que le récapitulatif et le cadrage
# des flux lisent les mêmes codes quel que soit le régime. (base ou taxe : la colonne lue dans la CA12)
CA12_VERS_CA3 = {
    "5A": "08", "06": "09", "6C": "9B", "07": "10", "08": "11",          # opérations imposables : base et taxe
    "AA": "B3", "AB": "B4", "AC": "A3", "11": "A2", "12": "A2", "13": "A2",
    "01": "F6", "02": "E1", "03": "E2", "3A": "E3", "04": "F2",           # opérations non imposables
    "18": "15", "AD": "5B", "19": "16",                                    # TVA brute
    "20": "20", "21": "21", "25": "21", "23": "19", "24": "22", "AE": "2C", "26": "23",  # TVA déductible
    "28": "28", "29": "25",                                                # TVA due / crédit
}


def ca12_vers_cases_ca3(cases12):
    out = {}
    for c12, c3 in CA12_VERS_CA3.items():
        v = cases12.get(c12)
        if not v:
            continue
        o = out.setdefault(c3, {})
        for col in ("base", "droite"):
            if v.get(col) is not None:
                o[col] = (o.get(col) or 0) + v[col]
    return out


def lire_pdf(chemin):
    """{"formulaire", "cases" (numérotation CA3), "recap", "neant", "nette", "credit"} d'un PDF de CA3 ou de CA12."""
    import pymupdf
    try:
        doc = pymupdf.open(chemin)
    except Exception as e:
        raise ErreurLecture(f"PDF illisible ({e.__class__.__name__})") from e
    with doc:
        texte = "\n".join(p.get_text() for p in doc)
        pages = [[(w[0], w[1], w[2], w[3], w[4]) for w in p.get_text("words")] for p in doc]
    if "3310-CA3" in texte or "3310 CA3" in texte:
        formulaire = "CA3"
        cases = lire_cases(pages)
        nette = (cases.get("28") or {}).get("droite") or 0
        credit = (cases.get("25") or {}).get("droite") or 0
    elif re.search(r"3517[\s-]*S[\s-]*CA12", texte) or "CA12" in texte:
        formulaire = "CA12"
        cases12 = lire_cases(pages, CODE_CA12, X_CODE_MAX_CA12)
        cases = ca12_vers_cases_ca3(cases12)
        # Contrôle sur le solde après acomptes : 33 (solde dû) ou 35 (solde excédentaire), comme ComptaZap
        nette = (cases12.get("33") or {}).get("droite") or 0
        credit = (cases12.get("35") or cases12.get("29") or {}).get("droite") or 0
        cases["acomptes"] = {"droite": (cases12.get("30") or {}).get("droite") or 0}
    else:
        raise ErreurLecture("formulaire non reconnu (ni CA3 ni CA12)")
    est_neant = neant(texte) and not any(v.get("droite") or v.get("base") for c, v in cases.items() if c not in ("TD", "acomptes"))
    return {"formulaire": formulaire, "cases": cases, "recap": vers_recap(cases), "neant": est_neant, "nette": nette, "credit": credit}


def controler(lecture, montant, is_credit):
    """La case 28 (ou 25 pour un crédit) lue égale-t-elle le montant enregistré par ComptaZap ?"""
    attendu = int(round(float(montant or 0)))
    lu = lecture["credit"] if is_credit else lecture["nette"]
    if attendu == 0 and lecture["neant"]:
        return True, ""
    if lu == attendu:
        return True, ""
    return False, f"montant lu {lu} € ≠ montant ComptaZap {attendu} €"
