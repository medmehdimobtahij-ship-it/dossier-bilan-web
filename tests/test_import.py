"""Tests de l'import des fichiers : formats de balance, récapitulatif TVA, journal de paie."""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "serveur"))

import import_fichier as I  # noqa: E402


def test_balance_format_balancep():
    t = "Numéro;Libellé;Solde N;Solde N-1\n101000;Capital;-1 000,00;-1000\n512000;Banque;1000;1000\nTotal;;0;0\n"
    l = I.balance(t.encode("utf-8"))
    assert l == [{"compte": "101000", "libelle": "Capital", "solde_n": -1000.0, "solde_n1": -1000.0},
                 {"compte": "512000", "libelle": "Banque", "solde_n": 1000.0, "solde_n1": 1000.0}]


def test_balance_debit_credit_et_titre():
    t = "Balance générale au 31/12/2025\n\nCompte\tIntitulé\tDébit\tCrédit\n401000\tFournisseurs\t100\t600\n606000\tAchats\t500\t0\n"
    l = I.balance(t.encode("cp1252"))
    assert [(x["compte"], x["solde_n"]) for x in l] == [("401000", -500.0), ("606000", 500.0)]


def test_balance_n1_seule():
    t = "Compte,Libellé,Solde\n512000,Banque,300\n"
    l = I.balance(t.encode(), colonne_cible="n1")
    assert l[0]["solde_n"] == 0 and l[0]["solde_n1"] == 300


def test_balance_xlsx():
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["N° compte", "Libellé", "Solde débiteur", "Solde créditeur"])
    ws.append([411000, "Clients", 1200, None])
    ws.append([706000, "Prestations", None, 1200])
    b = io.BytesIO()
    wb.save(b)
    l = I.balance(b.getvalue(), "balance.xlsx")
    assert [(x["compte"], x["solde_n"]) for x in l] == [("411000", 1200.0), ("706000", -1200.0)]


def test_balance_sans_colonne_compte():
    with pytest.raises(I.ErreurImport):
        I.balance(b"Nom;Montant\nA;1\n")


def test_fusion_n_et_n1():
    n = [{"compte": "512000", "libelle": "Banque", "solde_n": 10, "solde_n1": 0}]
    n1 = [{"compte": "512000", "libelle": "Banque", "solde_n": 0, "solde_n1": 4}, {"compte": "530000", "libelle": "Caisse", "solde_n": 0, "solde_n1": 1}]
    f = I.fusionner(n, n1)
    assert f == [{"compte": "512000", "libelle": "Banque", "solde_n": 10, "solde_n1": 4}, {"compte": "530000", "libelle": "Caisse", "solde_n": 0, "solde_n1": 1}]


def test_recap_tva_pennylane():
    t = ("Récapitulatif\n\nNuméro\tLignes de déclaration\tTotal\tTotal\tJanvier 2025\tJanvier 2025\tFévrier 2025\tFévrier 2025\n"
         "\tA - MONTANT DES OPÉRATIONS\t\t\t\t\t\t\n"
         "A1\tVentes\t300\t-\t100\t-\t200\t-\n08\tTaux normal 20%\t300\t-\t100\t-\t200\t-\n15\tTVA à reverser\t-\t5\t-\t5\t-\t-\n")
    r = I.recap_tva(t.encode("utf-8"))
    assert r["2025-01"]["A1"] == {"base": 100.0} and r["2025-02"]["08"] == {"base": 200.0}
    assert r["2025-01"]["15"] == {"taxe": 5.0}
    assert "2025-03" not in r


def test_journal_paie():
    t = "Code;Libellé;Nb salariés;Salarial;Patronal\n;Brut;2;50 000,00;\nSS001;Maladie;2;;3 500,00\n"
    j = I.journal_paie(t.encode("utf-8"))
    assert j[0] == {"code": "", "libelle": "Brut", "salarial": 50000.0, "patronal": 0.0}
    assert j[1]["patronal"] == 3500.0
