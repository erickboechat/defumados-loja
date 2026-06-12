import os
import re
import uuid
import sqlite3
import json
from datetime import datetime, timezone, timedelta
from functools import wraps
from PIL import Image

import flask
from flask import g, session, redirect, url_for

from config import Config

BRT = timezone(timedelta(hours=-3))

# Sinônimos e variações ortográficas para busca inteligente
SINONIMOS = {
    'coppa': 'copa',
    'copa': 'copa',
    'costela': 'costelinha',
    'costelinha': 'costelinha',
    'costela defumada': 'costelinha',
    'bacon': 'bacon',
    'panceta': 'bacon',
    'pancceta': 'bacon',
    'pancetta': 'bacon',
    'barriga': 'bacon',
    'touchino': 'bacon',
    'toucinho': 'bacon',
    'linguica': 'linguiça',
    'linguiça': 'linguiça',
    'calabresa': 'linguiça calabresa',
    'calabreza': 'linguiça calabresa',
    'paio': 'linguiça paio',
    'lombo': 'copa',
    'presunto': 'copa',
    'carne seca': 'copa',
    'porco': '',
    'defumado': '',
    'artesanal': '',
    'caseiro': '',
    'fatiado': '',
    'picado': '',
    'peça': '',
    'peca': '',
    'noz': 'noz manteiga',
    'noz manteiga': 'noz manteiga',
    'manteiga': 'noz manteiga',
    'salame': 'salame',
    'salaminho': 'salame',
    'salame italiano': 'salame italiano',
    'salamin': 'salame',
    'cheddar': 'linguiça cheddar',
    'chedar': 'linguiça cheddar',
    'cheda': 'linguiça cheddar',
}


def normalizar(texto):
    """Remove acentos e converte para minúsculas"""
    import unicodedata
    return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower().strip()


# ===== CONFIGURAÇÕES DE UPLOAD =====

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'produtos')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MAX_IMAGE_SIZE = (1200, 1200)



# ===== CONEXÃO =====

def _nova_conexao():
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_db():
    """Conecta ao banco — reusa conexão do flask.g quando em contexto de request"""
    if flask.has_app_context():
        if 'db' not in g:
            g.db = _nova_conexao()
        return g.db
    return _nova_conexao()


def close_db(e=None):
    if flask.has_app_context():
        db = g.pop('db', None)
        if db is not None:
            db.close()


