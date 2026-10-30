# 5. Aller plus loin

## Les niveaux d'abstraction

LangGraph n'est qu'un étage d'une pile. Chaque étage reprend celui du dessous et
le simplifie, au prix de moins de contrôle.

```
┌───────────────────────────────────────────────────────┐
│ Deep Agents     planification, fichiers virtuels,     │  le plus clé en main
│                 sous-agents                           │
├───────────────────────────────────────────────────────┤
│ LangChain       create_agent : l'agent standard       │
│                 en quelques lignes                    │
├───────────────────────────────────────────────────────┤
│ LangGraph       StateGraph : on dessine soi-même      │  <- ce projet
│                 les nœuds et les flèches              │
├───────────────────────────────────────────────────────┤
│ langchain-mcp-adapters   serveurs MCP -> outils       │  la prise, commune à tous
└───────────────────────────────────────────────────────┘
```

Le projet utilise le **StateGraph** parce qu'il montre chaque pièce. Les deux
étages supérieurs reçoivent les **mêmes outils MCP** : il suffit de leur passer
`await charger_outils()`.

### Le raccourci : `create_agent`

Équivalent du graphe de [`agent/graphe.py`](../agent/graphe.py) en une ligne
(testé avec `langchain` 1.4 sur cette stack) :

```python
from langchain.agents import create_agent

agent = create_agent(model=creer_modele(), tools=await charger_outils(),
                     system_prompt="Utilise les outils quand c'est utile.")
```

À préférer pour un agent simple. Le `StateGraph` reprend l'avantage dès que le
flux sort de la boucle classique (étape de validation, humain dans la boucle,
branches multiples).

### Deep Agents

[Deep Agents](https://docs.langchain.com/oss/python/deepagents/overview) est une
couche au-dessus de LangGraph, pensée pour les tâches **longues et
multi-étapes** : l'agent planifie, garde ses notes dans un système de fichiers
virtuel et délègue à des sous-agents (testé avec `deepagents` 0.7) :

```python
from deepagents import create_deep_agent

agent = create_deep_agent(model=creer_modele(), tools=await charger_outils(),
                          system_prompt="Utilise les outils quand c'est utile.")
```

Pour répondre à « combien font 12 plus 30 ? », c'est disproportionné. Il prend
son sens pour des demandes du type « analyse ces vingt documents et prépare une
synthèse ».

### Lequel choisir

| Besoin | Choix |
|---|---|
| Comprendre, enseigner, garder la main sur le flux | `StateGraph` |
| Un agent qui appelle des outils, sans cérémonie | `create_agent` |
| Une mission longue à décomposer et déléguer | Deep Agents |

## Bonnes pratiques

- **Écrire des outils qu'un modèle comprend.** Nom explicite, docstring avec un
  exemple, types précis. C'est le « prompt » de l'outil.
- **Le LLM propose, le code dispose.** Valider les entrées côté serveur MCP et
  renvoyer des erreurs claires : ne jamais faire confiance à ce que le modèle
  envoie.
- **Limiter la boucle.** `LIMITE_ETAPES` (25 par défaut) coupe un modèle qui
  tournerait en rond ; l'agent émet alors un événement `erreur`.
- **Peu d'outils par agent.** Au-delà d'une dizaine, la qualité des choix chute,
  surtout sur de petits modèles.
- **Tester sans LLM.** Le dossier [`tests/`](../tests) rejoue un modèle scripté
  (`FauxLLM`) : le graphe et le câblage MCP se vérifient en quelques secondes,
  de façon déterministe.
- **Tracer.** Pour un usage sérieux, brancher un outil de traçage (LangSmith,
  Langfuse) afin de voir chaque appel de modèle et d'outil.
- **Sécuriser les serveurs MCP distants.** Authentification, liste blanche
  d'outils, et aucun outil destructeur sans confirmation humaine.

## Un exemple complet : la calculatrice

La branche [`exemple/calculatrice`](https://github.com/floSa/MCP-Agent-Test-Bench/tree/exemple/calculatrice)
applique ce squelette à un cas concret : un petit modèle qui résout des calculs
posés en français **sans jamais calculer lui-même**, chaque opération passant
par des outils MCP.

---
Précédent : [4. Brancher un serveur MCP](04-brancher-un-mcp.md)
