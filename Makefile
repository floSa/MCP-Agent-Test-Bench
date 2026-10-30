# Raccourcis (équivalents docker compose dans le README)

CENTRAL = -f docker-compose.yml -f docker-compose.llm-central.yml
LOCAL   = -f docker-compose.yml -f docker-compose.llm-local.yml

.PHONY: up up-local down logs test test-e2e demo urls

up:            ## démarre la stack, branchée sur le service LLM central
	docker compose $(CENTRAL) up -d --build

up-local:      ## démarre la stack avec un Ollama embarqué
	docker compose $(LOCAL) up -d --build

down:          ## arrête tout
	docker compose $(CENTRAL) down

logs:
	docker compose $(CENTRAL) logs -f agent mcp-calculatrice

test:          ## tests rapides : outils, serveur MCP, graphe + arbitre (faux LLM)
	docker compose --profile test run --rm --build tests

test-e2e:      ## tests de bout en bout avec le vrai LLM (stack démarrée)
	docker compose $(CENTRAL) --profile e2e run --rm --build tests-e2e

demo:          ## une question posée au vrai agent, trace pas-à-pas
	docker compose $(CENTRAL) exec agent python -m agent.cli "trois fois quatre plus deux"

urls:          ## rappel des interfaces
	@echo "Streamlit : http://localhost:8501"
	@echo "MCPJam    : http://localhost:6274  (serveur MCP : http://mcp-calculatrice:8000/mcp/)"
	@echo "API agent : http://localhost:8080  (docs : /docs, outils : /outils)"
