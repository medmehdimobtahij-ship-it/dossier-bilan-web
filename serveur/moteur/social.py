"""Cadrage social d'après le journal de paie SILAE (feuille Cadrage_Social_SILAE).

Le journal est collé tel quel (code de rubrique, libellé, montants salariaux et patronaux). Les cotisations patronales
sont regroupées par organisme selon les deux premières lettres du code, puis rapprochées des montants comptables saisis.
"""
import fnmatch

from .outils import egal, nombre

ORGANISMES = {"AA": "Retraite", "CH": "Cotisations URSSAF", "PR": "Prévoyance + mutuelle", "PS": "Prévoyance + mutuelle",
              "PX": "Prévoyance + mutuelle", "SS": "Cotisations URSSAF", "TC": "Cfp + taxe d'apprentissage",
              "TR": "Tickets restaurants"}
ELEMENTS = ["Brut", "Avantages en nature", "Indemnités de rupture", "Cfp + taxe d'apprentissage", "Prévoyance + mutuelle",
            "Retraite", "Tickets restaurants", "Cotisations URSSAF", "Provision CP (à la main)"]


def _code_correspond(code, motif):
    """Critère joker de SOMME.SI.ENS (« * » = n'importe quelle suite de caractères), sans tenir compte de la casse."""
    return fnmatch.fnmatchcase(str(code or "").upper(), motif.upper())


def cadrage(journal, saisies, organismes=None):
    s = saisies or {}
    orga = {**ORGANISMES, **(organismes or {})}
    lignes = []
    for l in journal or []:
        code = str(l.get("code") or "").strip()
        r2 = code[:2] if code else ""
        lignes.append({"code": code, "libelle": str(l.get("libelle") or "").strip(), "salarial": nombre(l.get("salarial")),
                       "patronal": nombre(l.get("patronal")), "r2": r2, "organisme": orga.get(r2, "") if r2 else ""})
    brut = next((l["salarial"] for l in lignes if egal(l["libelle"], "Brut")), None)
    paie = {
        "Brut": brut,
        "Avantages en nature": sum(l["salarial"] for l in lignes if _code_correspond(l["code"], "A*.b") and l["salarial"] > 0),
        "Indemnités de rupture": sum(l["salarial"] for l in lignes if _code_correspond(l["code"], "J*")),
    }
    for org in ("Cfp + taxe d'apprentissage", "Prévoyance + mutuelle", "Retraite", "Tickets restaurants", "Cotisations URSSAF"):
        paie[org] = sum(l["patronal"] for l in lignes if egal(l["organisme"], org))
    paie["Provision CP (à la main)"] = nombre(s.get("provision_cp"))
    compta = s.get("compta") or {}
    rappro = []
    for e in ELEMENTS:
        p = paie.get(e)
        c = nombre(compta.get(e))
        rappro.append({"element": e, "paie": p, "compta": c, "ecart": (p or 0.0) - c, "commentaire": (s.get("commentaires") or {}).get(e, "")})
    a_parametrer = sorted({l["r2"] for l in lignes if l["r2"] and l["r2"] not in orga})
    return {"lignes": lignes, "rapprochement": rappro, "codes_a_parametrer": a_parametrer, "brut_trouve": brut is not None}