def init_db():
    """Cria as tabelas se não existirem"""
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS produtos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                descricao TEXT,
                imagens TEXT,
                estoque INTEGER DEFAULT 1,
                visivel INTEGER DEFAULT 1,
                peso TEXT DEFAULT '',
                ingredientes TEXT DEFAULT ''
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_nome TEXT NOT NULL,
                cliente_telefone TEXT,
                endereco TEXT,
                numero_casa TEXT DEFAULT '',
                complemento TEXT DEFAULT '',
                bairro TEXT DEFAULT '',
                cidade TEXT DEFAULT '',
                estado TEXT DEFAULT '',
                referencia TEXT DEFAULT '',
                email TEXT DEFAULT '',
                forma_entrega TEXT DEFAULT '',
                itens TEXT,
                total REAL,
                status TEXT DEFAULT 'registrado',
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                cep TEXT DEFAULT '',
                frete_valor REAL DEFAULT 0.0,
                frete_texto TEXT DEFAULT ''
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS avisos_estoque (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produto_id INTEGER NOT NULL,
                nome TEXT NOT NULL,
                email TEXT DEFAULT '',
                telefone TEXT DEFAULT '',
                notificado INTEGER DEFAULT 0,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (produto_id) REFERENCES produtos(id)
            )
        ''')
        # Migração segura: adiciona colunas que podem não existir em DBs antigos
        for col in ['cidade', 'estado', 'referencia', 'email']:
            try:
                conn.execute(f'ALTER TABLE pedidos ADD COLUMN {col} TEXT DEFAULT ""')
            except sqlite3.OperationalError:
                pass  # coluna já existe


# ===== PARSER UNIFICADO =====

def parse_produto(row):
    """Converte uma linha SQL do produto em dict tratado"""
    p = dict(row)
    p['imagens'] = json.loads(p['imagens']) if p.get('imagens') else []
    p['estoque'] = bool(p['estoque'])
    p['visivel'] = bool(p.get('visivel', True))
    p['preco'] = float(p['preco'])
    p['peso'] = p.get('peso', '')
    p['ingredientes'] = p.get('ingredientes', '')
    return p


# ===== PRODUTOS =====

def get_produtos(todos=False, order_by='nome', search=''):
    """Retorna lista de produtos, com filtro opcional por nome"""
    with get_db() as conn:
        params = []
        clausulas_where = []

        if not todos:
            clausulas_where.append('visivel = 1')

        if search:
            clausulas_where.append('nome LIKE ?')
            params.append(f'%{search}%')

        query = 'SELECT * FROM produtos'
        if clausulas_where:
            query += ' WHERE ' + ' AND '.join(clausulas_where)

        if order_by == 'preco_asc':
            query += ' ORDER BY preco ASC'
        elif order_by == 'preco_desc':
            query += ' ORDER BY preco DESC'
        elif order_by == 'nome_desc':
            query += ' ORDER BY nome COLLATE NOCASE DESC'
        else:
            query += ' ORDER BY nome COLLATE NOCASE ASC'

        rows = conn.execute(query, params).fetchall()
        produtos = [parse_produto(row) for row in rows]

        # Se não achou nada com LIKE, tenta busca inteligente
        if not produtos and search:
            produtos = _busca_inteligente(conn, search, todos, order_by)

        if order_by == 'vendas':
            for p in produtos:
                p['vendas'] = get_vendas_reais(conn, p['id'])
            produtos.sort(key=lambda x: x['vendas'], reverse=True)
        else:
            for p in produtos:
                p['vendas'] = 0

    return produtos


def _busca_inteligente(conn, search, todos, order_by):
    """Tenta encontrar produtos com busca expandida (sinônimos + normalização)"""
    search_norm = normalizar(search)
    termos = search_norm.split()

    # Busca todos os produtos visíveis
    query = 'SELECT * FROM produtos'
    clausulas = []
    if not todos:
        clausulas.append('visivel = 1')
    if clausulas:
        query += ' WHERE ' + ' AND '.join(clausulas)
    rows = conn.execute(query).fetchall()
    todos_produtos = [parse_produto(row) for row in rows]

    resultados = []

    for p in todos_produtos:
        nome_norm = normalizar(p['nome'])
        score = 0

        # 1. Verifica se cada termo da busca aparece no nome normalizado
        for termo in termos:
            if termo and termo in nome_norm:
                score += 2

        # 2. Verifica sinônimos
        for termo in termos:
            if termo == '':
                continue
            sinonimo = SINONIMOS.get(termo)
            if sinonimo:
                if sinonimo == '':
                    score += 1  # termo genérico (ex: "defumado", "porco")
                elif sinonimo in nome_norm:
                    score += 3 if termo != sinonimo else 2

        if score > 0:
            p['_score'] = score
            resultados.append(p)

    resultados.sort(key=lambda x: x['_score'], reverse=True)
    return resultados[:20]


def count_produtos(todos=False, search=''):
    """Retorna o total de produtos (para paginação)"""
    with get_db() as conn:
        query = 'SELECT COUNT(*) FROM produtos'
        params = []
        conditions = []
        if not todos:
            conditions.append('visivel = 1')
        if search:
            conditions.append('nome LIKE ?')
            params.append(f'%{search}%')
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        return conn.execute(query, params).fetchone()[0]


def get_produtos_paginados(page=1, per_page=15, todos=False, order_by='nome', search=''):
    """Retorna (produtos, total_paginas) com paginação"""
    total = count_produtos(todos=todos, search=search)
    total_paginas = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    with get_db() as conn:
        query = 'SELECT * FROM produtos'
        params = []
        conditions = []
        if not todos:
            conditions.append('visivel = 1')
        if search:
            conditions.append('nome LIKE ?')
            params.append(f'%{search}%')
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)

        if order_by == 'preco_asc':
            query += ' ORDER BY preco ASC'
        elif order_by == 'preco_desc':
            query += ' ORDER BY preco DESC'
        elif order_by == 'nome_desc':
            query += ' ORDER BY nome COLLATE NOCASE DESC'
        else:
            query += ' ORDER BY nome COLLATE NOCASE ASC'

        query += ' LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        rows = conn.execute(query, params).fetchall()
        produtos = [parse_produto(row) for row in rows]

        if order_by == 'vendas':
            for p in produtos:
                p['vendas'] = get_vendas_reais(conn, p['id'])
            produtos.sort(key=lambda x: x['vendas'], reverse=True)
        else:
            for p in produtos:
                p['vendas'] = 0

    return produtos, total_paginas


def get_produto(produto_id):
    """Busca um produto pelo ID (independe de visibilidade)"""
    with get_db() as conn:
        row = conn.execute('SELECT * FROM produtos WHERE id = ?', (produto_id,)).fetchone()
        return parse_produto(row) if row else None


def get_vendas_reais(conn, produto_id):
    """Conta unidades vendidas em pedidos com status 'concluido'"""
    total = 0
    rows = conn.execute("SELECT itens FROM pedidos WHERE status = 'concluido'").fetchall()
    for row in rows:
        try:
            itens = json.loads(row['itens'])
            for item in itens:
                if item.get('id') == produto_id:
                    total += item.get('qtd', 0)
        except (json.JSONDecodeError, TypeError):
            continue
    return total


# ===== ADMIN: CRUD PRODUTOS =====

def add_produto(nome, preco, descricao, imagens, estoque, peso='', ingredientes=''):
    """Adiciona um novo produto ao banco"""
    with get_db() as conn:
        conn.execute('''
            INSERT INTO produtos (nome, preco, descricao, imagens, estoque, peso, ingredientes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, preco, descricao, json.dumps(imagens, ensure_ascii=False), estoque, peso, ingredientes))


