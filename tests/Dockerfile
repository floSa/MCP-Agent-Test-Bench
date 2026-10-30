# Image de test : embarque les serveurs MCP d'exemple, l'agent et les tests.
# Contexte de build : la racine du projet (voir docker-compose.yml).
FROM python:3.12-slim

WORKDIR /app

COPY agent/requirements.txt agent/requirements.txt
COPY mcp_servers/requirements.txt mcp_servers/requirements.txt
COPY tests/requirements.txt tests/requirements.txt
RUN pip install --no-cache-dir -r tests/requirements.txt

COPY mcp_servers ./mcp_servers
COPY agent ./agent
COPY tests ./tests
COPY pytest.ini .

CMD ["pytest", "tests", "-m", "not e2e", "-v"]
