import os
import json
import time
import logging
import csv
import io
from urllib.parse import quote
from datetime import datetime, timedelta, timezone

from flask import (Flask, render_template, request, jsonify,
                   redirect, session, url_for, send_from_directory,
                   make_response, Response, flash)
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import check_password_hash
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config, WHATSAPP_NUMBER, WHATSAPP_URL
from models import (BRT, init_db, get_db,
                    get_produtos, get_produto,
                    get_produtos_paginados, count_produtos,
                    add_produto, edit_produto, toggle_visivel, toggle_estoque,
                    deletar_produto, get_pedidos, get_pedido, add_pedido,
                    get_pedidos_paginados, get_pedidos_filtrados, get_pedidos_by_telefone,
                    buscar_global, get_admin_logs,
                    update_pedido_status, delete_pedido, login_required,
                    processar_imagens_request,
                    add_aviso, count_avisos_pendentes, get_avisos_pendentes,
                    marcar_notificados, criar_indices,
                    close_db)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# ProxyFix: essencial quando rodando atrás de Nginx
# Ajusta X-Forwarded-For, X-Forwarded-Proto para gerar URLs HTTPS corretas
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

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["2000 per day", "300 per hour", "10 per second"],
    storage_uri=os.environ.get('RATE_LIMIT_STORAGE', 'memory://'),
)

# Decorators de rate limit específicos (aplicados nas rotas abaixo)
limite_login = limiter.limit("5 per minute")
limite_checkout = limiter.limit("10 per minute")
limite_csrf = limiter.limit("30 per minute")
limite_busca = limiter.limit("60 per minute")
limite_aviso = limiter.limit("5 per minute")
limite_pedidos = limiter.limit("10 per minute")

init_db()
criar_indices()

app.teardown_appcontext(close_db)

# Timestamp de inicialização (para health check)
START_TIME = time.time()


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
    return dict(csrf_token=generate_csrf, static_version=version)


# ===== SEO =====

@app.route('/sitemap.xml')
def sitemap():
    produtos = get_produtos(todos=False)
    pages = [
        {'loc': url_for('index', _external=True), 'priority': '1.0'},
        {'loc': url_for('nossa_historia', _external=True), 'priority': '0.8'},
        {'loc': url_for('contato', _external=True), 'priority': '0.7'},
        {'loc': url_for('politicas', _external=True), 'priority': '0.6'},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        xml += f'  <url><loc>{p["loc"]}</loc><priority>{p["priority"]}</priority></url>\n'
    for prod in produtos:
        url = url_for('produto_detalhe', produto_id=prod['id'], _external=True)
        xml += f'  <url><loc>{url}</loc><priority>0.9</priority></url>\n'
    xml += '</urlset>'
    resp = make_response(xml)
    resp.content_type = 'application/xml'
    return resp


@app.route('/robots.txt')
def robots():
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://defumadosac.com.br/sitemap.xml\n",
        mimetype='text/plain'
    )


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


# ===== FILTROS JINJA2 =====

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


# ===== CSRF TOKEN (para Instagram WebView) =====

@app.route('/csrf-token')
@limite_csrf
def csrf_token_api():
    return jsonify({'token': generate_csrf()})


# ===== ROTAS PÚBLICAS =====

@app.route('/')
def index():
    sort_by = request.args.get('sort', 'nome')
    search = request.args.get('q', '').strip()
    produtos = get_produtos(todos=False, order_by=sort_by, search=search)
    return render_template('index.html', produtos=produtos,
                           current_sort=sort_by, search=search)


@app.route('/produto/<int:produto_id>')
def produto_detalhe(produto_id):
    produto = get_produto(produto_id)
    if not produto or not produto.get('visivel', True):
        return render_template('404.html', mensagem='Produto não encontrado ou indisponível'), 404

    mais_vendidos = get_produtos(todos=False, order_by='vendas')
    relacionados = [p for p in mais_vendidos if p['id'] != produto_id][:4]

    return render_template('produto.html',
                           produto=produto,
                           relacionados=relacionados,
                            now=datetime.now(BRT))


