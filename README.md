# Calculatrice : un agent LangGraph + MCP avec arbitre

Un **exemple concret** du squelette [agent LangGraph + MCP](https://github.com/floSa/MCP_maison/tree/main) :
un LLM résout des calculs posés en français — « *trois fois quatre plus deux* » —
**sans jamais calculer lui-même**. Chaque opération passe par un outil exposé
via **MCP**, et un **arbitre** (un nœud du graphe) refuse toute étape qui ne
suit pas le vrai calcul. Le LLM est externe (Ollama ou vLLM).

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.2-1C3C3C)
![FastMCP](https://img.shields.io/badge/FastMCP-2.14-000000)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?logo=streamlit&logoColor=white)

## Les deux branches

| Branche | Contenu |
|---|---|
| [`main`](https://github.com/floSa/MCP_maison/tree/main) | Le squelette générique et son tutoriel (principe, StateGraph, brancher un LLM ou un MCP). |
| **`exemple/calculatrice`** (ici) | Le cas concret : calculatrice + arbitre anti-triche. |

La documentation de cette branche : [la calculatrice et son arbitre](docs/calculatrice.md),
[le serveur MCP](docs/mcp.md), [MCPJam](docs/mcpjam.md).

## Démarrage rapide

Prérequis : Docker, et un LLM servi en Ollama ou vLLM (voir le tutoriel sur
`main`). Le modèle doit savoir appeler des outils (`gemma4:e4b` convient).

```bash
cp .env.example .env     # puis adapter LLM_BASE_URL et LLM_MODEL
make up                  # branche l'agent sur le service LLM central
make demo                # "trois fois quatre plus deux", trace pas à pas
```

Sans service LLM central : `make up-local` embarque un Ollama dans la stack.

| Interface | Adresse |
|---|---|
| Chat (Streamlit) | <http://localhost:8501> |
| API de l'agent | <http://localhost:8080/docs> |
| Inspecteur MCPJam | <http://localhost:6274> |

## Architecture

```mermaid
flowchart LR
    user(["Utilisateur"])

    subgraph stack["docker compose"]
        direction LR
        ui["ui - Streamlit<br/>:8501"]
        mcpjam["mcpjam<br/>:6274"]

        subgraph agent["agent - FastAPI + LangGraph - :8080"]
            llm["nœud llm"]
            arbitre["nœud arbitre<br/>anti-triche"]
            outils["nœud outils"]
            llm --> arbitre
            arbitre -->|appel valide| outils
            arbitre -.->|refus| llm
            outils --> llm
        end

        mcp["mcp-calculatrice - FastMCP<br/>convertir, trouver_prioritaire,<br/>calculer, remplacer"]
    end

    ext["LLM externe<br/>Ollama ou vLLM<br/>(API /v1)"]

    user --> ui
    ui -->|"POST /chat/stream"| agent
    llm <-->|messages + outils| ext
    outils -->|MCP| mcp
    arbitre -.->|"vérité terrain<br/>(calcul prioritaire)"| mcp
    mcpjam -.->|teste à la main| mcp

    classDef boite fill:#1e293b,stroke:#475569,color:#e2e8f0
    classDef bouclier fill:#7f1d1d,stroke:#ef4444,color:#fee2e2
    classDef externe fill:#14532d,stroke:#22c55e,color:#dcfce7
    class ui,mcpjam,mcp,llm,outils boite
    class arbitre bouclier
    class ext externe
```

## Tests

```bash
make test        # outils, serveur MCP, graphe + arbitre : faux LLM, quelques secondes
make test-e2e    # bout en bout avec le vrai LLM (stack démarrée)
```
