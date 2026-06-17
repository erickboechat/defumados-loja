import os
import json
import time
import logging
from datetime import timedelta

from flask import Flask, render_template, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import csrf, limiter
from models import init_db, criar_indices, close_db, get_db
from blueprints import public_bp, checkout_bp, api_bp, admin_bp

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ProxyFix: essencial quando rodando atrás de Nginx
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

# Segurança: cookie de sessão
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', '1') == '1',
    SESSION_PERMANENT=False,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2),
    WTF_CSRF_TIME_LIMIT=3600,
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log', encoding='utf-8')
    ]
)
log = logging.getLogger(__name__)

# Inicializar extensões
csrf.init_app(app)
limiter.init_app(app)

# Rate limits específicos (expostos para blueprints usarem)
limite_csrf = limiter.limit("30 per minute")

# Inicializar banco
init_db()
criar_indices()

app.teardown_appcontext(close_db)

# Timestamp de inicialização (para health check)
START_TIME = time.time()


# ===== CONTEXT PROCESSOR =====

@app.context_processor
def inject_globals():
    version = '1'
    build_path = os.path.join(app.root_path, 'static', 'build.json')
    try:
        with open(build_path, 'r') as f:
            data = json.load(f)
            version = data.get('version', '1')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    critical_css = ''
    css_path = os.path.join(app.root_path, 'static', 'critical.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            critical_css = f.read()
    except FileNotFoundError:
        pass

    from flask_wtf.csrf import generate_csrf
    return dict(csrf_token=generate_csrf, static_version=version, critical_css=critical_css)


# ===== TEMPLATE FILTERS =====

@app.template_filter('webp_smart')
def webp_smart_filter(caminho_imagem):
    if not caminho_imagem:
        return ''
    nome_sem_ext, _ = os.path.splitext(caminho_imagem)
    caminho_webp = f"{nome_sem_ext}.webp"
    caminho_relativo = caminho_webp.replace('/static/', '', 1)
    if os.path.exists(os.path.join('static', caminho_relativo)):
        return caminho_webp
    return caminho_imagem


@app.template_filter('webp_smart_list')
def webp_smart_list_filter(imagens):
    return [webp_smart_filter(img) for img in imagens]


@app.template_filter('srcset_webp')
def srcset_webp_filter(caminho_imagem):
    if not caminho_imagem:
        return ''
    from urllib.parse import unquote, quote
    caminho_real = unquote(caminho_imagem)
    nome_sem_ext, _ = os.path.splitext(caminho_real)
    base_name = os.path.basename(nome_sem_ext)

    urls = []
    for w in [300, 600]:
        fname = f'{base_name}.webp' if w == 600 else f'{base_name}-{w}w.webp'
        fpath = os.path.join('static', 'uploads', 'produtos', fname)
        if os.path.exists(fpath):
            url = f'/static/uploads/produtos/{quote(fname)}'
            urls.append(f'{url} {w}w')
    if not urls:
        return webp_smart_filter(caminho_imagem) + ' 600w'
    return ', '.join(urls)


# ===== CSRF TOKEN (para Instagram WebView) =====

@app.route('/csrf-token')
@limite_csrf
def csrf_token_api():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'token': generate_csrf()})


# ===== HEALTH CHECK =====

@app.route('/health')
def health():
    db_ok = False
    try:
        conn = get_db()
        conn.execute('SELECT 1')
        db_ok = True
    except Exception:
        db_ok = False
    finally:
        close_db()

    uptime_sec = int(time.time() - START_TIME)
    uptime_str = f'{uptime_sec // 86400}d {(uptime_sec % 86400) // 3600}h {(uptime_sec % 3600) // 60}m'

    return jsonify({
        'status': 'ok' if db_ok else 'degraded',
        'db': 'ok' if db_ok else 'error',
        'uptime': uptime_str,
        'uptime_seconds': uptime_sec,
    }), 200 if db_ok else 503


# ===== ERROR HANDLERS =====

@app.errorhandler(404)
def pagina_nao_encontrada(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def erro_interno(e):
    log.error(f"Erro 500: {e}")
    return render_template('500.html'), 500


@app.errorhandler(429)
def rate_limit_exceeded(e):
    return render_template('429.html'), 429


@app.errorhandler(400)
def bad_request(e):
    from flask_wtf.csrf import CSRFError
    if isinstance(e.description, CSRFError) or 'csrf' in str(e.description).lower():
        log.warning(f"CSRF error: {e.description}")
        return render_template('400.html', mensagem='Sessão expirada. Volte à página anterior e recarregue para tentar novamente.'), 400
    log.warning(f"Erro 400: {e.description}")
    return render_template('400.html', mensagem=str(e.description) if e.description else None), 400


# ===== REGISTRAR BLUEPRINTS =====

app.register_blueprint(public_bp)
app.register_blueprint(checkout_bp)
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)


# ===== INICIALIZAÇÃO =====

if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=5000
    )