@app.route('/api/produtos')
def api_produtos():
    return jsonify(get_produtos(todos=False))


@app.route('/api/busca')
@limite_busca
def api_busca():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    resultados = get_produtos(todos=False, search=q)
    return jsonify([{
        'id': p['id'],
        'nome': p['nome'],
        'preco': p['preco'],
        'imagem': webp_smart_filter(p['imagens'][0]) if p['imagens'] else None,
        'estoque': p['estoque'],
    } for p in resultados[:8]])


@app.route('/api/produtos/<int:produto_id>')
def api_produto_detalhe(produto_id):
    produto = get_produto(produto_id)
    if produto:
        return jsonify(produto)
    return jsonify({'erro': 'Não encontrado'}), 404


@app.route('/nossa-historia')
def nossa_historia():
    return render_template('sobre.html')


@app.route('/politicas')
def politicas():
    return render_template('politicas.html')


@app.route('/contato')
def contato():
    return render_template('contato.html')


@app.route('/imagens/<path:filename>')
def servir_imagem(filename):
    return send_from_directory('public/imagens', filename)


# ===== CARRINHO / CHECKOUT =====

@app.route('/checkout')
def checkout():
    return render_template('checkout.html')


@app.route('/finalizar', methods=['POST'])
@csrf.exempt
@limite_checkout
def finalizar():
    dados = request.json
    itens = dados.get('itens', [])
    nome = dados.get('nome', 'Não informado')
    telefone = dados.get('telefone', 'Não informado')
    endereco = dados.get('endereco', 'Não informado')
    cep = dados.get('cep', 'Não informado')
    frete_metodo = dados.get('frete_metodo', 'Não selecionado')
    frete_valor = dados.get('frete_valor', 0.0)
    total = dados.get('total', 0.0)

    try:
        frete_valor = float(frete_valor) if frete_valor else 0.0
        total = float(total) if total else 0.0
    except (ValueError, TypeError):
        frete_valor = 0.0
        total = 0.0

    itens_formatados = '\n'.join([
        f"• {i['nome']} x{i['qtd']} = R$ {i['preco']*i['qtd']:.2f}"
        for i in itens
    ])

    if frete_valor > 0:
        linha_frete = f"📦 *Frete:* R$ {frete_valor:.2f} (Tarifa fixa RJ)"
        linha_total = f"💵 *TOTAL:* R$ {total:.2f}"
    else:
        linha_frete = "📦 *Frete:* Sob consulta (Correios/Transportadora)"
        linha_total = f"💵 *TOTAL:* R$ {total:.2f} + frete a combinar"

    msg = f"""🛒 *NOVO PEDIDO - DEFUMADOS AC*
    
👤 *Cliente:* {nome}
📱 *Contato:* {telefone}
📍 *CEP:* {cep}
🏠 *Endereço:* {endereco}
🚚 *Entrega:* {frete_metodo}

📦 *Itens:*
{itens_formatados}

{linha_frete}
{linha_total}

_Obrigado pela preferência! Aguarde a confirmação do pedido._ 🐷✨"""

    url = f"{WHATSAPP_URL}&text={quote(msg, safe='', encoding='utf-8')}"
    return jsonify({'redirect': url})


