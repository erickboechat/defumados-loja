#!/bin/bash
# Sincroniza imagens .webp novas para o GitHub
# Roda automaticamente junto com o backup do banco (cron: 0 3 * * *)
# Pode ser executado manualmente:
#   cd /home/deploy/defumados-loja && bash scripts/sync_imagens.sh
set -e

cd "$(dirname "$0")/.."

NOVAS=$(git status --porcelain static/uploads/produtos/ 2>/dev/null | head -20)

if [ -z "$NOVAS" ]; then
    echo "Nenhuma imagem nova encontrada."
    exit 0
fi

echo "Imagens novas detectadas:"
echo "$NOVAS"

git add static/uploads/produtos/
git commit -m "feat: sincronizar imagens dos produtos [skip ci]"
git push

echo "Imagens sincronizadas com o GitHub."
