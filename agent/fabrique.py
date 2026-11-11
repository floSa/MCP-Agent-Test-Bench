"""Fabrique de l'agent : branche le LLM et les serveurs MCP sur le graphe.

C'est le SEUL endroit qui connaît à la fois la config, le client LLM et le
client MCP. Les outils sont découverts à chaque appel : ajouter un serveur dans
mcp_servers.json suffit, sans toucher au code.
"""

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

from agent import config
from agent.graphe import construire_graphe


def creer_modele() -> ChatOpenAI:
    """Client LLM : service central LLM-Service (API OpenAI)."""
    return ChatOpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY or "inutile",
        model=config.LLM_MODEL,
        temperature=0,
        timeout=300,
        extra_body=config.LLM_EXTRA_BODY or None,
    )


async def charger_outils() -> list:
    """Se connecte à tous les serveurs MCP et renvoie leurs outils fusionnés."""
    client = MultiServerMCPClient(config.charger_serveurs_mcp())
    return await client.get_tools()


async def creer_graphe():
    """Graphe prêt à l'emploi : vrai LLM + outils MCP découverts."""
    return construire_graphe(creer_modele(), await charger_outils())