@app.route('/checkout/process', methods=['POST'])
@csrf.exempt
@limite_checkout
def process_checkout():
    consentimento = request.form.get('lgpd_consent')
    if consentimento != '1':
        flash('É necessário aceitar a Política de Privacidade para finalizar o pedido.', 'error')
        return redirect(url_for('checkout'))

    nome = request.form.get('nome', '').strip()
    telefone = request.form.get('telefone', '').strip()
    telefone = ''.join(c for c in telefone if c.isdigit())
    email = request.form.get('email', '').strip()
    cep = request.form.get('cep', '').strip()
    endereco = request.form.get('endereco', '').strip()
    numero = request.form.get('numero', '').strip()
    complemento = request.form.get('complemento', '').strip()
    bairro = request.form.get('bairro', '').strip()
    cidade = request.form.get('cidade', '').strip()
    estado = request.form.get('estado', '').strip()
    referencia = request.form.get('referencia', '').strip()
    forma_entrega = request.form.get('forma_entrega', 'Entrega').strip()

    try:
        frete_valor = float(request.form.get('frete_valor', 0) or 0)
    except (ValueError, TypeError):
        frete_valor = 0.0
    frete_texto = request.form.get('frete_texto', 'A combinar')

    itens_json = request.form.get('carrinho_json', '[]')
    try:
        itens = json.loads(itens_json)
    except (json.JSONDecodeError, TypeError):
        itens = []

    if not nome or not telefone or not endereco or len(itens) == 0:
        flash('Dados incompletos. Por favor, preencha todos os campos obrigatórios.', 'error')
        return redirect(url_for('checkout'))

    total = sum(item['preco'] * item['qtd'] for item in itens)
    pedido_id = add_pedido(nome, telefone, endereco, numero, complemento,
                           bairro, cidade, estado, referencia, email,
                           cep, forma_entrega, itens_json, total,
                           frete_valor, frete_texto)

    log.info(f"Pedido #{pedido_id} registrado por {nome} ({telefone})")

    endereco_completo = f"{endereco}, {numero}" + (f" - {complemento}" if complemento else "")
    msg = f"*🛒 NOVO PEDIDO #{pedido_id} - DEFUMADOS AC*\n\n"
    msg += f"📋 *DADOS DO CLIENTE:*\n"
    msg += f"👤 Nome: {nome}\n"
    msg += f"📱 Telefone: {telefone}\n"
    if email:
        msg += f"📧 E-mail: {email}\n"
    msg += f"\n📍 *ENDEREÇO DE ENTREGA:*\n"
    msg += f"📮 CEP: {cep}\n"
    msg += f"🏠 {endereco_completo}\n"
    msg += f"🏘️ Bairro: {bairro}\n"
    msg += f"🌆 Cidade: {cidade}/{estado}\n"
    if referencia:
        msg += f"📍 Referência: {referencia}\n"
    msg += f"\n🚚 *ENTREGA:*\n"
    msg += f"Tipo: {forma_entrega}\n"
    msg += f"Frete: {frete_texto}\n\n"
    msg += f"📦 *PRODUTOS:*\n"
    for item in itens:
        msg += f"▪️ {item['qtd']}x {item['nome']}\n"
        msg += f"   R$ {(item['preco']*item['qtd']):.2f}\n"
    msg += f"\n💰 *TOTAL DO PEDIDO:*\n"
    msg += f"Subtotal: R$ {total:.2f}\n"
    if frete_valor > 0:
        msg += f"Frete: R$ {frete_valor:.2f}\n"
        msg += f"*TOTAL: R$ {(total + frete_valor):.2f}*\n"
    else:
        msg += f"Frete: A combinar\n"
        msg += f"*TOTAL: R$ {total:.2f} (sem frete)*\n"
    msg += f"\n✅ *Obrigado pela preferência!*\n"
    msg += f"Aguarde a confirmação do pedido.\n"
    msg += f"💬 *Pedido #{pedido_id} gerado automaticamente pelo site*"

    wa_link = f"{WHATSAPP_URL}&text={quote(msg, safe='', encoding='utf-8')}"
    return redirect(wa_link)


# ===== MEUS PEDIDOS (PÚBLICO) =====

