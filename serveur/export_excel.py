"""Export du dossier calculé en classeur Excel (valeurs, sans formules) : pour archiver ou transmettre le dossier."""
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

ENCRE = Font(bold=True, color="FFFFFF")
FOND = PatternFill("solid", fgColor="111214")
GRAS = Font(bold=True)
FIN = Side(style="thin", color="D0D3D8")
MONTANT = '#,##0.00;[Red]-#,##0.00'
POURCENT = '0.0%'


def _feuille(wb, titre, entetes, lignes, formats=None, largeurs=None):
    ws = wb.create_sheet(titre[:31])
    ws.append(entetes)
    for j in range(1, len(entetes) + 1):
        c = ws.cell(1, j)
        c.font, c.fill, c.alignment = ENCRE, FOND, Alignment(vertical="center", wrap_text=True)
    for l in lignes:
        ws.append(l)
    formats = formats or {}
    for j, fmt in formats.items():
        for i in range(2, ws.max_row + 1):
            ws.cell(i, j).number_format = fmt
    for j in range(1, len(entetes) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (largeurs or {}).get(j, 16)
    ws.freeze_panes = "A2"
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for c in row:
            c.border = Border(bottom=FIN)
    return ws


def exporter(d, r):
    wb = Workbook()
    wb.remove(wb.active)
    i = r["infos"]
    synth = wb.create_sheet("Synthèse")
    synth.append([f"Dossier bilan {d['nom']}"])
    synth["A1"].font = Font(bold=True, size=14)
    synth.append([f"Exercice du {i['debut_exercice']} au {i['cloture']}"])
    synth.append([])
    synth.append(["Contrôle", "État", "Détail"])
    for c in synth[4]:
        c.font, c.fill = ENCRE, FOND
    for c in r["controles"]:
        synth.append([c["titre"], {"ok": "OK", "alerte": "À regarder", "erreur": "Erreur"}[c["niveau"]], c["detail"]])
    synth.append([])
    for g in r["mail"]["groupes"]:
        synth.append([g["titre"], "N", "N-1"])
        synth.cell(synth.max_row, 1).font = GRAS
        for l in g["lignes"]:
            synth.append([l["libelle"], l["n"], l["n1"]])
            for j in (2, 3):
                synth.cell(synth.max_row, j).number_format = POURCENT if l["pourcentage"] else MONTANT
    synth.column_dimensions["A"].width, synth.column_dimensions["B"].width, synth.column_dimensions["C"].width = 48, 18, 60

    b = r["balance"]["lignes"]
    _feuille(wb, "Balance", ["Compte", "Libellé", "Solde N", "Solde N-1", "Variation", "Variation %", "Rubrique SIG", "Commentaire"],
             [[x["compte"], x["libelle"], x["n"], x["n1"], x["var"], x["var_pct"], (x["sig"] or "").strip(), x["commentaire"]] for x in b],
             {3: MONTANT, 4: MONTANT, 5: MONTANT, 6: POURCENT}, {2: 40, 7: 40, 8: 40})
    lignes = []
    for cy in r["cycles"]:
        for x in cy["lignes"]:
            lignes.append([cy["titre"], x["compte"], x["libelle"], x["n"], x["n1"], x["var"], x["statut"], x["note"]])
    _feuille(wb, "Révision", ["Cycle", "Compte", "Libellé", "Solde N", "Solde N-1", "Variation", "Statut", "Commentaire"], lignes,
             {4: MONTANT, 5: MONTANT, 6: MONTANT}, {1: 24, 3: 40, 8: 50})
    _feuille(wb, "SIG", ["", "Libellé", "N", "% CA", "N-1", "% CA", "Variation", "Variation %"],
             [[l["signe"], l["libelle"], l["n"], l["pct_n"], l["n1"], l["pct_n1"], l["var"], l["var_pct"]] for l in r["sig"]["lignes"]],
             {3: MONTANT, 4: POURCENT, 5: MONTANT, 6: POURCENT, 7: MONTANT, 8: POURCENT}, {2: 52})
    cap = r["capitaux"]
    _feuille(wb, "Capitaux", ["Compte", "Solde N-1", "Variation", "Solde N", "Alerte"],
             [[l["libelle"], l["n1"], l["var"], l["n"], l["alerte"]] for l in cap["lignes"]], {2: MONTANT, 3: MONTANT, 4: MONTANT}, {1: 44, 5: 30})
    ag = r["ago_n"]
    a = ag["affectation"]
    _feuille(wb, "Affectation N", ["Élément", "Montant"],
             [["Résultat à affecter", r["balance"]["resultat_n"]], [a["libelle_distribuable"], a["distribuable"]],
              ["Réserve légale", a["reserve_legale"]], ["Réserve statutaire", a["reserve_statutaire"]],
              ["Réserves réglementées", a["reserves_reglementees"]], ["Autres réserves", a["autres_reserves"]],
              ["Dividendes", a["dividendes"]], ["Compte courant d'associé", a["compte_courant"]],
              ["Report à nouveau créditeur", a["ran_crediteur"]], ["Report à nouveau débiteur", a["ran_debiteur"]]],
             {2: MONTANT}, {1: 40})
    rep = ag["repartition"]["associes"]
    _feuille(wb, "Dividendes N", ["Associé", "Parts", "%", "Dividende brut", "Base PS (2BH)", "Base cotisations (2CG)", "PS", "Précompte 12,8 %", "Net versé"],
             [[x["nom"], x["parts"], x["pct"], x["retenu"], x["base_ps"], x["base_cotis"], x["ps"], x["precompte"], x["net"]] for x in rep if x["parts"] or x["retenu"]],
             {3: POURCENT, 4: MONTANT, 5: MONTANT, 6: MONTANT, 7: MONTANT, 8: MONTANT, 9: MONTANT}, {1: 28})
    f = r["fiscal"]
    _feuille(wb, "Résultat fiscal", ["Élément", "Montant"],
             [["Bénéfice comptable", f["benefice"]], ["Déficit comptable", f["deficit"]], ["Total des réintégrations", f["total_reintegrations"]],
              ["Total des déductions", f["total_deductions"]], ["Résultat fiscal avant imputation", f["avant_imputation"]],
              ["Déficit antérieur", f["deficit_anterieur"]], ["Déficit imputé", f["deficit_impute"]], ["Déficit restant à reporter", f["deficit_restant"]],
              ["Résultat fiscal", f["apres_imputation"]], ["IS au taux réduit", f["is_taux_reduit"]], ["IS au taux normal", f["is_taux_normal"]],
              ["IS total", f["is_total"]], ["Résultat net comptable ajusté", f["resultat_net_ajuste"]]], {2: MONTANT}, {1: 40})
    recap = r["tva"]["recap"]
    codes = ["A1", "A2", "A3", "B2", "E1", "E2", "08", "08_taxe", "09", "09_taxe", "9B", "9B_taxe", "16", "19", "20", "22", "23", "25", "28"]
    _feuille(wb, "TVA", ["Ligne"] + [c["libelle"] for c in recap["colonnes"]] + ["Total"],
             [[k] + [c["valeurs"].get(k, 0) for c in recap["colonnes"]] + [recap["totaux"].get(k, 0)] for k in codes],
             {j: MONTANT for j in range(2, len(recap["colonnes"]) + 3)})
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
