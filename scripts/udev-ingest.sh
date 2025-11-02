#!/bin/bash

# udev-ingest.sh - Script para copiar mídia de um dispositivo USB para a área de staging.

# --- Variáveis de Configuração ---
STAGING_DIR="/mnt/media/staging_ingest"
MOUNT_POINT_BASE="/mnt/usb_ingest"
LOG_FILE="/var/log/udev-ingest.log"
DEVICE="$1"

# --- Funções ---
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# --- Validação ---
if [ -z "$DEVICE" ]; then
    log_message "ERRO: O script foi chamado sem um dispositivo como argumento."
    exit 1
fi

if [ ! -b "$DEVICE" ]; then
    log_message "ERRO: O argumento '$DEVICE' não é um dispositivo de bloco válido."
    exit 1
fi

# --- Execução ---
log_message "INÍCIO: Novo dispositivo detectado: $DEVICE"

# Cria um ponto de montagem único para evitar conflitos
MOUNT_POINT="${MOUNT_POINT_BASE}_$(basename $DEVICE)"
mkdir -p "$MOUNT_POINT"
log_message "Ponto de montagem criado em $MOUNT_POINT"

# Monta o dispositivo
mount "$DEVICE" "$MOUNT_POINT"
if [ $? -ne 0 ]; then
    log_message "ERRO: Falha ao montar $DEVICE em $MOUNT_POINT."
    rmdir "$MOUNT_POINT"
    exit 1
fi
log_message "Dispositivo $DEVICE montado com sucesso."

# Cria o diretório de staging se não existir
mkdir -p "$STAGING_DIR"

# Copia os arquivos de mídia usando rsync (robusto e preserva atributos)
# Filtra para incluir apenas os formatos de vídeo mais comuns.
log_message "Iniciando a cópia de arquivos de mídia..."
rsync -av --progress --remove-source-files \
    --include='*.mkv' --include='*.mp4' --include='*.avi' --include='*.mov' \
    --include='*/' --exclude='*' \
    "$MOUNT_POINT/" "$STAGING_DIR/" >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log_message "Cópia concluída com sucesso."
else
    log_message "AVISO: rsync terminou com um código de erro. A cópia pode estar incompleta."
fi

# Desmonta o dispositivo
umount "$MOUNT_POINT"
if [ $? -ne 0 ]; then
    log_message "ERRO: Falha ao desmontar $DEVICE de $MOUNT_POINT."
    # Não saia, ainda queremos limpar o diretório.
else
    log_message "Dispositivo $DEVICE desmontado com sucesso."
fi

# Remove o ponto de montagem
rmdir "$MOUNT_POINT"
log_message "Ponto de montagem $MOUNT_POINT removido."

log_message "FIM: Processamento de $DEVICE concluído."

exit 0
