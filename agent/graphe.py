"""Le graphe de l'agent : un StateGraph LangGraph de trois pièces.

        START ──▶ [ llm ] ──── appel d'outil ? ──▶ [ outils ]
                     ▲              │ non                │
                     │              ▼                    │
                     │            END                    │
                     └───────────────────────────────────┘

  - l'ÉTAT         : la liste des messages (MessagesState), partagée par les nœuds ;
  - le nœud « llm »    : envoie la conversation au modèle, ajoute sa réponse ;
  - le nœud « outils » : exécute les appels d'outils demandés (via MCP), ajoute
                         les résultats ;
  - l'arête conditionnelle : si la réponse du modèle contient un appel d'outil,
                         aller aux outils, sinon terminer.

C'est la boucle « ReAct » (Penser, Agir, Observer) rendue explicite.
Voir docs/02-state-graph.md.
"""

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

PROMPT_SYSTEME = (
    "Tu es un assistant qui dispose d'outils. "
    "Quand un outil permet de répondre, utilise-le plutôt que de deviner, "
    "puis réponds de façon brève, en français."
)


def construire_graphe(modele, outils, prompt_systeme: str = PROMPT_SYSTEME):
    """Assemble et compile le graphe.

    `modele`  : un modèle de chat LangChain (ChatOpenAI, ou un faux en test).
    `outils`  : la liste d'outils LangChain (ici, issus des serveurs MCP).
    """
    modele_avec_outils = modele.bind_tools(outils)

    async def noeud_llm(etat: MessagesState):
        messages = [SystemMessage(prompt_systeme), *etat["messages"]]
        return {"messages": [await modele_avec_outils.ainvoke(messages)]}

    graphe = StateGraph(MessagesState)
    graphe.add_node("llm", noeud_llm)
    graphe.add_node("outils", ToolNode(outils))

    graphe.add_edge(START, "llm")
    graphe.add_conditional_edges(
        "llm", tools_condition, {"tools": "outils", END: END})
    graphe.add_edge("outils", "llm")
    return graphe.compile()
