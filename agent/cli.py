"""CLI de l'agent : affiche les étapes (appels MCP, réponses) dans le terminal.

Usage (dans le conteneur) :
    docker compose exec agent python -m agent.cli "combien font 12 plus 30 ?"
"""

import asyncio
import json
import sys

from agent import config
from agent.evenements import iter_evenements
from agent.fabrique import creer_graphe


async def main(question: str) -> None:
    print(f"Question : {question}\n")
    graphe = await creer_graphe()
    async for e in iter_evenements(graphe, question, config.LIMITE_ETAPES):
        if e["type"] == "pensee":
            print(f"  [pensee]  {e['contenu'][:300]}")
        elif e["type"] == "appel_outil":
            args = json.dumps(e["arguments"], ensure_ascii=False)
            print(f"  [MCP]     {e['nom']}({args})")
        elif e["type"] == "resultat_outil":
            print(f"            -> {e['contenu']}")
        elif e["type"] == "reponse":
            print(f"\nRéponse : {e['contenu']}")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage : python -m agent.cli "combien font 12 plus 30 ?"')
        sys.exit(1)
    asyncio.run(main(question))
