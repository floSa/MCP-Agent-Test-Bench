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


def test_outils_decouverts_sur_les_deux_serveurs():
    noms = {o["nom"] for o in httpx.get(f"{AGENT_URL}/outils", timeout=30).json()}
    assert {"additionner", "multiplier",
            "mettre_en_majuscules", "compter_mots"} <= noms


def test_le_llm_utilise_un_outil_mcp():
    reponse = httpx.post(f"{AGENT_URL}/chat",
                         json={"question": "Combien font 12 plus 30 ?"},
                         timeout=DELAI)
    assert reponse.status_code == 200
    donnees = reponse.json()
    appels = [e["nom"] for e in donnees["etapes"] if e["type"] == "appel_outil"]
    assert "additionner" in appels, donnees
    assert "42" in donnees["reponse"]


def test_flux_sse():
    types = []
    with httpx.stream("POST", f"{AGENT_URL}/chat/stream",
                      json={"question": "Mets « salut » en majuscules"},
                      timeout=DELAI) as flux:
        for ligne in flux.iter_lines():
            if ligne.startswith("data: "):
                types.append(json.loads(ligne[6:])["type"])
    assert "appel_outil" in types and types[-1] == "fin"
