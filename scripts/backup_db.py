#!/usr/bin/env python3
"""
Backup do banco SQLite — versão Python (funciona no Windows também).

Uso:
    python scripts/backup_db.py

Agendar no Windows (Task Scheduler):
    python C:\defumados-loja\scripts\backup_db.py

Agendar no Linux (cron):
    0 3 * * * cd /caminho/para/defumados-loja && python scripts/backup_db.py
"""
import os
import shutil
import gzip
from datetime import datetime, timedelta

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(PROJECT_DIR, 'backups')
DB_FILE = os.path.join(PROJECT_DIR, 'loja.db')
RETENTION_DAYS = 30

os.makedirs(BACKUP_DIR, exist_ok=True)

timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
backup_name = f'loja_{timestamp}.db'
backup_path = os.path.join(BACKUP_DIR, backup_name)

shutil.copy2(DB_FILE, backup_path)

with open(backup_path, 'rb') as f_in:
    with gzip.open(f'{backup_path}.gz', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)
os.remove(backup_path)

cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
for f in os.listdir(BACKUP_DIR):
    if f.startswith('loja_') and f.endswith('.db.gz'):
        fpath = os.path.join(BACKUP_DIR, f)
        mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
        if mtime < cutoff:
            os.remove(fpath)
            print(f"Removido backup antigo: {f}")

print(f"✅ Backup criado: {backup_name}.gz")