@app.route('/meus-pedidos', methods=['GET', 'POST'])
@limite_pedidos
def meus_pedidos():
    pedidos = []
    telefone = ''
    buscou = False

    if request.method == 'POST':
        telefone = request.form.get('telefone', '').strip()
        buscou = True
        if telefone:
            pedidos = get_pedidos_by_telefone(telefone)

    return render_template('meus_pedidos.html',
                           pedidos=pedidos,
                           telefone=telefone,
                           buscou=buscou)


@app.route('/meus-pedidos/<int:pedido_id>')
def meus_pedidos_detalhe(pedido_id):
    pedido = get_pedido(pedido_id)
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('meus_pedidos_detalhe.html', pedido=pedido)


# ===== ROTAS ADMIN =====

@app.route('/admin/login', methods=['GET', 'POST'])
@limite_login
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        user = request.form.get('username')
        password = request.form.get('password')
        if (user == Config.ADMIN_USER and
                check_password_hash(Config.ADMIN_PASS_HASH, password)):
            session['admin_logged_in'] = True
            session.permanent = True
            log.info(f"Admin login bem-sucedido: {user}")
            return redirect(url_for('admin_dashboard'))
        log.warning(f"Tentativa de login inválida para usuário: {user}")
        return render_template('admin/login.html', erro='Usuário ou senha inválidos')

    return render_template('admin/login.html', erro=None)


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))


@app.route('/admin')
@login_required
def admin_dashboard():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    produtos, total_paginas = get_produtos_paginados(page=page, per_page=15, todos=True, search=q)
    avisos_count = {p['id']: count_avisos_pendentes(p['id']) for p in produtos}
    total_produtos = count_produtos(todos=True, search=q)
    visiveis = count_produtos(todos=False, search=q)
    hoje = datetime.now(BRT).strftime('%Y-%m-%d')
    with get_db() as conn:
        pedidos_hoje = conn.execute("SELECT COUNT(*), COALESCE(SUM(total), 0) FROM pedidos WHERE date(data_criacao) = ? AND status != 'cancelado'", (hoje,)).fetchone()
    return render_template('admin/dashboard.html',
                           produtos=produtos,
                           page=page,
                           total_paginas=total_paginas,
                           avisos_count=avisos_count,
                           q=q,
                           stats={
                               'total_produtos': total_produtos,
                               'visiveis': visiveis,
                               'pedidos_hoje': pedidos_hoje[0],
                               'faturamento_hoje': pedidos_hoje[1],
                           })


@app.route('/admin/add', methods=['POST'])
@login_required
def admin_add_produto():
    try:
        preco_str = request.form.get('preco', '0').replace(',', '.')
        preco = float(preco_str)
    except (ValueError, TypeError):
        return "❌ Preço inválido.", 400

    imagens = processar_imagens_request(request)

    add_produto(
        nome=request.form.get('nome', ''),
        preco=preco,
        descricao=request.form.get('descricao', ''),
        imagens=imagens,
        estoque=1 if request.form.get('estoque') == 'on' else 0,
        peso=request.form.get('peso', ''),
        ingredientes=request.form.get('ingredientes', '')
    )
    log.info(f"Produto adicionado: {request.form.get('nome')}")
    flash('Produto adicionado com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/edit/<int:produto_id>', methods=['POST'])
@login_required
def admin_edit_produto(produto_id):
    try:
        preco_str = request.form.get('preco', '0').replace(',', '.')
        preco = float(preco_str)
    except (ValueError, TypeError):
        return "❌ Preço inválido.", 400

    imagens_raw = request.form.get('imagens', '').strip()
    arquivos_upload = request.files.getlist('imagens_upload')
    tem_arquivo = any(f.filename for f in arquivos_upload)

    if imagens_raw or tem_arquivo:
        imagens = processar_imagens_request(request)
    else:
        imagens = None

    edit_produto(
        produto_id=produto_id,
        nome=request.form.get('nome'),
        preco=preco,
        descricao=request.form.get('descricao'),
        estoque=1 if request.form.get('estoque') == 'on' else 0,
        peso=request.form.get('peso', ''),
        ingredientes=request.form.get('ingredientes', ''),
        imagens=imagens
    )
    log.info(f"Produto #{produto_id} editado")
    flash('Produto atualizado com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/visivel/<int:produto_id>', methods=['POST'])
