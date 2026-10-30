"""Transforme le flux brut de LangGraph en événements simples et lisibles.

LangGraph (stream_mode="updates") émet « le nœud X vient d'ajouter ces
messages ». Ici chaque message devient un petit dict avec une clé « type » :

  {"type": "pensee",         "contenu": ...}             texte du modèle avant un outil
  {"type": "appel_outil",    "nom", "arguments"}         le modèle demande un outil
  {"type": "resultat_outil", "nom", "contenu", "erreur"} ce que le serveur MCP a renvoyé
  {"type": "reponse",        "contenu": ...}             réponse finale du modèle
  {"type": "erreur",         "detail": ...}              limite d'étapes atteinte
  {"type": "fin",            "reponse", "etapes"}        dernier événement, toujours émis

L'API (SSE), la CLI et l'interface Streamlit consomment tous ce même format.
"""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError


def texte_du_contenu(contenu) -> str:
    """Un message peut porter une chaîne ou une liste de blocs : tout aplatir."""
    if isinstance(contenu, str):
        return contenu
    morceaux = []
    for bloc in contenu or []:
        if isinstance(bloc, str):
            morceaux.append(bloc)
        elif isinstance(bloc, dict) and bloc.get("type") == "text":
            morceaux.append(bloc.get("text", ""))
    return "".join(morceaux)


def evenements_du_message(message) -> list:
    """Convertit un message du graphe en zéro, un ou plusieurs événements."""
    if isinstance(message, AIMessage):
        texte = texte_du_contenu(message.content).strip()
        if message.tool_calls:
            evenements = [{"type": "pensee", "contenu": texte}] if texte else []
            evenements += [{"type": "appel_outil", "nom": appel["name"],
                            "arguments": appel["args"]}
                           for appel in message.tool_calls]
            return evenements
        return [{"type": "reponse", "contenu": texte}]
    if isinstance(message, ToolMessage):
        return [{"type": "resultat_outil", "nom": message.name,
                 "contenu": texte_du_contenu(message.content),
                 "erreur": message.status == "error"}]
    return []


async def iter_evenements(graphe, question: str, limite_etapes: int = 25):
    """Exécute le graphe sur `question` et émet les événements au fil de l'eau."""
    reponse, etapes = "", 0
    flux = graphe.astream(
        {"messages": [HumanMessage(question)]},
        config={"recursion_limit": limite_etapes},
        stream_mode="updates",
    )
    try:
        async for mise_a_jour in flux:
            for sortie in mise_a_jour.values():
                for message in sortie["messages"]:
                    for evenement in evenements_du_message(message):
                        etapes += 1
                        if evenement["type"] == "reponse":
                            reponse = evenement["contenu"]
                        yield evenement
    except GraphRecursionError:
        yield {"type": "erreur",
               "detail": f"limite de {limite_etapes} étapes atteinte sans réponse"}
    yield {"type": "fin", "reponse": reponse, "etapes": etapes}
