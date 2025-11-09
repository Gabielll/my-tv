# Baseado no Dockerfile genérico
FROM python:3.9-slim

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copia o shared
COPY shared/ /app/shared/

# Copia os requirements e instala
COPY metadata_enricher/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do serviço
COPY metadata_enricher/ /app/metadata_enricher/

# Comando de execução
CMD ["python", "metadata_enricher/app.py"]