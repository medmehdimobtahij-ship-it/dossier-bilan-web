"""Tests du mode démo : dossiers fictifs cohérents, connexion sans mot de passe, services externes coupés."""
import os
import sys
import tempfile

import pytest

ICI = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(ICI, "..", "serveur"))

import demo  # noqa: E402
from moteur import calculer  # noqa: E402


@pytest.mark.parametrize("d", demo.dossiers(), ids=lambda d: d["siren"])
def test_dossiers_demo_coherents(d):
    """Chaque dossier de démo passe les contrôles comptables : balances équilibrées, SIG = résultat,
    affectation N-1 justifiée, TVA cadrée sur le solde et sur les flux."""
    r = calculer(d)
    niveaux = {c["cle"]: c["niveau"] for c in r["controles"]}
    for cle in ("equilibre_n", "equilibre_n1", "sig_resultat", "sig_resultat_n1", "affectation_n1", "resultat_affecte"):
        assert niveaux[cle] == "ok", cle
    for cle, col in r["tva"]["flux"]["colonnes"].items():
        assert col["difference"] == pytest.approx(0, abs=0.01), cle
    assert not r["tva"]["recap"]["mois_manquants"]
    assert len(r["balance"]["lignes"]) > 25


def test_dossiers_demo_manifestement_fictifs():
    for d in demo.dossiers():
        assert "(fictif)" in d["nom"] and d["siren"].startswith("999")


@pytest.fixture()
def site_demo(monkeypatch):
    monkeypatch.setenv("BILAN_DATA", tempfile.mkdtemp())
    monkeypatch.setenv("BILAN_DEMO", "1")
    for m in ("stockage", "comptazap", "comptes", "pennylane", "demo", "app"):
        sys.modules.pop(m, None)
    import app as module_app
    yield module_app.creer_app().test_client()
    monkeypatch.delenv("BILAN_DEMO")
    for m in ("stockage", "comptazap", "comptes", "pennylane", "demo", "app"):
        sys.modules.pop(m, None)


def test_demo_bout_en_bout(site_demo):
    c = site_demo
    cfg = c.get("/api/config").get_json()
    assert cfg["demo"] and [x["identifiant"] for x in cfg["comptes"]] == ["demo"]
    assert c.post("/api/connexion", json={"identifiant": "demo"}).status_code == 200
    dossiers = c.get("/api/dossiers").get_json()["dossiers"]
    assert len(dossiers) == len(demo.SOCIETES)
    r = c.get(f"/api/dossiers/{dossiers[0]['id']}").get_json()
    assert r["resultats"]["balance"]["lignes"]
    H = {"X-Bilan": "1"}
    assert c.get("/api/pennylane").status_code == 403
    assert c.post("/api/connecteur/code", headers=H).status_code == 403
    assert c.get("/api/poste/config", headers={"Authorization": "Bearer DBL-x"}).status_code == 403
    assert c.post("/api/mot-de-passe", json={"ancien": "demo", "nouveau": "x" * 12}, headers=H).status_code == 403
    assert c.get(f"/api/dossiers/{dossiers[0]['id']}/export.xlsx").status_code == 200
