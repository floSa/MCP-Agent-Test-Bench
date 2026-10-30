"""Niveau 3 — le graphe + l'arbitre, avec un FAUX LLM scripté et le VRAI serveur MCP.

C'est ici qu'on prouve que l'agent ne peut pas tricher : on scénarise des LLM
honnêtes, tricheurs ou maladroits, et on vérifie que l'arbitre laisse passer
les premiers et bloque les autres. Tout est déterministe (aucun vrai LLM).
"""

from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.evenements import iter_evenements
from agent.graphe import construire_graphe
from faux_llm import FauxLLM, appel_outil

QUESTION = "trois fois quatre plus deux"

SCENARIO_HONNETE = [
    appel_outil("convertir_texte_en_formule", texte=QUESTION),
    appel_outil("trouver_calcul_prioritaire", formule="3 * 4 + 2"),
    appel_outil("calculer", gauche=3, operateur="*", droite=4),
    appel_outil("remplacer_calcul_par_resultat",
                formule="3 * 4 + 2", sous_expression="3 * 4", valeur=12),
    appel_outil("trouver_calcul_prioritaire", formule="12 + 2"),
    appel_outil("calculer", gauche=12, operateur="+", droite=2),
    appel_outil("remplacer_calcul_par_resultat",
                formule="12 + 2", sous_expression="12 + 2", valeur=14),
    AIMessage("REPONSE FINALE: 14"),
]


async def _jouer(url_mcp, scenario, limite=40):
    outils = await MultiServerMCPClient(
        {"calculatrice": {"transport": "streamable_http", "url": url_mcp}}
    ).get_tools()
    graphe = construire_graphe(FauxLLM(reponses=scenario), outils)
    return [e async for e in iter_evenements(graphe, QUESTION, limite)]


def _refus(evenements):
    return [e for e in evenements if e["type"] == "refus_arbitre"]


async def test_llm_honnete_est_valide(url_mcp):
    evenements = await _jouer(url_mcp, SCENARIO_HONNETE)
    fin = evenements[-1]
    assert fin["valide"] is True
    assert fin["reponse"] == 14
    assert fin["formule"] == "3 * 4 + 2"
    assert _refus(evenements) == []


async def test_llm_tricheur_est_refuse(url_mcp):
    """Répond de tête, sans outil : refusé en boucle, jamais validé."""
    evenements = await _jouer(url_mcp, [AIMessage("REPONSE FINALE: 14")],
                              limite=10)
    assert _refus(evenements)
    assert "aucune formule" in _refus(evenements)[0]["detail"].lower()
    assert evenements[-1]["valide"] is False
    assert evenements[-1]["reponse"] is None


async def test_mauvais_calcul_prioritaire_refuse_puis_rattrape(url_mcp):
    """Le modèle veut d'abord 4 + 2 (faux), l'arbitre refuse, il se corrige."""
    scenario = [
        appel_outil("convertir_texte_en_formule", texte=QUESTION),
        appel_outil("trouver_calcul_prioritaire", formule="3 * 4 + 2"),
        appel_outil("calculer", gauche=4, operateur="+", droite=2),      # refusé
        *SCENARIO_HONNETE[2:],
    ]
    evenements = await _jouer(url_mcp, scenario)
    assert len(_refus(evenements)) == 1
    assert "calcul prioritaire" in _refus(evenements)[0]["detail"]
    assert evenements[-1]["valide"] is True and evenements[-1]["reponse"] == 14


async def test_reponse_fausse_refusee(url_mcp):
    """Formule bien réduite par les outils, mais nombre annoncé faux."""
    scenario = [*SCENARIO_HONNETE[:-1], AIMessage("REPONSE FINALE: 15"),
                AIMessage("REPONSE FINALE: 14")]
    evenements = await _jouer(url_mcp, scenario)
    refus = _refus(evenements)
    assert len(refus) == 1 and "ne correspond pas" in refus[0]["detail"]
    assert evenements[-1]["valide"] is True and evenements[-1]["reponse"] == 14
