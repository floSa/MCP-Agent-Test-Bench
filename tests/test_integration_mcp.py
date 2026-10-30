"""Niveau 3 — de VRAIS serveurs MCP en HTTP + le graphe, avec un faux LLM.

Vérifie le câblage réel : mcp_servers.json -> client MCP -> outils fusionnés
de plusieurs serveurs -> appel d'outil à travers le réseau.
"""

import json
import os
import pathlib
import socket
import subprocess
import sys
import time

import httpx
import pytest
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.evenements import iter_evenements
from agent.graphe import construire_graphe
from faux_llm import FauxLLM, appel_outil

SERVEURS = pathlib.Path(__file__).resolve().parent.parent / "mcp_servers"


def _port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def serveurs_mcp():
    """Lance maths.py et texte.py sur des ports libres, puis les arrête."""
    ports, processus = {}, []
    for nom in ("maths", "texte"):
        ports[nom] = _port_libre()
        processus.append(subprocess.Popen(
            [sys.executable, str(SERVEURS / f"{nom}.py")],
            env={**os.environ, "PORT": str(ports[nom])},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    try:
        for port in ports.values():
            for _ in range(50):
                try:
                    httpx.get(f"http://127.0.0.1:{port}/sante", timeout=1)
                    break
                except httpx.HTTPError:
                    time.sleep(0.2)
            else:
                pytest.fail(f"serveur MCP injoignable sur le port {port}")
        yield {nom: {"transport": "streamable_http",
                     "url": f"http://127.0.0.1:{port}/mcp/"}
               for nom, port in ports.items()}
    finally:
        for p in processus:
            p.terminate()


async def test_outils_de_plusieurs_serveurs_fusionnes(serveurs_mcp):
    outils = await MultiServerMCPClient(serveurs_mcp).get_tools()
    assert {o.name for o in outils} == {
        "additionner", "multiplier", "mettre_en_majuscules", "compter_mots"}


async def test_graphe_appelle_un_vrai_serveur_mcp(serveurs_mcp):
    outils = await MultiServerMCPClient(serveurs_mcp).get_tools()
    llm = FauxLLM(reponses=[appel_outil("multiplier", a=4, b=3),
                            AIMessage("Le résultat est 12.")])
    graphe = construire_graphe(llm, outils)
    evenements = [e async for e in iter_evenements(graphe, "4 fois 3 ?")]
    resultat = next(e for e in evenements if e["type"] == "resultat_outil")
    assert resultat["nom"] == "multiplier"
    assert float(resultat["contenu"]) == 12
    assert evenements[-1]["reponse"] == "Le résultat est 12."


def test_fichier_de_config_par_defaut_valide():
    from agent import config
    serveurs = config.charger_serveurs_mcp()
    assert serveurs and all("url" in s and "transport" in s
                            for s in serveurs.values())
