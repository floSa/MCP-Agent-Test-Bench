FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY outils_calcul.py llm.py calculatrice.py ./

EXPOSE 8000
CMD ["python", "calculatrice.py"]
