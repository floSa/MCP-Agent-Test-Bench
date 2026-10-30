"""Serveur MCP d'exemple n°1 : deux outils de calcul.

Un serveur MCP, avec FastMCP, se résume à des fonctions Python décorées par
@mcp.tool. Le nom, la docstring et les annotations de types de chaque fonction
sont transformés automatiquement en description d'outil lisible par le LLM :
la docstring joue donc le rôle d'un mini-prompt.

Lancement : python maths.py  (transport HTTP, endpoint /mcp/)
"""

import os

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

mcp = FastMCP(name="maths")


@mcp.tool
def additionner(a: float, b: float) -> float:
    """Additionne deux nombres. Exemple : additionner(2, 3) -> 5."""
    return a + b


@mcp.tool
def multiplier(a: float, b: float) -> float:
    """Multiplie deux nombres. Exemple : multiplier(4, 3) -> 12."""
    return a * b


@mcp.custom_route("/sante", methods=["GET"])
async def sante(request: Request) -> JSONResponse:
    """Endpoint de santé pour le healthcheck Docker (hors protocole MCP)."""
    return JSONResponse({"statut": "ok", "service": "mcp-maths"})


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
