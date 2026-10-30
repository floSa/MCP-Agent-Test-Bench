"""Faux LLM scripté : rejoue des réponses prévues, sans aucun vrai modèle.

C'est ce qui rend les tests du graphe rapides et déterministes : on décide à
l'avance « au 1er tour le modèle demande l'outil X, au 2e il répond Y ».
"""

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class FauxLLM(BaseChatModel):
    reponses: list          # les AIMessage à rejouer, dans l'ordre
    appels: int = 0

    @property
    def _llm_type(self) -> str:
        return "faux"

    def bind_tools(self, outils, **kwargs):
        return self  # le script décide seul : les outils sont ignorés

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        modele = self.reponses[min(self.appels, len(self.reponses) - 1)]
        # Identifiants uniques à chaque tour : LangGraph fusionne les messages
        # de même id au lieu de les ajouter, ce qui masquerait les répétitions.
        message = modele.model_copy(update={
            "id": f"faux-{self.appels}",
            "tool_calls": [{**c, "id": f"{c['id']}-{self.appels}"}
                           for c in modele.tool_calls]})
        self.appels += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def appel_outil(nom: str, **arguments) -> AIMessage:
    return AIMessage(content="", tool_calls=[
        {"name": nom, "args": arguments, "id": f"appel_{nom}"}])
