"""API HTTP de l'agent (FastAPI).

Endpoints :
  GET  /sante         healthcheck Docker
  GET  /outils        outils découverts sur les serveurs MCP (utile pour vérifier)
  POST /chat          réponse complète en une fois (JSON)
  POST /chat/stream   événements en direct (SSE) : c'est ce que consomme Streamlit

Les deux endpoints de chat s'appuient sur le MÊME générateur d'événements
(agent/evenements.py) : /chat l'épuise, /chat/stream le relaie.
"""

import json

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import config
from agent.evenements import iter_evenements
from agent.fabrique import charger_outils, creer_graphe

app = FastAPI(
    title="Agent LangGraph + MCP",
    description="Un agent LangGraph qui utilise les outils de serveurs MCP.",
)


class Question(BaseModel):
    question: str


@app.get("/sante")
async def sante():
    return {"statut": "ok", "service": "agent", "modele": config.LLM_MODEL,
            "llm": config.LLM_BASE_URL}


@app.get("/outils")
async def outils():
    return [{"nom": o.name, "description": o.description}
            for o in await charger_outils()]


@app.post("/chat")
async def chat(q: Question):
    graphe = await creer_graphe()
    evenements = [e async for e in
                  iter_evenements(graphe, q.question, config.LIMITE_ETAPES)]
    return {"reponse": evenements[-1]["reponse"], "etapes": evenements[:-1]}


@app.post("/chat/stream")
async def chat_stream(q: Question):
    graphe = await creer_graphe()

    async def flux():
        async for evenement in iter_evenements(graphe, q.question,
                                               config.LIMITE_ETAPES):
            yield f"data: {json.dumps(evenement, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        flux(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
