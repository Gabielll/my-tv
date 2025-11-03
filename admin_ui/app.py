import os
import sys
from flask import Flask, request, render_template, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
import logging

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_db_connection

# --- Configuração ---
UPLOAD_FOLDER = '/mnt/media/staging_ingest'
ALLOWED_EXTENSIONS = {'mkv', 'mp4', 'avi', 'mov'}

app = Flask(__name__, static_folder='static', template_folder='static')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 * 1024  # 16 GB

logging.basicConfig(level=logging.INFO)

# --- Funções Auxiliares ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Rotas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'mediafiles' not in request.files:
        return jsonify(error="Nenhum arquivo enviado"), 400

    files = request.files.getlist('mediafiles')

    if not files or files[0].filename == '':
        return jsonify(error="Nenhum arquivo selecionado"), 400

    errors = {}
    success_count = 0

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            destination = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Garante que o diretório de destino exista
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            try:
                file.save(destination)
                logging.info(f"Arquivo '{filename}' salvo com sucesso em '{destination}'")
                success_count += 1
            except Exception as e:
                logging.error(f"Erro ao salvar o arquivo '{filename}': {e}")
                errors[file.filename] = str(e)
        elif file:
            errors[file.filename] = "Extensão de arquivo não permitida"

    if success_count == 0:
        return jsonify(error="Nenhum arquivo válido foi processado", details=errors), 400

    if errors:
         return jsonify(
            message=f"{success_count} arquivo(s) enviados com sucesso, mas alguns arquivos tiveram erros.",
            errors=errors
        ), 207 # Multi-Status

    return jsonify(message=f"Todos os {success_count} arquivos foram enviados com sucesso!"), 200


@app.route('/scheduling', methods=['GET', 'POST'])
def scheduling():
    conn = get_db_connection()
    try:
        if request.method == 'POST':
            # Lógica para salvar a regra de agendamento
            # (Isso será implementado em um passo futuro)
            pass

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM channel_master_grid ORDER BY channel_name;")
            rules = cur.fetchall()
            return render_template('scheduling.html', rules=rules)
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