def edit_produto(produto_id, nome, preco, descricao, estoque, peso='', ingredientes='', imagens=None):
    """Atualiza um produto existente"""
    with get_db() as conn:
        if imagens is not None:
            conn.execute('''
                UPDATE produtos
                SET nome=?, preco=?, descricao=?, imagens=?, estoque=?, peso=?, ingredientes=?
                WHERE id=?
            ''', (nome, preco, descricao, json.dumps(imagens, ensure_ascii=False),
                  estoque, peso, ingredientes, produto_id))
        else:
            conn.execute('''
                UPDATE produtos
                SET nome=?, preco=?, descricao=?, estoque=?, peso=?, ingredientes=?
                WHERE id=?
            ''', (nome, preco, descricao, estoque, peso, ingredientes, produto_id))


def toggle_visivel(produto_id):
    """Alterna entre visível/oculto"""
    with get_db() as conn:
        conn.execute('UPDATE produtos SET visivel = 1 - visivel WHERE id = ?', (produto_id,))


def toggle_estoque(produto_id):
    """Alterna entre em estoque/esgotado"""
    with get_db() as conn:
        conn.execute('UPDATE produtos SET estoque = NOT estoque WHERE id = ?', (produto_id,))


def deletar_produto(produto_id):
    """Remove um produto do banco"""
    with get_db() as conn:
        conn.execute('DELETE FROM produtos WHERE id = ?', (produto_id,))


# ===== PEDIDOS =====

def get_pedidos():
    """Retorna todos os pedidos ordenados do mais recente"""
    with get_db() as conn:
        return conn.execute('SELECT * FROM pedidos ORDER BY data_criacao DESC').fetchall()