@login_required
def admin_toggle_visivel(produto_id):
    toggle_visivel(produto_id)
    log.info(f"Produto #{produto_id} visível alternado")
    flash('Visibilidade do produto alterada!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/toggle/<int:produto_id>', methods=['POST'])
@login_required
def admin_toggle_estoque(produto_id):
    toggle_estoque(produto_id)
    log.info(f"Produto #{produto_id} estoque alternado")
    flash('Estoque do produto alterado!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/deletar/<int:produto_id>', methods=['POST'])
@login_required
def admin_deletar_produto(produto_id):
    deletar_produto(produto_id)
    log.info(f"Produto #{produto_id} deletado")
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notificar/<int:produto_id>', methods=['GET'])
@login_required
def admin_notificar(produto_id):
    produto = get_produto(produto_id)
    if not produto:
        return render_template('404.html', mensagem='Produto não encontrado'), 404

    avisos = list(get_avisos_pendentes(produto_id))
    marcar_notificados(produto_id)

    if not produto['estoque']:
        toggle_estoque(produto_id)

    return render_template('admin/notificar.html',
                          produto=produto, avisos=avisos,
                          whatsapp_url=WHATSAPP_URL)


# ===== API =====

@app.route('/api/avisar-estoque', methods=['POST'])
@csrf.exempt
@limite_aviso
def api_avisar_estoque():
    data = request.json
    if not data:
        return jsonify({'erro': 'Dados inválidos'}), 400

    produto_id = data.get('produto_id')
    nome = data.get('nome', '').strip()
    email = data.get('email', '').strip()
    telefone = data.get('telefone', '').strip()

    if not produto_id or not nome:
        return jsonify({'erro': 'Campos obrigatórios: produto_id, nome'}), 400

    aviso_id = add_aviso(produto_id, nome, email, telefone)
    return jsonify({'success': True, 'id': aviso_id})


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


# ===== ADMIN: PEDIDOS =====

@app.route('/admin/pedidos')
@login_required
def admin_pedidos():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    pedidos, total_paginas = get_pedidos_paginados(page=page, per_page=20, search=q, status=status)
    return render_template('admin/pedidos.html',
                           pedidos=pedidos,
                           page=page,
                           total_paginas=total_paginas,
                           q=q,
                           status_filter=status)


@app.route('/admin/pedidos/<int:pedido_id>')
@login_required
def admin_pedido_detalhe(pedido_id):
    pedido = get_pedido(pedido_id)
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('admin/pedido_detalhe.html', pedido=pedido)


@app.route('/admin/pedidos/<int:pedido_id>/status', methods=['POST'])
@login_required
def admin_update_pedido_status(pedido_id):
    novo_status = request.form.get('status')
    update_pedido_status(pedido_id, novo_status)
    flash('Status do pedido atualizado!', 'success')
    return redirect(url_for('admin_pedido_detalhe', pedido_id=pedido_id))


@app.route('/admin/pedidos/<int:pedido_id>/delete', methods=['POST'])
@login_required
def admin_delete_pedido(pedido_id):
    delete_pedido(pedido_id)
    log.info(f"Pedido #{pedido_id} deletado")
    flash('Pedido excluído com sucesso!', 'success')
    return redirect(url_for('admin_pedidos'))


