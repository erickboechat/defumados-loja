#!/bin/bash
# ============================================================
# Script de configuração inicial do servidor Ubuntu
# Execute como root (ou com sudo) em uma VPS Ubuntu 22.04+
# ============================================================
set -euo pipefail

echo "========================================"
echo "  Configuração inicial — Defumados AC"
echo "========================================"

# ---------------------------
# 1. Variáveis (EDITAR!)
# ---------------------------
DOMAIN="defumadosac.com.br"
DEPLOY_USER="deploy"
DEPLOY_DIR="/home/${DEPLOY_USER}/defumados-loja"
REPO_URL="https://github.com/SEU_USUARIO/defumados-loja.git"

echo ""
echo "Passo 1/8 — Atualizando o sistema..."
apt update && apt upgrade -y

echo ""
echo "Passo 2/8 — Instalando dependências do sistema..."
apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx git curl

echo ""
echo "Passo 3/8 — Criando usuário deploy..."
if id "${DEPLOY_USER}" &>/dev/null; then
    echo "Usuário ${DEPLOY_USER} já existe."
else
    adduser --disabled-password --gecos "" "${DEPLOY_USER}"
    echo "Usuário ${DEPLOY_USER} criado."
fi

echo ""
echo "Passo 4/8 — Clonando o repositório..."
if [ -d "${DEPLOY_DIR}" ]; then
    echo "Diretório já existe. Pulando clone."
else
    mkdir -p "$(dirname "${DEPLOY_DIR}")"
    git clone "${REPO_URL}" "${DEPLOY_DIR}"
fi

echo ""
echo "Passo 5/8 — Criando ambiente virtual e instalando dependências Python..."
cd "${DEPLOY_DIR}"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Passo 6/8 — Criando arquivo .env..."
if [ -f ".env" ]; then
    echo ".env já existe. Mantendo atual."
else
    cp .env.example .env
    echo ""
    echo "⚠️  ATENÇÃO: Edite o .env com suas configurações!"
    echo "   nano ${DEPLOY_DIR}/.env"
    echo ""
    echo "   Gere uma SECRET_KEY segura: python3 -c \"import secrets; print(secrets.token_hex(32))\""
fi

echo ""
echo "Passo 7/8 — Configurando permissões..."
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_DIR}"
chmod 755 "${DEPLOY_DIR}"
mkdir -p "${DEPLOY_DIR}/backups"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${DEPLOY_DIR}/backups"

echo ""
echo "Passo 8/8 — Configurando Nginx..."
cp "${DEPLOY_DIR}/scripts/nginx_defumadosac.conf" /etc/nginx/sites-available/${DOMAIN}
if [ -f "/etc/nginx/sites-enabled/default" ]; then
    rm /etc/nginx/sites-enabled/default
fi
ln -sf /etc/nginx/sites-available/${DOMAIN} /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

echo ""
echo "========================================"
echo "  Configuração inicial CONCLUÍDA!"
echo "========================================"
echo ""
echo "PRÓXIMOS PASSOS:"
echo "  1. Edite o .env:  nano ${DEPLOY_DIR}/.env"
echo "  2. Configure o SSL:  sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
echo "  3. Instale o serviço:"
echo "       sudo cp ${DEPLOY_DIR}/scripts/defumadosac.service /etc/systemd/system/"
echo "       sudo systemctl daemon-reload"
echo "       sudo systemctl enable defumadosac"
echo "       sudo systemctl start defumadosac"
echo "       sudo systemctl status defumadosac"
echo ""
echo "  4. Configure o backup e monitor (cron):"
echo "       sudo -u ${DEPLOY_USER} crontab -e"
echo "       Adicione:"
echo "         0 3 * * * cd ${DEPLOY_DIR} && ${DEPLOY_DIR}/venv/bin/python scripts/backup_db.py"
echo "         */5 * * * * cd ${DEPLOY_DIR} && ${DEPLOY_DIR}/venv/bin/python scripts/monitor.py >> ${DEPLOY_DIR}/logs/monitor.log 2>&1"
echo "       Depois crie a pasta de logs:"
echo "       mkdir -p ${DEPLOY_DIR}/logs"
echo "       chown ${DEPLOY_USER}:${DEPLOY_USER} ${DEPLOY_DIR}/logs"
echo ""
