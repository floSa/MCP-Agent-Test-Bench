"""Le graphe de l'agent calculatrice : le squelette + un nœud ARBITRE.

        START ──▶ [ llm ] ──▶ [ arbitre ] ── appel valide ──▶ [ outils ] ──▶ [ noter ]
                    ▲            │  │                                           │
                    │            │  └── réponse finale valide ──▶ END           │
                    │            │                                               │
                    └── refus ───┘◀──────────────────────────────────────────────┘

Par rapport au squelette de la branche main (llm ⇄ outils), deux nœuds s'ajoutent :

  - « arbitre » : vérifie ce que le modèle propose AVANT que cela ait un effet.
      * un appel d'outil est exécuté seulement s'il est l'étape attendue du
        calcul (bon outil, bons arguments) ;
      * une réponse finale est acceptée seulement si la formule a été réduite
        étape par étape par les outils, et si le nombre annoncé est le bon.
    Sinon, le refus est renvoyé au modèle comme un message, et la boucle continue.
  - « noter » : après chaque outil réussi, met à jour la mémoire de l'arbitre
    (formule courante, dernier résultat).

C'est le patron « le LLM propose, le code dispose ». Voir docs/calculatrice.md.
"""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from agent.arbitre import Arbitre, extraire_nombre_final
from agent.evenements import texte_du_contenu

# Prompt court et directif : un petit modèle ignore les protocoles longs.
PROMPT_SYSTEME = """Tu es une calculatrice sans cerveau : tu ne sais ni convertir ni calculer toi-meme.
Resous la question en appelant les outils, UN seul outil par tour, dans cet ordre :
convertir_texte_en_formule, puis en boucle trouver_calcul_prioritaire, calculer,
remplacer_calcul_par_resultat, jusqu'a ce que la formule soit un seul nombre.
Tu n'as le droit d'ecrire du texte qu'a la toute fin, au format :
REPONSE FINALE: <nombre>"""


def donnees_outil(message: ToolMessage):
    """Valeur utile d'un résultat d'outil : JSON décodé si possible, sinon texte."""
    texte = texte_du_contenu(message.content).strip()
    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        return texte


def construire_graphe(modele, outils, prompt_systeme: str = PROMPT_SYSTEME):
    """Assemble et compile le graphe. Un graphe = un calcul (l'arbitre a une mémoire)."""
    modele_avec_outils = modele.bind_tools(outils)
    par_nom = {o.name: o for o in outils}

    async def oracle_priorite(formule: str) -> dict:
        """Vérité terrain de l'arbitre : le serveur MCP, jamais le LLM."""
        brut = await par_nom["trouver_calcul_prioritaire"].ainvoke(
            {"formule": formule})
        if isinstance(brut, list):
            brut = texte_du_contenu(brut)
        return json.loads(brut) if isinstance(brut, str) else brut

    arbitre = Arbitre(oracle_priorite=oracle_priorite)

    # -- les nœuds ---------------------------------------------------------------

    async def noeud_llm(etat: MessagesState):
        messages = [SystemMessage(prompt_systeme), *etat["messages"]]
        return {"messages": [await modele_avec_outils.ainvoke(messages)]}

    async def noeud_arbitre(etat: MessagesState):
        """Valide la proposition du modèle ; renvoie un refus, ou ne change rien."""
        proposition: AIMessage = etat["messages"][-1]
        appels = proposition.tool_calls

        if not appels:                                   # réponse finale
            texte = texte_du_contenu(proposition.content)
            refus = arbitre.verifier_reponse_finale(extraire_nombre_final(texte))
            if refus is None:
                return {}
            return {"messages": [HumanMessage(
                f"ARBITRE : {refus}", additional_kwargs={"arbitre": True})]}

        if len(appels) > 1:                              # un outil à la fois
            refus = "Refusé : appelle UN seul outil par tour."
        else:
            refus = await arbitre.verifier_appel(appels[0]["name"],
                                                 appels[0]["args"])
        if refus is None:
            return {}
        # Un refus doit répondre à CHAQUE appel demandé (sinon l'API rejette
        # la conversation) : on renvoie le même message pour chacun.
        return {"messages": [ToolMessage(
            refus, tool_call_id=a["id"], name=a["name"],
            additional_kwargs={"arbitre": True}) for a in appels]}

    async def noeud_noter(etat: MessagesState):
        """Après un outil réussi, l'arbitre mémorise le résultat."""
        resultat: ToolMessage = etat["messages"][-1]
        proposition: AIMessage = etat["messages"][-2]
        if resultat.status != "error":
            arbitre.noter_resultat(resultat.name,
                                   proposition.tool_calls[0]["args"],
                                   donnees_outil(resultat))
        return {}

    # -- l'aiguillage après l'arbitre ----------------------------------------------

    def apres_arbitre(etat: MessagesState) -> str:
        dernier = etat["messages"][-1]
        if isinstance(dernier, AIMessage):
            return "outils" if dernier.tool_calls else "fin"   # validé
        return "llm"                                            # refusé

    graphe = StateGraph(MessagesState)
    graphe.add_node("llm", noeud_llm)
    graphe.add_node("arbitre", noeud_arbitre)
    graphe.add_node("outils", ToolNode(outils))
    graphe.add_node("noter", noeud_noter)

    graphe.add_edge(START, "llm")
    graphe.add_edge("llm", "arbitre")
    graphe.add_conditional_edges(
        "arbitre", apres_arbitre, {"outils": "outils", "llm": "llm", "fin": END})
    graphe.add_edge("outils", "noter")
    graphe.add_edge("noter", "llm")
    return graphe.compile()
