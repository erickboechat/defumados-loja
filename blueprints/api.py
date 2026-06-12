from flask import Blueprint, request, jsonify

from models import get_produtos, get_produto, add_aviso
from extensions import limiter

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/produtos')
def api_produtos():
    return jsonify(get_produtos(todos=False))


@api_bp.route('/busca')
@limiter.limit("60 per minute")
def api_busca():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    resultados = get_produtos(todos=False, search=q)

    def _webp_smart(caminho_imagem):
        import os
        if not caminho_imagem:
            return ''
        nome_sem_ext, _ = os.path.splitext(caminho_imagem)
        caminho_webp = f"{nome_sem_ext}.webp"
        caminho_relativo = caminho_webp.replace('/static/', '', 1)
        if os.path.exists(os.path.join('static', caminho_relativo)):
            return caminho_webp
        return caminho_imagem

    return jsonify([{
        'id': p['id'],
        'nome': p['nome'],
        'preco': p['preco'],
        'imagem': _webp_smart(p['imagens'][0]) if p['imagens'] else None,
        'estoque': p['estoque'],
    } for p in resultados[:8]])


@api_bp.route('/produtos/<int:produto_id>')
def api_produto_detalhe(produto_id):
    produto = get_produto(produto_id)
    if produto:
        return jsonify(produto)
    return jsonify({'erro': 'Não encontrado'}), 404


@api_bp.route('/avisar-estoque', methods=['POST'])
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
