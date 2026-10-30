"""Niveau 4 — bout en bout : stack Docker complète + VRAI LLM.

Lancement : docker compose --profile e2e run --rm tests-e2e
"""

import json
import os

import httpx
import pytest

pytestmark = pytest.mark.e2e

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8080")
UI_URL = os.environ.get("UI_URL", "http://ui:8501")
DELAI = httpx.Timeout(600.0)


def test_sante():
    reponse = httpx.get(f"{AGENT_URL}/sante", timeout=10)
    assert reponse.status_code == 200 and reponse.json()["statut"] == "ok"


def test_ui_streamlit_en_ligne():
    assert httpx.get(f"{UI_URL}/_stcore/health", timeout=10).status_code == 200


def test_outils_decouverts():
    noms = {o["nom"] for o in httpx.get(f"{AGENT_URL}/outils", timeout=30).json()}
    assert {"convertir_texte_en_formule", "trouver_calcul_prioritaire",
            "calculer", "remplacer_calcul_par_resultat"} <= noms


def test_trois_fois_quatre_plus_deux():
    reponse = httpx.post(f"{AGENT_URL}/chat",
                         json={"question": "trois fois quatre plus deux"},
                         timeout=DELAI)
    assert reponse.status_code == 200
    donnees = reponse.json()
    assert donnees["valide"] is True, donnees
    assert abs(donnees["reponse"] - 14) < 1e-6
    assert donnees["formule"] == "3 * 4 + 2"


def test_flux_sse():
    types = []
    with httpx.stream("POST", f"{AGENT_URL}/chat/stream",
                      json={"question": "dix moins deux fois trois"},
                      timeout=DELAI) as flux:
        for ligne in flux.iter_lines():
            if ligne.startswith("data: "):
                types.append(json.loads(ligne[6:]))
    assert any(e["type"] == "appel_outil" for e in types)
    assert types[-1]["type"] == "fin" and types[-1]["valide"] is True
    assert abs(types[-1]["reponse"] - 4) < 1e-6
