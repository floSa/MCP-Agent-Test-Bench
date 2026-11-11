"""Configuration de l'agent : quel LLM, quels serveurs MCP.

Tout se règle par variables d'environnement (fichier .env) et par le fichier
mcp_servers.json. Aucun nom de modèle ni d'URL n'est écrit ailleurs dans le code.
"""

import json
import os
import pathlib

# --- LLM ---------------------------------------------------------------------
# Service LLM central (LLM-Service, API compatible OpenAI sous /v1) :
#   depuis un conteneur du réseau llm-net : http://llm-central:8080/v1
#   depuis l'hôte                          : http://127.0.0.1:8080/v1
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://llm-central:8080/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "chat")
# Clé du service (LITELLM_MASTER_KEY de LLM-Service), à fournir dans .env.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
# Paramètres supplémentaires ajoutés à chaque requête, en JSON. Vide par défaut.
# La réflexion est active par défaut sur « chat » ; pour la couper :
#   LLM_EXTRA_BODY={"chat_template_kwargs": {"enable_thinking": false}}
LLM_EXTRA_BODY = json.loads(os.environ.get("LLM_EXTRA_BODY") or "{}")

# --- Serveurs MCP --------------------------------------------------------------
FICHIER_MCP = pathlib.Path(
    os.environ.get("MCP_SERVERS_FILE",
                   pathlib.Path(__file__).parent / "mcp_servers.json"))

# Garde-fou : nombre maximal d'étapes du graphe avant arrêt forcé.
LIMITE_ETAPES = int(os.environ.get("LIMITE_ETAPES", "25"))


def charger_serveurs_mcp(fichier: pathlib.Path = FICHIER_MCP) -> dict:
    """Lit la liste des serveurs MCP : {nom: {transport, url}}."""
    return json.loads(pathlib.Path(fichier).read_text(encoding="utf-8"))
