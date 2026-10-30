"""Serveur MCP d'exemple n°2 : deux outils sur le texte.

Il sert à montrer qu'un agent peut utiliser PLUSIEURS serveurs MCP à la fois :
les outils de `maths.py` et ceux de ce fichier arrivent mélangés dans la même
liste, et le LLM choisit celui qui convient.

Lancement : python texte.py  (transport HTTP, endpoint /mcp/)
"""

import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP(name="texte")


@mcp.tool
def mettre_en_majuscules(texte: str) -> str:
    """Met un texte en majuscules. Exemple : « bonjour » -> « BONJOUR »."""
    return texte.upper()


@mcp.tool
def compter_mots(texte: str) -> int:
    """Compte les mots d'un texte. Exemple : « un deux trois » -> 3."""
    return len(texte.split())


@mcp.custom_route("/sante", methods=["GET"])
async def sante(request: Request) -> JSONResponse:
    """Endpoint de santé pour le healthcheck Docker (hors protocole MCP)."""
    return JSONResponse({"statut": "ok", "service": "mcp-texte"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
