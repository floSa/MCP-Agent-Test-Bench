"""Interface Streamlit en mode chat : appels MCP et reponse du modele en direct.

L'UI ne contient AUCUNE logique metier. Elle se contente de :
  1. envoyer la question a l'endpoint SSE de l'agent (POST /chat/stream) ;
  2. afficher chaque evenement (texte du modele, appel d'outil MCP, resultat de
     l'outil, reponse finale) DES qu'il arrive, au fil du flux.
"""

import json
import os

import httpx
import streamlit as st

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8080")

# Quelques questions toutes pretes, proposees dans la barre laterale.
EXEMPLES = [
    "Combien font 12 plus 30 ?",
    "Mets « bonjour le monde » en majuscules",
    "Combien de mots dans « un petit texte de test » ?",
    "Multiplie 6 par 7, puis mets le mot « resultat » en majuscules",
]

st.set_page_config(page_title="Agent LangGraph + MCP", layout="centered")


# ---------------------------------------------------------------------------
# Communication avec l'agent
# ---------------------------------------------------------------------------

def flux_sse(question: str):
    """Generateur : produit chaque evenement renvoye par /chat/stream.

    Le serveur emet du Server-Sent Events : des lignes « data: <json> »
    separees par des lignes vides. On ne garde que les lignes utiles.
    """
    with httpx.stream(
        "POST",
        f"{AGENT_URL}/chat/stream",
        json={"question": question},
        timeout=httpx.Timeout(600.0),
    ) as reponse:
        reponse.raise_for_status()
        for ligne in reponse.iter_lines():
            if ligne.startswith("data: "):
                yield json.loads(ligne[len("data: "):])


# ---------------------------------------------------------------------------
# Rendu d'un evenement de la trace ReAct
# ---------------------------------------------------------------------------

def _afficher_resultat_outil(colonne, resultat):
    colonne.caption("Resultat")
    if isinstance(resultat, (dict, list)):
        colonne.json(resultat)
    else:
        colonne.code(json.dumps(resultat, ensure_ascii=False), language="json")


def afficher_evenement(evenement: dict) -> None:
    """Met en scene un evenement selon son type."""
    type_evenement = evenement["type"]

    if type_evenement == "pensee":
        st.caption(evenement["contenu"])

    elif type_evenement == "appel_outil":
        with st.container(border=True):
            st.markdown(f"**Appel MCP** &rarr; `{evenement['nom']}`")
            st.json(evenement["arguments"])

    elif type_evenement == "resultat_outil":
        with st.container(border=True):
            st.markdown(f"**Resultat** de `{evenement['nom']}`"
                        + (" (erreur)" if evenement.get("erreur") else ""))
            st.code(evenement["contenu"], language="text")

    elif type_evenement == "reponse":
        st.success(evenement["contenu"])

    elif type_evenement == "erreur":
        st.error(evenement["detail"])


def afficher_tour(question: str, evenements: list) -> None:
    """Reaffiche un echange deja termine (depuis l'historique)."""
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        for evenement in evenements:
            afficher_evenement(evenement)


# ---------------------------------------------------------------------------
# Barre laterale : etat du service et exemples
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Service")
    try:
        sante = httpx.get(f"{AGENT_URL}/sante", timeout=5).json()
        st.success(f"Agent en ligne &mdash; modele `{sante.get('modele', '?')}`")
    except Exception:
        st.error(f"Agent injoignable ({AGENT_URL})")

    st.header("Exemples")
    for exemple in EXEMPLES:
        if st.button(exemple, use_container_width=True):
            st.session_state["question_en_attente"] = exemple

    st.caption(
        "L'agent decouvre les outils des serveurs MCP listes dans "
        "agent/mcp_servers.json et choisit lesquels appeler."
    )


# ---------------------------------------------------------------------------
# Corps : titre, historique, saisie
# ---------------------------------------------------------------------------

st.title("Agent LangGraph + MCP")
st.markdown(
    "Posez une question. L'agent (un graphe LangGraph) decide s'il a besoin "
    "d'un outil, l'appelle sur un serveur **MCP**, puis repond. Chaque appel "
    "s'affiche en direct."
)

if "historique" not in st.session_state:
    st.session_state["historique"] = []

# Reaffichage des echanges precedents.
for tour in st.session_state["historique"]:
    afficher_tour(tour["question"], tour["evenements"])

# Nouvelle question : soit tapee, soit issue d'un bouton d'exemple.
question = st.chat_input("Posez une question, par ex. : combien font 12 plus 30 ?")
if not question and "question_en_attente" in st.session_state:
    question = st.session_state.pop("question_en_attente")

if question:
    with st.chat_message("user"):
        st.markdown(question)

    evenements = []
    with st.chat_message("assistant"):
        try:
            # Chaque evenement est rendu DES son arrivee : effet streaming.
            for evenement in flux_sse(question):
                evenements.append(evenement)
                afficher_evenement(evenement)
        except Exception as erreur:  # noqa: BLE001
            st.error(f"Impossible de joindre l'agent : {erreur}")

    st.session_state["historique"].append(
        {"question": question, "evenements": evenements})
