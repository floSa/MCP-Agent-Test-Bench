# 3. Brancher le LLM central (LLM-Service)

## Principe : un LLM partagé, pas un par projet

Lancer un serveur de LLM par projet gaspille du disque et de la VRAM. Un seul
service, **LLM-Service**, est appelé par tous les projets via le réseau Docker
externe `llm-net`.

```mermaid
flowchart LR
    subgraph llmsvc["LLM-Service - un seul, toujours allumé"]
        central["llm-central (LiteLLM)<br/>API OpenAI :8080<br/>modèle « chat »"]
    end
    net{{"réseau Docker partagé llm-net"}}
    p1["Ce projet<br/>(agent)"]
    p2["Autre projet"]
    p1 --> net
    p2 --> net
    net --> central
```

Ce projet ne contient aucun LLM : [`docker-compose.yml`](../docker-compose.yml)
lance seulement l'agent, l'interface et les serveurs MCP.

## Réglages (`.env`)

| Variable | Valeur | Rôle |
|---|---|---|
| `LLM_BASE_URL` | `http://llm-central:8080/v1` (conteneur) ou `http://127.0.0.1:8080/v1` (hôte) | API OpenAI du service |
| `LLM_MODEL` | `chat` | Qwen3.5-4B, réflexion + vision, contexte 16 384 jetons |
| `LLM_API_KEY` | clé propre « mcp-agent-test-bench » (jamais la clé maîtresse de LLM-Service) | clé obligatoire, jamais commitée |
| `LLM_EXTRA_BODY` | `{"chat_template_kwargs": {"enable_thinking": false}}` | coupe la réflexion |

Le `.env` n'est pas suivi par git ; seul [`.env.example`](../.env.example) l'est.

## Démarrage

1. Démarrer LLM-Service (crée le réseau `llm-net`).
2. `cp .env.example .env` puis écrire la clé propre de l'application et
   l'adresse conteneur dans `.env` :
   `~/mes_projets/Projet-IA/LLM-Service/scripts/cle.sh creer mcp-agent-test-bench --dans <dépôt>/.env --noms LLM_BASE_URL,LLM_API_KEY`
   (procédure : `LLM-Service/docs/brancher-une-application.md`). Révocation :
   `scripts/cle.sh revoquer mcp-agent-test-bench` ; consommation :
   `scripts/cle.sh consommation` (depuis le dépôt LLM-Service).
3. Lier les ports publiés à `127.0.0.1` (voir ci-dessous), puis `make up`.

### Ports publiés sur toutes les interfaces (point ouvert)

[`docker-compose.yml`](../docker-compose.yml) publie 8101, 8102, 8090, 8501
et 6274 sans adresse, donc sur toutes les interfaces de la machine. Avant de
lancer la pile, les lier à `127.0.0.1` (par exemple `"127.0.0.1:8501:8501"`).
Le compose n'est pas encore modifié : point laissé à décider.

`make up` ajoute au compose de base
[`docker-compose.llm-central.yml`](../docker-compose.llm-central.yml), qui
rattache l'agent au réseau `llm-net` (`external: true`).

Le port 8080 de l'hôte étant occupé par LLM-Service, l'API de l'agent est
publiée sur **8090** (`AGENT_PORT` pour le changer).

## Essai réel avec la clé propre (14/11/2026)

Conteneur ponctuel, sans port publié :

```bash
docker compose -f docker-compose.yml -f docker-compose.llm-central.yml \
  run --rm --no-deps --build agent \
  python -c "from agent.fabrique import creer_modele; print(creer_modele().invoke('Dis bonjour en un mot.').content)"
```

Réponse : « Bonjour » (21 jetons comptés sur la clé `mcp-agent-test-bench`).

## Réflexion désactivée

La réflexion est active par défaut sur `chat`. Pour un agent à outils, elle
allonge les réponses sans bénéfice : `LLM_EXTRA_BODY` la coupe via
`chat_template_kwargs`. Pour la réactiver, laisser `LLM_EXTRA_BODY` vide ; le
raisonnement arrive alors dans `message.reasoning_content`.

## Choisir un modèle

L'agent exige un modèle qui sait **appeler des outils** (*function calling*).
`chat` convient (essai réel : appels `additionner` puis `mettre_en_majuscules`).

## Où se fait le branchement dans le code

Une seule fonction, [`creer_modele()`](../agent/fabrique.py) :

```python
ChatOpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY,
           model=config.LLM_MODEL, temperature=0, extra_body=...)
```

Rien d'autre dans le projet ne connaît le LLM.

---
Précédent : [2. Le StateGraph](02-state-graph.md) · Suite : [4. Brancher un serveur MCP](04-brancher-un-mcp.md)
