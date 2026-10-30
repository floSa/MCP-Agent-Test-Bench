"""Configuration de l'agent : quel LLM, quels serveurs MCP.

Tout se règle par variables d'environnement (fichier .env) et par le fichier
mcp_servers.json. Aucun nom de modèle ni d'URL n'est écrit ailleurs dans le code.
"""

import json
import os
import pathlib

# --- LLM ---------------------------------------------------------------------
# Ollama et vLLM exposent la même API (compatible OpenAI) sous /v1 : un seul
# client suffit, seule l'URL change.
#   Ollama central : http://ollama-central:11434/v1
#   vLLM           : http://<service-vllm>:8000/v1
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://ollama-central:11434/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "gemma4:e4b")
# Ollama ignore la clé ; vLLM l'exige seulement s'il a été lancé avec --api-key.
LLM_API_KEY = os.environ.get("LLM_API_KEY", "inutile")

# --- Serveurs MCP --------------------------------------------------------------
FICHIER_MCP = pathlib.Path(
    os.environ.get("MCP_SERVERS_FILE",
                   pathlib.Path(__file__).parent / "mcp_servers.json"))

# Garde-fou : nombre maximal d'étapes du graphe avant arrêt forcé.
LIMITE_ETAPES = int(os.environ.get("LIMITE_ETAPES", "25"))


def charger_serveurs_mcp(fichier: pathlib.Path = FICHIER_MCP) -> dict:
    """Lit la liste des serveurs MCP : {nom: {transport, url}}."""
    return json.loads(pathlib.Path(fichier).read_text(encoding="utf-8"))
