import json
import logging

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_wtf.csrf import CSRFProtect

from utils import build_whatsapp_msg_checkout, build_whatsapp_msg_finalizar, whatsapp_url
from models import add_pedido
from extensions import csrf, limiter

log = logging.getLogger(__name__)

checkout_bp = Blueprint('checkout', __name__)


@checkout_bp.route('/checkout')
def checkout():
    return render_template('checkout.html')


@checkout_bp.route('/finalizar', methods=['POST'])
@csrf.exempt
@limiter.limit("10 per minute")
def finalizar():
    dados = request.json
    itens = dados.get('itens', [])
    nome = dados.get('nome', 'Não informado')
    telefone = dados.get('telefone', 'Não informado')
    endereco = dados.get('endereco', 'Não informado')
    cep = dados.get('cep', 'Não informado')
    frete_metodo = dados.get('frete_metodo', 'Não selecionado')
    frete_valor = float(dados.get('frete_valor', 0) or 0)
    total = float(dados.get('total', 0) or 0)

    msg = build_whatsapp_msg_finalizar(itens, nome, telefone, cep, endereco,
                                       frete_metodo, frete_valor, total)
    url = whatsapp_url(msg)
    return jsonify({'redirect': url})


@checkout_bp.route('/checkout/process', methods=['POST'])
@csrf.exempt
@limiter.limit("10 per minute")
def process_checkout():
    consentimento = request.form.get('lgpd_consent')
    if consentimento != '1':
        flash('É necessário aceitar a Política de Privacidade para finalizar o pedido.', 'error')
        return redirect(url_for('checkout.checkout'))

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
        return redirect(url_for('checkout.checkout'))

    total = sum(item['preco'] * item['qtd'] for item in itens)
    pedido_id = add_pedido(nome, telefone, endereco, numero, complemento,
                           bairro, cidade, estado, referencia, email,
                           cep, forma_entrega, itens_json, total,
                           frete_valor, frete_texto)

    log.info(f"Pedido #{pedido_id} registrado por {nome} ({telefone})")

    msg = build_whatsapp_msg_checkout(pedido_id, nome, telefone, email, cep,
                                      endereco, numero, complemento, bairro,
                                      cidade, estado, referencia, forma_entrega,
                                      itens, total, frete_valor, frete_texto)
    wa_link = whatsapp_url(msg)
    return redirect(wa_link)