@app.route('/admin/pedidos/bulk', methods=['POST'])
@login_required
def admin_pedidos_bulk():
    pedido_ids = request.form.getlist('pedido_ids')
    action = request.form.get('action')

    if not pedido_ids or not action:
        flash('Nenhum pedido selecionado.', 'error')
        return redirect(url_for('admin_pedidos'))

    count = len(pedido_ids)

    if action == 'delete':
        for pid in pedido_ids:
            delete_pedido(int(pid))
        log.info(f"{count} pedido(s) deletado(s) em massa")
        flash(f'{count} pedido(s) excluído(s) com sucesso!', 'success')
    else:
        for pid in pedido_ids:
            update_pedido_status(int(pid), action)
        log.info(f"{count} pedido(s) atualizado(s) para '{action}' em massa")
        flash(f'{count} pedido(s) atualizado(s) para "{action}"!', 'success')

    return redirect(url_for('admin_pedidos'))


@app.route('/admin/api/search')
@login_required
def admin_api_search():
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    results = buscar_global(search=q, limit=min(limit, 20))
    
    # Format for frontend
    return jsonify({
        'produtos': [{
            'id': p['id'],
            'nome': p['nome'],
            'preco': p['preco'],
            'estoque': p['estoque'],
            'visivel': p['visivel'],
            'thumb': p['thumb'],
            'url': f'/admin/edit/{p["id"]}'  # placeholder, could be detail view
        } for p in results['produtos']],
        'pedidos': [{
            'id': p['id'],
            'cliente_nome': p['cliente_nome'],
            'cliente_telefone': p['cliente_telefone'],
            'total': p['total'],
            'status': p['status'],
            'data_criacao': p['data_criacao'],
            'url': f'/admin/pedidos/{p["id"]}'
        } for p in results['pedidos']]
    })


@app.route('/admin/logs')
@login_required
def admin_logs():
    page = request.args.get('page', 1, type=int)
    level = request.args.get('level', '').strip()
    q = request.args.get('q', '').strip()
    logs, total_paginas, total = get_admin_logs(page=page, per_page=50, level=level, search=q)
    return render_template('admin/logs.html',
                           logs=logs,
                           page=page,
                           total_paginas=total_paginas,
                           total=total,
                           level=level,
                           q=q)


@app.route('/admin/pedidos/export')
@login_required
def admin_pedidos_export():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    pedidos = get_pedidos_filtrados(search=q, status=status)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    # Header
    writer.writerow([
        'ID', 'Cliente', 'Telefone', 'Email', 'CEP',
        'Endereço', 'Número', 'Complemento', 'Bairro', 'Cidade', 'Estado', 'Referência',
        'Forma Entrega', 'Frete Valor', 'Frete Texto',
        'Itens', 'Total', 'Status', 'Data Criação'
    ])

    for p in pedidos:
        # Parse itens JSON para texto legível
        itens_texto = ''
        try:
            itens = json.loads(p['itens']) if p['itens'] else []
            itens_texto = '; '.join([f"{i.get('qtd', 1)}x {i.get('nome', '')}" for i in itens])
        except (json.JSONDecodeError, TypeError):
            itens_texto = p['itens'] or ''

        writer.writerow([
            p['id'],
            p['cliente_nome'] or '',
            p['cliente_telefone'] or '',
            p['email'] or '',
            p['cep'] or '',
            p['endereco'] or '',
            p['numero_casa'] or '',
            p['complemento'] or '',
            p['bairro'] or '',
            p['cidade'] or '',
            p['estado'] or '',
            p['referencia'] or '',
            p['forma_entrega'] or '',
            f"{p['frete_valor']:.2f}" if p['frete_valor'] else '',
            p['frete_texto'] or '',
            itens_texto,
            f"{p['total']:.2f}" if p['total'] else '',
            p['status'] or '',
            p['data_criacao'] or ''
        ])

    output.seek(0)
    filename = f'pedidos_{datetime.now(BRT).strftime("%Y%m%d_%H%M%S")}.csv'
    return Response(
        output.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


# ===== INICIALIZAÇÃO =====

if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        host=os.environ.get('FLASK_HOST', '127.0.0.1'),
        port=5000
    )
