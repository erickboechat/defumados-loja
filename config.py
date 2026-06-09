import os
from werkzeug.security import generate_password_hash


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            'SECRET_KEY não definida. '
            'Crie um arquivo .env na raiz do projeto com SECRET_KEY=sua-chave-secreta '
            'ou veja .env.example para referência.'
        )
    ADMIN_USER = os.environ.get('ADMIN_USER', 'admin')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'mudarme123')
    ADMIN_PASS_HASH = generate_password_hash(ADMIN_PASSWORD)
    DATABASE = 'loja.db'
    DEBUG = os.environ.get('FLASK_DEBUG', '0') == '1'


WHATSAPP_NUMBER = os.environ.get('WHATSAPP_NUMBER', '5521986358184')
WHATSAPP_URL = f'https://api.whatsapp.com/send?phone={WHATSAPP_NUMBER}'
