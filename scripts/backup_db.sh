#!/bin/bash
# Backup diário do banco SQLite
# Instale no cron: crontab -e
# Adicione: 0 3 * * * /caminho/para/scripts/backup_db.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="$PROJECT_DIR/backups"
DB_FILE="$PROJECT_DIR/loja.db"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

mkdir -p "$BACKUP_DIR"

# Backup com timestamp
cp "$DB_FILE" "$BACKUP_DIR/loja_$DATE.db"

# Compactar
gzip "$BACKUP_DIR/loja_$DATE.db"

# Remover backups com mais de 30 dias
find "$BACKUP_DIR" -name "loja_*.db.gz" -mtime +30 -delete

echo "✅ Backup criado: loja_$DATE.db.gz"
echo "📦 Total de backups: $(ls -1 "$BACKUP_DIR"/*.db.gz 2>/dev/null | wc -l)"
