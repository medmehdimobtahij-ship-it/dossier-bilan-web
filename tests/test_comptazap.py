"""Tests du lien ComptaZap : lecture des cases d'une CA3, réception par le site, choix des déclarations, import."""
import os
import sys
import tempfile

import pytest

ICI = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ICI, "..", "connecteur"))
sys.path.insert(0, os.path.join(ICI, "..", "serveur"))

import lecture_tva as L  # noqa: E402


def mots(lignes):
    """Mots positionnés comme sur le PDF d'impots.gouv : (x0, y0, x1, y1, texte)."""
    out = []
    for y, elements in lignes:
        for x, t in elements:
            out.append((x, y, x + 8 * len(t), y + 8, t))
    return out


def test_lecture_par_position():
    page = mots([
        (255, [(27, "A1"), (60, "Ventes"), (529, "105"), (545, "223")]),
        (751, [(28, "08"), (94, "20"), (458, "20"), (469, "093"), (538, "4"), (545, "019")]),   # le taux « 20 » n'est pas un montant
        (428, [(28, "16"), (169, "08"), (538, "8"), (545, "752")]),                             # « lignes 08 à 5B » non plus
        (503, [(28, "20"), (545, "198")]),
        (697, [(28, "25"), (119, "23"), (538, "1"), (545, "305")]),
    ])
    c = L.lire_cases([page])
    assert c["A1"] == {"droite": 105223}
    assert c["08"] == {"base": 20093, "droite": 4019}
    assert c["16"] == {"droite": 8752}
    r = L.vers_recap(c)
    assert r["A1"] == {"base": 105223} and r["08"] == {"base": 20093, "taxe": 4019} and r["20"] == {"base": 198}


def test_controle():
    assert L.controler({"nette": 1305, "credit": 0, "neant": False}, 1305.0, False)[0]
    assert L.controler({"nette": 0, "credit": 22952, "neant": False}, 22952.0, True)[0]
    assert L.controler({"nette": 0, "credit": 0, "neant": True}, 0, False)[0]
    ok, msg = L.controler({"nette": 1300, "credit": 0, "neant": False}, 1305.0, False)
    assert not ok and "1300" in msg


def test_ca12_vers_ca3():
    c = L.ca12_vers_cases_ca3({"5A": {"base": 25058, "droite": 5012}, "AC": {"base": 5676, "droite": 1135}, "23": {"droite": 499},
                               "20": {"droite": 3292}, "28": {"droite": 2624}})
    assert c["08"] == {"base": 25058, "droite": 5012} and c["A3"]["base"] == 5676 and c["19"] == {"droite": 499} and c["28"] == {"droite": 2624}


@pytest.fixture()
def site(monkeypatch):
    data = tempfile.mkdtemp()
    monkeypatch.setenv("BILAN_DATA", data)
    monkeypatch.setenv("BILAN_SANS_MDP", "1")
    for m in ("stockage", "comptazap", "comptes", "pennylane", "app"):
        sys.modules.pop(m, None)
    import comptes
    comptes.initialiser()
    import app as module_app
    a = module_app.creer_app()
    c = a.test_client()
    c.post("/api/connexion", json={"identifiant": "admin"})
    return c


def decl(debut, fin, montant, depot, type_="Déclaration initiale", ok=True, base_a1=1000):
    return {"siren": "123456789", "client": "TEST", "formulaire": "CA3", "periode_debut": debut, "periode_fin": fin, "type_depot": type_,
            "date_depot": depot, "montant": montant, "is_credit": False, "controle_ok": ok, "controle_msg": "" if ok else "écart",
            "recap": {"A1": {"base": base_a1}, "08": {"base": base_a1, "taxe": base_a1 // 5}}, "pdf_sha": "", "pdf_nom": ""}


def test_connecteur_bout_en_bout(site):
    H = {"X-Bilan": "1"}
    assert site.get("/api/poste/config", headers={"Authorization": "Bearer DBL-faux"}).status_code == 401
    code = site.post("/api/connecteur/code", headers=H).get_json()["code"]
    P = {"Authorization": f"Bearer {code}"}
    assert site.get("/api/poste/config", headers=P).status_code == 200
    declarations = [
        decl("01/01/2025", "31/03/2025", 200, "20/04/2025 10:00:00", base_a1=1000),                       # trimestre 1
        decl("01/01/2025", "31/03/2025", 300, "02/06/2025 10:00:00", "Déclaration rectificative", base_a1=1500),  # la remplace
        decl("01/04/2025", "30/06/2025", 100, "20/07/2025 10:00:00", ok=False),                           # contrôle KO : écartée
        decl("01/07/2025", "30/09/2025", 100, "20/10/2025 10:00:00"),
        decl("01/10/2025", "31/12/2025", 100, "20/01/2026 10:00:00"),
        decl("01/01/2026", "31/03/2026", 100, "20/04/2026 10:00:00"),                                     # hors exercice
    ]
    r = site.post("/api/poste/tva", json={"declarations": declarations, "poste": "PC-TEST"}, headers=P).get_json()
    assert r["recues"] == 6
    did = site.post("/api/dossiers", json={"nom": "TEST", "siren": "123 456 789", "cloture": "2025-12-31"}, headers=H).get_json()["id"]
    liste = site.get(f"/api/dossiers/{did}/comptazap").get_json()["declarations"]
    assert len(liste) == 5 and sum(x["retenue"] for x in liste) == 4
    v = site.get(f"/api/dossiers/{did}").get_json()["dossier"]["version"]
    d = site.post(f"/api/dossiers/{did}/tva/comptazap", json={"version": v}, headers=H).get_json()
    rc = d["resultats"]["tva"]["recap"]
    assert rc["totaux"]["A1"] == 1500 + 1000 + 1000          # la rectificative, sans le trimestre écarté
    assert rc["mois_manquants"] == ["04-2025", "05-2025", "06-2025"]  # seul le trimestre écarté manque
    assert d["saisies"]["tva"]["source"]["origine"] == "ComptaZap" and len(d["saisies"]["tva"]["source"]["ecartees"]) == 1


def test_sans_siren(site):
    H = {"X-Bilan": "1"}
    did = site.post("/api/dossiers", json={"nom": "SANS SIREN", "cloture": "2025-12-31"}, headers=H).get_json()["id"]
    r = site.post(f"/api/dossiers/{did}/tva/comptazap", json={}, headers=H)
    assert r.status_code == 422 and "SIREN" in r.get_json()["erreur"]
