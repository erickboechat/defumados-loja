from flask import (Blueprint, render_template, request, jsonify,
                   send_from_directory, make_response, Response)
from datetime import datetime

from utils import BRT
from models import get_produtos, get_produto, get_pedido, get_pedidos_by_telefone
from extensions import csrf, limiter

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def index():
    sort_by = request.args.get('sort', 'nome')
    search = request.args.get('q', '').strip()
    produtos = get_produtos(todos=False, order_by=sort_by, search=search)
    return render_template('index.html', produtos=produtos,
                           current_sort=sort_by, search=search)


@public_bp.route('/produto/<int:produto_id>')
def produto_detalhe(produto_id):
    from models import get_produtos as _get_produtos
    produto = get_produto(produto_id)
    if not produto or not produto.get('visivel', True):
        return render_template('404.html', mensagem='Produto não encontrado ou indisponível'), 404

    mais_vendidos = _get_produtos(todos=False, order_by='vendas')
    relacionados = [p for p in mais_vendidos if p['id'] != produto_id][:4]

    return render_template('produto.html',
                           produto=produto,
                           relacionados=relacionados,
                           now=datetime.now(BRT))


@public_bp.route('/nossa-historia')
def nossa_historia():
    return render_template('sobre.html')


@public_bp.route('/politicas')
def politicas():
    return render_template('politicas.html')


@public_bp.route('/contato')
def contato():
    return render_template('contato.html')


@public_bp.route('/imagens/<path:filename>')
def servir_imagem(filename):
    return send_from_directory('public/imagens', filename)


# ===== MEUS PEDIDOS =====

@public_bp.route('/meus-pedidos', methods=['GET', 'POST'])
@csrf.exempt
@limiter.limit("10 per minute")
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


@public_bp.route('/meus-pedidos/<int:pedido_id>')
def meus_pedidos_detalhe(pedido_id):
    pedido = get_pedido(pedido_id)
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('meus_pedidos_detalhe.html', pedido=pedido)


# ===== SEO =====

@public_bp.route('/sitemap.xml')
def sitemap():
    from flask import url_for
    produtos = get_produtos(todos=False)
    now = datetime.now(BRT).strftime('%Y-%m-%d')
    pages = [
        {'loc': url_for('public.index', _external=True), 'priority': '1.0', 'lastmod': now},
        {'loc': url_for('public.nossa_historia', _external=True), 'priority': '0.8', 'lastmod': now},
        {'loc': url_for('public.contato', _external=True), 'priority': '0.7', 'lastmod': now},
        {'loc': url_for('public.politicas', _external=True), 'priority': '0.6', 'lastmod': now},
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        xml += f'  <url><loc>{p["loc"]}</loc><lastmod>{p["lastmod"]}</lastmod><priority>{p["priority"]}</priority></url>\n'
    for prod in produtos:
        url = url_for('public.produto_detalhe', produto_id=prod['id'], _external=True)
        xml += f'  <url><loc>{url}</loc><lastmod>{now}</lastmod><priority>0.9</priority></url>\n'
    xml += '</urlset>'
    resp = make_response(xml)
    resp.content_type = 'application/xml'
    return resp


@public_bp.route('/robots.txt')
def robots():
    return Response(
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /checkout\n"
        "Disallow: /csrf-token\n"
        "\n"
        "Sitemap: https://defumadosac.com.br/sitemap.xml\n",
        mimetype='text/plain'
    )


@public_bp.route('/llms.txt')
def llms_txt():
    content = (
        "# Defumados AC\n"
        "> Defumados artesanais de porco em Vargem Grande, Rio de Janeiro\n"
        "\n"
        "## Sobre\n"
        "Produzimos defumados, curados e embutidos artesanais desde 2015.\n"
        "Marca: Defumados Arcos Carballiño. CNPJ: 34.245.632/0001-37.\n"
        "\n"
        "## Produtos\n"
        "Linguiças, bacon, copa, costelinha, salame e mais.\n"
        "Produtos artesanais, curados e defumados com defumação natural.\n"
        "\n"
        "## Preços\n"
        "Faixa de preço: R$ 20 a R$ 80.\n"
        "Consulta atualizada no site: https://defumadosac.com.br\n"
        "\n"
        "## Contato\n"
        "WhatsApp: (21) 98635-8184\n"
        "Email: defumadosac@outlook.com\n"
        "Instagram: @defumadosac\n"
        "\n"
        "## Localização\n"
        "Vargem Grande, Rio de Janeiro - RJ\n"
        "Entrega fixa R$ 15,00: Zona Sul, Barra, Recreio, Tijuca, Centro.\n"
        "Entregamos em todo Brasil via Correios/transportadoras.\n"
    )
    resp = Response(content, mimetype='text/plain')
    return resp


@public_bp.route('/faq-teste')
def faq_teste():
    produto = get_produto(1)
    if not produto:
        produto = get_produto(2)
    if not produto:
        from flask import abort
        abort(404)
    return render_template('faq_test.html', produto=produto)
