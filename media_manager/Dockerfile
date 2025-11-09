# Baseado no Dockerfile genérico
FROM python:3.9-slim

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copia o shared
COPY shared/ /app/shared/

# Copia os requirements e instala
COPY media_manager/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do serviço
COPY media_manager/ /app/media_manager/

# Comando de execução
CMD ["python", "media_manager/app.py"]