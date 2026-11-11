# Raccourcis (équivalents docker compose dans le README)

CENTRAL = -f docker-compose.yml -f docker-compose.llm-central.yml

.PHONY: up down logs test test-e2e demo urls

up:            ## démarre la stack, branchée sur le service LLM central
	docker compose $(CENTRAL) up -d --build


down:          ## arrête tout
	docker compose $(CENTRAL) down

logs:
	docker compose $(CENTRAL) logs -f agent mcp-maths mcp-texte

test:          ## tests rapides : serveurs MCP, graphe, intégration (faux LLM)
	docker compose --profile test run --rm --build tests

test-e2e:      ## tests de bout en bout avec le vrai LLM (stack démarrée)
	docker compose $(CENTRAL) --profile e2e run --rm --build tests-e2e

demo:          ## une question posée au vrai agent, trace pas-à-pas
	docker compose $(CENTRAL) exec agent python -m agent.cli "Combien font 12 plus 30, puis mets le mot résultat en majuscules ?"

urls:          ## rappel des interfaces
	@echo "Streamlit : http://localhost:8501"
	@echo "MCPJam    : http://localhost:6274  (serveur MCP : http://mcp-maths:8000/mcp/)"
	@echo "API agent : http://localhost:8090  (docs : /docs, outils : /outils)"
