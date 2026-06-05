import os
import uuid
import sqlite3
import json
from functools import wraps
from PIL import Image

from flask import session, redirect, url_for

from config import Config


# ===== CONFIGURAÇÕES DE UPLOAD =====

UPLOAD_FOLDER = os.path.join('static', 'uploads', 'produtos')
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
MAX_IMAGE_SIZE = (1200, 1200)



# ===== CONEXÃO =====

def get_db():
    """Conecta ao banco SQLite e retorna a conexão"""
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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

        if order_by == 'vendas':
            for p in produtos:
                p['vendas'] = get_vendas_reais(conn, p['id'])
            produtos.sort(key=lambda x: x['vendas'], reverse=True)
        else:
            for p in produtos:
                p['vendas'] = 0

    return produtos


def count_produtos(todos=False):
    """Retorna o total de produtos (para paginação)"""
    with get_db() as conn:
        query = 'SELECT COUNT(*) FROM produtos'
        if not todos:
            query += ' WHERE visivel = 1'
        return conn.execute(query).fetchone()[0]


def get_produtos_paginados(page=1, per_page=15, todos=False, order_by='nome'):
    """Retorna (produtos, total_paginas) com paginação"""
    total = count_produtos(todos=todos)
    total_paginas = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    with get_db() as conn:
        query = 'SELECT * FROM produtos'
        if not todos:
            query += ' WHERE visivel = 1'

        if order_by == 'preco_asc':
            query += ' ORDER BY preco ASC'
        elif order_by == 'preco_desc':
            query += ' ORDER BY preco DESC'
        elif order_by == 'nome_desc':
            query += ' ORDER BY nome COLLATE NOCASE DESC'
        else:
            query += ' ORDER BY nome COLLATE NOCASE ASC'

        query += ' LIMIT ? OFFSET ?'
        rows = conn.execute(query, (per_page, offset)).fetchall()
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


def count_pedidos():
    """Retorna o total de pedidos (para paginação)"""
    with get_db() as conn:
        return conn.execute('SELECT COUNT(*) FROM pedidos').fetchone()[0]


def get_pedidos_paginados(page=1, per_page=20):
    """Retorna (pedidos, total_paginas) com paginação"""
    total = count_pedidos()
    total_paginas = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM pedidos ORDER BY data_criacao DESC LIMIT ? OFFSET ?',
            (per_page, offset)
        ).fetchall()

    return rows, total_paginas


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
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO pedidos
                (cliente_nome, cliente_telefone, endereco, numero_casa, complemento,
                 bairro, cidade, estado, referencia, email, cep,
                 forma_entrega, itens, total, status, frete_valor, frete_texto)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registrado', ?, ?)
        ''', (nome, telefone, endereco, numero, complemento,
              bairro, cidade, estado, referencia, email, cep,
              forma_entrega, itens_json, total, frete_valor, frete_texto))
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
    with get_db() as conn:
        cursor = conn.execute('''
            INSERT INTO avisos_estoque (produto_id, nome, email, telefone)
            VALUES (?, ?, ?, ?)
        ''', (produto_id, nome, email, telefone))
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
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
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