def count_pedidos(search='', status=''):
    """Retorna o total de pedidos (para paginação)"""
    with get_db() as conn:
        query = 'SELECT COUNT(*) FROM pedidos'
        params = []
        conditions = []
        if search:
            conditions.append('(cliente_nome LIKE ? OR cliente_telefone LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%'])
        if status:
            conditions.append('status = ?')
            params.append(status)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        return conn.execute(query, params).fetchone()[0]


def get_pedidos_paginados(page=1, per_page=20, search='', status=''):
    """Retorna (pedidos, total_paginas) com paginação"""
    total = count_pedidos(search=search, status=status)
    total_paginas = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    with get_db() as conn:
        query = 'SELECT * FROM pedidos'
        params = []
        conditions = []
        if search:
            conditions.append('(cliente_nome LIKE ? OR cliente_telefone LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%'])
        if status:
            conditions.append('status = ?')
            params.append(status)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY data_criacao DESC LIMIT ? OFFSET ?'
        params.extend([per_page, offset])
        rows = conn.execute(query, params).fetchall()

    return rows, total_paginas


def get_pedidos_filtrados(search='', status=''):
    """Retorna TODOS os pedidos filtrados (sem paginação, para export CSV)"""
    with get_db() as conn:
        query = 'SELECT * FROM pedidos'
        params = []
        conditions = []
        if search:
            conditions.append('(cliente_nome LIKE ? OR cliente_telefone LIKE ?)')
            params.extend([f'%{search}%', f'%{search}%'])
        if status:
            conditions.append('status = ?')
            params.append(status)
        if conditions:
            query += ' WHERE ' + ' AND '.join(conditions)
        query += ' ORDER BY data_criacao DESC'
        rows = conn.execute(query, params).fetchall()

    return rows


def buscar_global(search='', limit=10):
    """Busca global: produtos + pedidos. Retorna dict com resultados limitados."""
    if not search or len(search.strip()) < 2:
        return {'produtos': [], 'pedidos': []}
    
    search = search.strip()
    like = f'%{search}%'
    
    with get_db() as conn:
        # Buscar produtos
        produtos_rows = conn.execute('''
            SELECT id, nome, preco, estoque, visivel, imagens
            FROM produtos
            WHERE nome LIKE ?
            ORDER BY 
                CASE WHEN nome LIKE ? THEN 0 ELSE 1 END,
                nome
            LIMIT ?
        ''', (like, f'{search}%', limit)).fetchall()
        
        # Buscar pedidos
        pedidos_rows = conn.execute('''
            SELECT id, cliente_nome, cliente_telefone, total, status, data_criacao
            FROM pedidos
            WHERE cliente_nome LIKE ? OR cliente_telefone LIKE ?
            ORDER BY data_criacao DESC
            LIMIT ?
        ''', (like, like, limit)).fetchall()
        
        produtos = []
        for p in produtos_rows:
            p = dict(p)
            # Get first image for thumbnail
            try:
                imgs = json.loads(p['imagens']) if p['imagens'] else []
                p['thumb'] = imgs[0] if imgs else None
            except:
                p['thumb'] = None
            produtos.append(p)
        
        pedidos = [dict(p) for p in pedidos_rows]
        
        return {'produtos': produtos, 'pedidos': pedidos}


