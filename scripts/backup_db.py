#!/usr/bin/env python3
"""
Backup do banco SQLite — envia uma cópia por email.

Uso:
    python scripts/backup_db.py

Agendar no Linux (cron):
    0 3 * * * cd /caminho/para/defumados-loja && python scripts/backup_db.py
"""
import os
import smtplib
import shutil
import gzip
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('backup')

BRT = timezone(timedelta(hours=-3))

PROJECT_DIR = Path(__file__).resolve().parent.parent
BACKUP_DIR = PROJECT_DIR / 'backups'
DB_FILE = PROJECT_DIR / 'loja.db'
RETENTION_DAYS = 30

BACKUP_DIR.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(BRT).strftime('%Y-%m-%d_%H-%M-%S')
backup_name = f'loja_{timestamp}.db'
backup_path = BACKUP_DIR / backup_name
backup_gz = BACKUP_DIR / f'{backup_name}.gz'

# 1. Criar backup comprimido
shutil.copy2(str(DB_FILE), str(backup_path))
with open(backup_path, 'rb') as f_in:
    with gzip.open(str(backup_gz), 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
backup_path.unlink()
logger.info('Backup criado: %s', backup_gz.name)

# 2. Remover backups antigos
cutoff = datetime.now(BRT) - timedelta(days=RETENTION_DAYS)
for f in BACKUP_DIR.iterdir():
    if f.name.startswith('loja_') and f.name.endswith('.db.gz'):
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=BRT)
        if mtime < cutoff:
            f.unlink()
            logger.info('Removido backup antigo: %s', f.name)

# 3. Enviar por email
gmail_user = os.environ.get('GMAIL_USER')
gmail_pass = os.environ.get('GMAIL_APP_PASSWORD')
alert_email = os.environ.get('ALERT_EMAIL')

if all([gmail_user, gmail_pass, alert_email]):
    try:
        msg = MIMEMultipart()
        msg['From'] = gmail_user
        msg['To'] = alert_email
        msg['Subject'] = f'Backup loja.db - {timestamp}'

        msg.attach(MIMEText(
            f'Backup automático do banco de dados.\n\n'
            f'Arquivo: {backup_gz.name}\n'
            f'Tamanho: {backup_gz.stat().st_size / 1024:.1f} KB\n'
            f'Data: {datetime.now(BRT).strftime("%d/%m/%Y %H:%M:%S")}',
            'plain', 'utf-8'
        ))

        with open(backup_gz, 'rb') as anexo:
            parte = MIMEBase('application', 'gzip')
            parte.set_payload(anexo.read())
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', f'attachment; filename="{backup_gz.name}"')
            msg.attach(parte)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        logger.info('Backup enviado por email para %s', alert_email)
    except Exception as e:
        logger.error('Falha ao enviar backup por email: %s', e)
else:
    logger.warning('Email não configurado — backup salvo apenas no servidor')

print(f'Backup concluido: {backup_gz.name}')
