import os
import sys
import time
from flask import Flask, request, render_template, jsonify, redirect, url_for, g
from werkzeug.utils import secure_filename

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_db_connection
from shared.logging_config import configure_logging, get_logger, generate_correlation_id, CorrelationContext
from shared.health_check import create_standard_health_checker
from shared.config import Config

# --- Configuração ---
service_config = Config.get_service_config()
media_config = Config.get_media_config()

# Configure logging
configure_logging(service_config['name'])
logger = get_logger(service_config['name'])

app = Flask(__name__, static_folder='static', template_folder='static')
app.config['UPLOAD_FOLDER'] = media_config['staging_dir']
app.config['MAX_CONTENT_LENGTH'] = media_config['max_file_size']

# Create health checker
health_checker = create_standard_health_checker(service_config['name'])
health_checker.create_flask_endpoint(app)

# --- Middleware para Correlation ID ---
@app.before_request
def before_request():
    # Generate or extract correlation ID
    correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
    g.correlation_id = correlation_id
    
    # Set correlation ID in logger context
    logger.set_correlation_id(correlation_id)
    
    # Log request start
    logger.info(
        "Request started",
        context={
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
    )
    g.request_start_time = time.time()

@app.after_request
def after_request(response):
    # Calculate request duration
    duration_ms = (time.time() - g.request_start_time) * 1000
    
    # Log request completion
    logger.info(
        "Request completed",
        context={
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'content_length': response.content_length
        },
        duration_ms=duration_ms
    )
    
    # Add correlation ID to response headers
    response.headers['X-Correlation-ID'] = g.correlation_id
    return response

# --- Funções Auxiliares ---
def allowed_file(filename):
    if '.' not in filename:
        return False
    
    extension = '.' + filename.rsplit('.', 1)[1].lower()
    return extension in media_config['allowed_extensions']

# --- Rotas ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.audit("file_upload_started", "media_files", context={'remote_addr': request.remote_addr})
    
    if 'mediafiles' not in request.files:
        logger.warning("Upload request without files", context={'remote_addr': request.remote_addr})
        return jsonify(error="Nenhum arquivo enviado"), 400

    files = request.files.getlist('mediafiles')

    if not files or files[0].filename == '':
        logger.warning("Upload request with empty files", context={'remote_addr': request.remote_addr})
        return jsonify(error="Nenhum arquivo selecionado"), 400

    errors = {}
    success_count = 0
    total_size = 0

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            destination = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file_size = 0

            # Garante que o diretório de destino exista
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            try:
                file.save(destination)
                file_size = os.path.getsize(destination)
                total_size += file_size
                
                logger.info(
                    "File uploaded successfully",
                    context={
                        'filename': filename,
                        'destination': destination,
                        'file_size_bytes': file_size,
                        'remote_addr': request.remote_addr
                    }
                )
                logger.audit("file_uploaded", filename, context={
                    'file_size_bytes': file_size,
                    'destination': destination
                })
                success_count += 1
                
            except Exception as e:
                logger.error(
                    "Failed to save uploaded file",
                    error=e,
                    context={
                        'filename': filename,
                        'destination': destination,
                        'remote_addr': request.remote_addr
                    },
                    severity="operational"
                )
                errors[file.filename] = str(e)
        elif file:
            logger.warning(
                "File rejected due to invalid extension",
                context={
                    'filename': file.filename,
                    'remote_addr': request.remote_addr
                }
            )
            errors[file.filename] = "Extensão de arquivo não permitida"

    # Log final upload summary
    logger.info(
        "Upload operation completed",
        context={
            'total_files': len(files),
            'successful_uploads': success_count,
            'failed_uploads': len(errors),
            'total_size_bytes': total_size,
            'remote_addr': request.remote_addr
        }
    )

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
    logger.info("Scheduling page accessed", context={'method': request.method, 'remote_addr': request.remote_addr})
    
    conn = None
    try:
        conn = get_db_connection()
        logger.debug("Database connection established for scheduling")
        
        if request.method == 'POST':
            logger.audit("scheduling_rule_modification_attempted", "channel_master_grid", 
                        context={'remote_addr': request.remote_addr})
            # Lógica para salvar a regra de agendamento
            # (Isso será implementado em um passo futuro)
            pass

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM channel_master_grid ORDER BY channel_name;")
            rules = cur.fetchall()
            
            logger.info("Scheduling rules retrieved", context={
                'rules_count': len(rules),
                'remote_addr': request.remote_addr
            })
            
            return render_template('scheduling.html', rules=rules)
            
    except Exception as e:
        logger.error(
            "Failed to load scheduling page",
            error=e,
            context={'remote_addr': request.remote_addr},
            severity="operational"
        )
        return jsonify(error="Erro interno do servidor"), 500
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