def get_admin_logs(page=1, per_page=50, level='', search=''):
    """Lê app.log e retorna apenas ações do admin (filtra HTTP requests e startup)."""
    import os
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.log')
    
    if not os.path.exists(log_path):
        return [], 0, 1
    
    # Regex: datetime [LEVEL] message
    pattern = re.compile(
        r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) \[(\w+)\] (.+)$'
    )
    
    # Linhas de ruído a filtrar
    NOISE = [' - - [', 'development server', 'Running on', 'Press CTRL+C',
             'StatUpdater', 'GET /static/', 'POST /static/']
    
    logs = []
    try:
        with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # Filtrar ruído HTTP e startup
                if any(n in line for n in NOISE):
                    continue
                m = pattern.match(line)
                if not m:
                    continue
                dt_str, lvl, msg = m.groups()
                # Filtro por nível
                if level and lvl.upper() != level.upper():
                    continue
                # Filtro por busca
                if search and search.lower() not in msg.lower():
                    continue
                logs.append({
                    'datetime': dt_str,
                    'level': lvl.upper(),
                    'message': msg,
                })
    except Exception:
        return [], 0, 1
    
    # Mais recentes primeiro
    logs.reverse()
    
    total = len(logs)
    total_paginas = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_paginas))
    start = (page - 1) * per_page
    page_logs = logs[start:start + per_page]
    
    return page_logs, total_paginas, total


def get_pedidos_by_telefone(telefone):
    """Busca pedidos pelo telefone do cliente (normalizado)"""
    digitos = ''.join(c for c in telefone if c.isdigit())
    if not digitos:
        return []
    with get_db() as conn:
        pattern = '%' + '%'.join(digitos) + '%'
        rows = conn.execute(
            'SELECT * FROM pedidos WHERE cliente_telefone LIKE ? ORDER BY data_criacao DESC',
            (pattern,)
        ).fetchall()
        result = []
        for row in rows:
            p = dict(row)
            try:
                p['itens'] = json.loads(p['itens']) if p['itens'] else []
            except (json.JSONDecodeError, TypeError):
                p['itens'] = []
            result.append(p)
        return result


def get_pedido(pedido_id):
    """Busca um pedido pelo ID e já converte itens para lista"""
    with get_db() as conn:
        row = conn.execute('SELECT * FROM pedidos WHERE id = ?', (pedido_id,)).fetchone()
        if not row:
            return None
        p = dict(row)
        try:
            p['itens'] = json.loads(p['itens']) if p['itens'] else []
        except (json.JSONDecodeError, TypeError):
            p['itens'] = []
        return p


def add_pedido(nome, telefone, endereco, numero, complemento, bairro, cidade, estado,
               referencia, email, cep, forma_entrega, itens_json,
               total, frete_valor, frete_texto):
    """Registra um novo pedido e retorna o ID"""
    agora = datetime.now(BRT).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO pedidos
                (cliente_nome, cliente_telefone, endereco, numero_casa, complemento,
                 bairro, cidade, estado, referencia, email, cep,
                 forma_entrega, itens, total, status, frete_valor, frete_texto,
                 data_criacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registrado', ?, ?, ?)
        ''', (nome, telefone, endereco, numero, complemento,
              bairro, cidade, estado, referencia, email, cep,
              forma_entrega, itens_json, total, frete_valor, frete_texto,
              agora))
        return cursor.lastrowid


def update_pedido_status(pedido_id, status):
    """Atualiza o status de um pedido"""
    with get_db() as conn:
        conn.execute('UPDATE pedidos SET status = ? WHERE id = ?', (status, pedido_id))


def delete_pedido(pedido_id):
    """Remove um pedido do banco"""
    with get_db() as conn:
        conn.execute('DELETE FROM pedidos WHERE id = ?', (pedido_id,))


# ===== AVISOS DE ESTOQUE =====

def add_aviso(produto_id, nome, email, telefone):
    """Registra um aviso de quando o produto voltar ao estoque"""
    agora = datetime.now(BRT).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO avisos_estoque (produto_id, nome, email, telefone, data_criacao)
            VALUES (?, ?, ?, ?, ?)
        ''', (produto_id, nome, email, telefone, agora))
        return cursor.lastrowid


def count_avisos_pendentes(produto_id):
    """Conta quantos avisos pendentes (não notificados) existem para um produto"""
    with get_db() as conn:
        return conn.execute(
            'SELECT COUNT(*) FROM avisos_estoque WHERE produto_id = ? AND notificado = 0',
            (produto_id,)
        ).fetchone()[0]


