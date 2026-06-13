import os
import json
import csv
import io
import logging
from datetime import datetime, timedelta

from flask import (Blueprint, render_template, request, jsonify,
                   redirect, url_for, session, flash, Response)
from werkzeug.security import check_password_hash

from config import Config, WHATSAPP_URL
from utils import BRT, parse_preco
from models import (get_produtos_paginados, count_produtos, get_produto,
                    add_produto, edit_produto, toggle_visivel, toggle_estoque,
                    deletar_produto, get_pedido, get_pedidos_paginados,
                    get_pedidos_filtrados, update_pedido_status, delete_pedido,
                    count_avisos_pendentes, get_avisos_pendentes,
                    marcar_notificados, processar_imagens_request,
                    buscar_global, get_admin_logs, count_pedidos_hoje,
                    count_pedidos_periodo, count_pedidos_pendentes,
                    login_required)
from extensions import limiter

log = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin.admin_dashboard'))

    if request.method == 'POST':
        user = request.form.get('username')
        password = request.form.get('password')
        if (user == Config.ADMIN_USER and
                check_password_hash(Config.ADMIN_PASS_HASH, password)):
            session['admin_logged_in'] = True
            session.permanent = True
            log.info(f"Admin login bem-sucedido: {user}")
            return redirect(url_for('admin.admin_dashboard'))
        log.warning(f"Tentativa de login inválida para usuário: {user}")
        return render_template('admin/login.html', erro='Usuário ou senha inválidos')

    return render_template('admin/login.html', erro=None)


