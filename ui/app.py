"""Interface Streamlit en mode chat : appels MCP, refus de l'arbitre et reponse en direct.

L'UI ne contient AUCUNE logique metier. Elle se contente de :
  1. envoyer la question a l'endpoint SSE de l'agent (POST /chat/stream) ;
  2. afficher chaque evenement (texte du modele, appel d'outil MCP, resultat de
     l'outil, refus de l'arbitre, reponse finale) DES qu'il arrive, au fil du flux.
"""

import json
import os

import httpx
import streamlit as st

AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8080")

# Quelques questions toutes pretes, proposees dans la barre laterale.
EXEMPLES = [
    "trois fois quatre plus deux",
    "dix moins deux fois trois",
    "ouvre parenthese deux plus trois ferme parenthese fois quatre",
    "cent divise par quatre divise par cinq",
]

st.set_page_config(page_title="Calculatrice : agent LangGraph + MCP", layout="centered")


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
        # Proposition du modele : l'arbitre decide ensuite si elle est valide.
        st.markdown(f"Le modele propose : `{evenement['contenu']}`")

    elif type_evenement == "refus_arbitre":
        nom = f" (`{evenement['nom']}`)" if evenement.get("nom") else ""
        st.error(f"**Arbitre**{nom} &mdash; {evenement['detail']}")

    elif type_evenement == "erreur":
        st.warning(evenement["detail"])

    elif type_evenement == "fin":
        if evenement["valide"]:
            reponse = evenement["reponse"]
            if float(reponse).is_integer():
                reponse = int(reponse)
            st.success(f"### {evenement['formule']} = {reponse}\n"
                       "Reponse construite par les outils et validee par "
                       "l'arbitre.")
        else:
            st.error("### Echec\nAucune reponse validee par l'arbitre.")


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
        "L'agent ne calcule jamais lui-meme : chaque operation passe par les "
        "outils MCP, et l'arbitre rejette toute reponse qui n'a pas ete "
        "construite par les outils."
    )


# ---------------------------------------------------------------------------
# Corps : titre, historique, saisie
# ---------------------------------------------------------------------------

st.title("Calculatrice : agent LangGraph + MCP")
st.markdown(
    "Posez un calcul **en francais**. Le LLM n'a le droit de calculer **qu'avec "
    "les outils MCP** ; un **arbitre** (un noeud du graphe LangGraph) refuse "
    "toute etape qui ne suit pas le vrai calcul. Appels et refus s'affichent "
    "en direct."
)

if "historique" not in st.session_state:
    st.session_state["historique"] = []

# Reaffichage des echanges precedents.
for tour in st.session_state["historique"]:
    afficher_tour(tour["question"], tour["evenements"])

# Nouvelle question : soit tapee, soit issue d'un bouton d'exemple.
question = st.chat_input("Ecrivez un calcul, par ex. : trois fois quatre plus deux")
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
