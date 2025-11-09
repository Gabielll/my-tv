# Baseado no Dockerfile genérico
FROM python:3.9-slim

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copia o shared
COPY shared/ /app/shared/

# Copia os requirements e instala
COPY scheduler_ai/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do serviço
COPY scheduler_ai/ /app/scheduler_ai/

# Comando de execução
CMD ["python", "scheduler_ai/app.py"]