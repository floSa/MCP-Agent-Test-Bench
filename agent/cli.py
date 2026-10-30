"""CLI de l'agent : affiche les étapes (appels MCP, refus de l'arbitre) puis la réponse.

Usage (dans le conteneur) :
    docker compose exec agent python -m agent.cli "trois fois quatre plus deux"
"""

import asyncio
import json
import sys

from agent import config
from agent.evenements import iter_evenements
from agent.fabrique import creer_graphe


async def main(question: str) -> int:
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
            print(f"  [LLM]     propose : {e['contenu']}")
        elif e["type"] == "refus_arbitre":
            print(f"  [ARBITRE] {e['detail']}")
        elif e["type"] == "erreur":
            print(f"  [ERREUR]  {e['detail']}")
        elif e["type"] == "fin":
            print()
            if e["valide"]:
                nombre = e["reponse"]
                nombre = int(nombre) if float(nombre).is_integer() else nombre
                print(f"[OK] {e['formule']} = {nombre} "
                      f"(réponse validée par l'arbitre)")
                return 0
            print("[ECHEC] aucune réponse validée par l'arbitre")
            return 2
    return 2


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage : python -m agent.cli "trois fois quatre plus deux"')
        sys.exit(1)
    sys.exit(asyncio.run(main(question)))
