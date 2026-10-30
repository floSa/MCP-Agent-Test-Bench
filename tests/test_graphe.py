"""Niveau 2 — le StateGraph, avec un faux LLM et de simples outils Python."""

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from agent.evenements import iter_evenements
from agent.graphe import construire_graphe
from faux_llm import FauxLLM, appel_outil


@tool
def additionner(a: float, b: float) -> float:
    """Additionne deux nombres."""
    return a + b


async def _evenements(reponses, outils, question="12 + 30 ?", limite=25):
    graphe = construire_graphe(FauxLLM(reponses=reponses), outils)
    return [e async for e in iter_evenements(graphe, question, limite)]


async def test_boucle_outil_puis_reponse():
    evenements = await _evenements(
        [appel_outil("additionner", a=12, b=30), AIMessage("Le résultat est 42.")],
        [additionner])
    assert [e["type"] for e in evenements] == [
        "appel_outil", "resultat_outil", "reponse", "fin"]
    assert evenements[0]["arguments"] == {"a": 12, "b": 30}
    assert evenements[1]["contenu"] == "42.0"
    assert evenements[-1]["reponse"] == "Le résultat est 42."


async def test_reponse_directe_sans_outil():
    evenements = await _evenements([AIMessage("Bonjour !")], [additionner])
    assert [e["type"] for e in evenements] == ["reponse", "fin"]


async def test_garde_fou_limite_etapes():
    """Un modèle qui redemande un outil sans fin est coupé par la limite."""
    evenements = await _evenements([appel_outil("additionner", a=1, b=1)],
                                   [additionner], limite=6)
    assert evenements[-2]["type"] == "erreur"
    assert "limite" in evenements[-2]["detail"]
    assert evenements[-1]["type"] == "fin" and evenements[-1]["reponse"] == ""
