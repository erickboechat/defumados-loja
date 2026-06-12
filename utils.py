from datetime import timezone, timedelta
from urllib.parse import quote

BRT = timezone(timedelta(hours=-3))


def parse_preco(preco_str):
    """Converte string de preço (com vírgula ou ponto) para float. Retorna 0.0 em caso de erro."""
    try:
        return float(preco_str.replace(',', '.'))
    except (ValueError, TypeError, AttributeError):
        return 0.0


def build_whatsapp_msg_checkout(pedido_id, nome, telefone, email, cep,
                                 endereco, numero, complemento, bairro,
                                 cidade, estado, referencia, forma_entrega,
                                 itens, total, frete_valor, frete_texto):
    """Monta mensagem WhatsApp para o pedido do formulário de checkout."""
    endereco_completo = f"{endereco}, {numero}" + (f" - {complemento}" if complemento else "")
    msg = f"*NOVO PEDIDO #{pedido_id} - DEFUMADOS AC*\n\n"
    msg += f"DADOS DO CLIENTE:\n"
    msg += f"Nome: {nome}\n"
    msg += f"Telefone: {telefone}\n"
    if email:
        msg += f"E-mail: {email}\n"
    msg += f"\nENDERECO DE ENTREGA:\n"
    msg += f"CEP: {cep}\n"
    msg += f"{endereco_completo}\n"
    msg += f"Bairro: {bairro}\n"
    msg += f"Cidade: {cidade}/{estado}\n"
    if referencia:
        msg += f"Referencia: {referencia}\n"
    msg += f"\nENTREGA:\n"
    msg += f"Tipo: {forma_entrega}\n"
    msg += f"Frete: {frete_texto}\n\n"
    msg += f"PRODUTOS:\n"
    for item in itens:
        msg += f"  {item['qtd']}x {item['nome']}\n"
        msg += f"   R$ {(item['preco']*item['qtd']):.2f}\n"
    msg += f"\nTOTAL DO PEDIDO:\n"
    msg += f"Subtotal: R$ {total:.2f}\n"
    if frete_valor > 0:
        msg += f"Frete: R$ {frete_valor:.2f}\n"
        msg += f"TOTAL: R$ {(total + frete_valor):.2f}\n"
    else:
        msg += f"Frete: A combinar\n"
        msg += f"TOTAL: R$ {total:.2f} (sem frete)\n"
    msg += f"\nObrigado pela preferencia!\n"
    msg += f"Aguarde a confirmacao do pedido.\n"
    msg += f"Pedido #{pedido_id} gerado automaticamente pelo site"
    return msg


def build_whatsapp_msg_finalizar(itens, nome, telefone, cep, endereco,
                                  frete_metodo, frete_valor, total):
    """Monta mensagem WhatsApp para o checkout via JSON (finalizar)."""
    itens_formatados = '\n'.join([
        f"  {i['nome']} x{i['qtd']} = R$ {i['preco']*i['qtd']:.2f}"
        for i in itens
    ])

    if frete_valor > 0:
        linha_frete = f"Frete: R$ {frete_valor:.2f} (Tarifa fixa RJ)"
        linha_total = f"TOTAL: R$ {total:.2f}"
    else:
        linha_frete = "Frete: Sob consulta (Correios/Transportadora)"
        linha_total = f"TOTAL: R$ {total:.2f} + frete a combinar"

    msg = f"""NOVO PEDIDO - DEFUMADOS AC

Cliente: {nome}
Contato: {telefone}
CEP: {cep}
Endereco: {endereco}
Entrega: {frete_metodo}

Itens:
{itens_formatados}

{linha_frete}
{linha_total}

Obrigado pela preferencia! Aguarde a confirmacao do pedido."""
    return msg


def whatsapp_url(msg):
    """Retorna URL do WhatsApp com a mensagem codificada."""
    from config import WHATSAPP_URL
    return f"{WHATSAPP_URL}&text={quote(msg, safe='', encoding='utf-8')}"