@admin_bp.route('/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('public.index'))


@admin_bp.route('/')
@login_required
def admin_dashboard():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    produtos, total_paginas = get_produtos_paginados(page=page, per_page=15, todos=True, search=q)
    avisos_count = {p['id']: count_avisos_pendentes(p['id']) for p in produtos}
    total_produtos = count_produtos(todos=True, search=q)
    visiveis = count_produtos(todos=False, search=q)
    pedidos_hoje_qtd, pedidos_hoje_total = count_pedidos_hoje()

    agora = datetime.now(BRT)
    hoje_str = agora.strftime('%Y-%m-%d')
    mes_inicio = agora.replace(day=1).strftime('%Y-%m-%d')
    semana_inicio = (agora - timedelta(days=6)).strftime('%Y-%m-%d')
    dias30_inicio = (agora - timedelta(days=29)).strftime('%Y-%m-%d')

    pedidos_mes_qtd, pedidos_mes_total = count_pedidos_periodo(mes_inicio, hoje_str)
    pedidos_semana_qtd, pedidos_semana_total = count_pedidos_periodo(semana_inicio, hoje_str)
    pedidos_30d_qtd, pedidos_30d_total = count_pedidos_periodo(dias30_inicio, hoje_str)
    pedidos_pendentes = count_pedidos_pendentes()

    ticket_medio = pedidos_mes_total / pedidos_mes_qtd if pedidos_mes_qtd > 0 else 0

    return render_template('admin/dashboard.html',
                           produtos=produtos,
                           page=page,
                           total_paginas=total_paginas,
                           avisos_count=avisos_count,
                           q=q,
                           stats={
                               'total_produtos': total_produtos,
                               'visiveis': visiveis,
                               'pedidos_hoje': pedidos_hoje_qtd,
                               'faturamento_hoje': pedidos_hoje_total,
                               'faturamento_mes': pedidos_mes_total,
                               'pedidos_mes': pedidos_mes_qtd,
                               'ticket_medio': ticket_medio,
                               'faturamento_7d': pedidos_semana_total,
                               'faturamento_30d': pedidos_30d_total,
                               'pedidos_pendentes': pedidos_pendentes,
                           })


@admin_bp.route('/add', methods=['POST'])
@login_required
def admin_add_produto():
    preco = parse_preco(request.form.get('preco', '0'))
    if preco <= 0:
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
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/edit/<int:produto_id>', methods=['POST'])
@login_required
def admin_edit_produto(produto_id):
    preco = parse_preco(request.form.get('preco', '0'))
    if preco <= 0:
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
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/visivel/<int:produto_id>', methods=['POST'])
@login_required
def admin_toggle_visivel(produto_id):
    toggle_visivel(produto_id)
    log.info(f"Produto #{produto_id} visível alternado")
    flash('Visibilidade do produto alterada!', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/toggle/<int:produto_id>', methods=['POST'])
@login_required
def admin_toggle_estoque(produto_id):
    toggle_estoque(produto_id)
    log.info(f"Produto #{produto_id} estoque alternado")
    flash('Estoque do produto alterado!', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/deletar/<int:produto_id>', methods=['POST'])
@login_required
def admin_deletar_produto(produto_id):
    deletar_produto(produto_id)
    log.info(f"Produto #{produto_id} deletado")
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/notificar/<int:produto_id>', methods=['GET'])
@login_required
def admin_notificar(produto_id):
    produto = get_produto(produto_id)
    if not produto:
        return render_template('404.html', mensagem='Produto não encontrado'), 404

    avisos = list(get_avisos_pendentes(produto_id))
    ativado = request.args.get('ativado') == '1'

    return render_template('admin/notificar.html',
                           produto=produto, avisos=avisos,
                           whatsapp_url=WHATSAPP_URL, ativado=ativado)


@admin_bp.route('/notificar/<int:produto_id>/ativar', methods=['POST'])
@login_required
def admin_ativar_estoque(produto_id):
    produto = get_produto(produto_id)
    if not produto:
        return render_template('404.html', mensagem='Produto não encontrado'), 404

    avisos = list(get_avisos_pendentes(produto_id))
    marcar_notificados(produto_id)

    if not produto['estoque']:
        toggle_estoque(produto_id)

    return redirect(url_for('admin.admin_notificar', produto_id=produto_id, ativado='1'))


# ===== PEDIDOS =====

@admin_bp.route('/pedidos')
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


@admin_bp.route('/pedidos/<int:pedido_id>')
@login_required
def admin_pedido_detalhe(pedido_id):
    pedido = get_pedido(pedido_id)
    if not pedido:
        return render_template('404.html', mensagem='Pedido não encontrado'), 404
    return render_template('admin/pedido_detalhe.html', pedido=pedido)


@admin_bp.route('/pedidos/<int:pedido_id>/status', methods=['POST'])
@login_required
def admin_update_pedido_status(pedido_id):
    novo_status = request.form.get('status')
    update_pedido_status(pedido_id, novo_status)
    flash('Status do pedido atualizado!', 'success')
    return redirect(url_for('admin.admin_pedido_detalhe', pedido_id=pedido_id))


@admin_bp.route('/pedidos/<int:pedido_id>/delete', methods=['POST'])
@login_required
def admin_delete_pedido(pedido_id):
    delete_pedido(pedido_id)
    log.info(f"Pedido #{pedido_id} deletado")
    flash('Pedido excluído com sucesso!', 'success')
    return redirect(url_for('admin.admin_pedidos'))


@admin_bp.route('/pedidos/bulk', methods=['POST'])
@login_required
def admin_pedidos_bulk():
    pedido_ids = request.form.getlist('pedido_ids')
    action = request.form.get('action')

    if not pedido_ids or not action:
        flash('Nenhum pedido selecionado.', 'error')
        return redirect(url_for('admin.admin_pedidos'))

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

    return redirect(url_for('admin.admin_pedidos'))


@admin_bp.route('/api/search')
@login_required
def admin_api_search():
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 10, type=int)
    results = buscar_global(search=q, limit=min(limit, 20))

    return jsonify({
        'produtos': [{
            'id': p['id'],
            'nome': p['nome'],
            'preco': p['preco'],
            'estoque': p['estoque'],
            'visivel': p['visivel'],
            'thumb': p['thumb'],
            'url': f'/admin/edit/{p["id"]}'
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


@admin_bp.route('/logs')
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


@admin_bp.route('/pedidos/export')
@login_required
def admin_pedidos_export():
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()
    pedidos = get_pedidos_filtrados(search=q, status=status)

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')

    writer.writerow([
        'ID', 'Cliente', 'Telefone', 'Email', 'CEP',
        'Endereço', 'Número', 'Complemento', 'Bairro', 'Cidade', 'Estado', 'Referência',
        'Forma Entrega', 'Frete Valor', 'Frete Texto',
        'Itens', 'Total', 'Status', 'Data Criação'
    ])

    for p in pedidos:
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