def get_avisos_pendentes(produto_id):
    """Retorna lista de avisos pendentes para um produto"""
    with get_db() as conn:
        return conn.execute(
            'SELECT * FROM avisos_estoque WHERE produto_id = ? AND notificado = 0',
            (produto_id,)
        ).fetchall()


def marcar_notificados(produto_id):
    """Marca todos os avisos de um produto como notificados"""
    with get_db() as conn:
        conn.execute(
            'UPDATE avisos_estoque SET notificado = 1 WHERE produto_id = ? AND notificado = 0',
            (produto_id,)
        )


# ===== UPLOAD DE IMAGENS =====

def extensao_permitida(filename):
    """Verifica se a extensão do arquivo é permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def gerar_nome_unico(filename):
    """Gera um nome único para evitar conflitos: timestamp_uuid.ext"""
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
    timestamp = datetime.now(BRT).strftime('%Y%m%d%H%M%S')
    return f"{timestamp}_{uuid.uuid4().hex[:8]}.{ext}"


def salvar_imagem_upload(arquivo):
    """
    Salva um arquivo de imagem enviado pelo formulário.
    - Valida extensão
    - Redimensiona se necessário
    - Converte para WebP automaticamente
    - Retorna a URL pública do arquivo salvo
    """
    if not arquivo or not arquivo.filename:
        return None

    if not extensao_permitida(arquivo.filename):
        return None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    nome_arquivo = gerar_nome_unico(arquivo.filename)
    caminho_temp = os.path.join(UPLOAD_FOLDER, nome_arquivo)

    arquivo.save(caminho_temp)

    try:
        img = Image.open(caminho_temp).convert('RGB')
        img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)

        nome_webp = nome_arquivo.rsplit('.', 1)[0] + '.webp'
        caminho_webp = os.path.join(UPLOAD_FOLDER, nome_webp)
        img.save(caminho_webp, 'WEBP', quality=85)

        os.remove(caminho_temp)

        return f"/static/uploads/produtos/{nome_webp}"
    except Exception:
        return f"/static/uploads/produtos/{nome_arquivo}"


def processar_imagens_request(request):
    """
    Processa imagens enviadas por upload + URLs do textarea.
    Retorna uma lista combinada de URLs de imagens.
    """
    urls = []

    imagens_raw = request.form.get('imagens', '')
    for url in imagens_raw.split('\n'):
        url = url.strip()
        if url:
            urls.append(url)

    arquivos = request.files.getlist('imagens_upload')
    for arquivo in arquivos:
        if arquivo and arquivo.filename:
            url = salvar_imagem_upload(arquivo)
            if url:
                urls.append(url)

    if not urls:
        urls = ['https://via.placeholder.com/300?text=Sem+Foto']

    return urls


# ===== AUTENTICAÇÃO ADMIN =====

def admin_logado():
    """Verifica se o admin está logado pela sessão"""
    return session.get('admin_logged_in', False)


def login_required(f):
    """Decorator que protege rotas admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not admin_logado():
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function


# ===== ÍNDICES DO BANCO =====

def criar_indices():
    """Cria índices para melhor performance"""
    with get_db() as conn:
        for idx in [
            'CREATE INDEX IF NOT EXISTS idx_pedidos_telefone ON pedidos(cliente_telefone)',
            'CREATE INDEX IF NOT EXISTS idx_avisos_produto ON avisos_estoque(produto_id)',
            'CREATE INDEX IF NOT EXISTS idx_produtos_visivel ON produtos(visivel)',
            'CREATE INDEX IF NOT EXISTS idx_pedidos_status ON pedidos(status)',
            'CREATE INDEX IF NOT EXISTS idx_avisos_notificado ON avisos_estoque(notificado)',
        ]:
            try:
                conn.execute(idx)
            except sqlite3.OperationalError:
                pass
