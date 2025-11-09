# Baseado no Dockerfile.ffmpeg
FROM python:3.9-slim

RUN apt-get update && apt-get install -y ffmpeg

WORKDIR /app

ENV PYTHONPATH "${PYTHONPATH}:/app"

# Copia o shared
COPY shared/ /app/shared/

# Copia os requirements e instala
COPY normalization_worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código do serviço
COPY normalization_worker/ /app/normalization_worker/

# Comando de execução
CMD ["python", "normalization_worker/app.py"]