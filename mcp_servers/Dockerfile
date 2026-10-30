FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Une seule image pour tous les serveurs d'exemple : docker-compose.yml choisit
# lequel lancer (python maths.py ou python texte.py).
COPY maths.py texte.py ./

EXPOSE 8000
CMD ["python", "maths.py"]
