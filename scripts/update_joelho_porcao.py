#!/usr/bin/env python3
"""
Atualiza as imagens do produto 'Joelho de Porco Defumado (Porção)'
para as 4 novas fotos.
"""
import sqlite3
import os
import sys

DB_PATH = os.environ.get('DATABASE_URL', 'loja.db')
if DB_PATH.startswith('sqlite:///'):
    DB_PATH = DB_PATH.replace('sqlite:///', '')

NOVAS_IMAGENS = [
    '/static/uploads/produtos/foto porção joelho de porco defumado 01.webp',
    '/static/uploads/produtos/foto porção joelho de porco defumado 02.webp',
    '/static/uploads/produtos/foto porção joelho de porco defumado 03.webp',
    '/static/uploads/produtos/foto porção joelho de porco defumado 04.webp',
]

import json

def main():
    db = sqlite3.connect(DB_PATH)
    row = db.execute(
        "SELECT id, nome, imagens FROM produtos WHERE nome LIKE '%Joelho%' AND nome LIKE '%Por%'"
    ).fetchone()

    if not row:
        print("Produto 'Joelho de Porco Defumado (Porção)' não encontrado!")
        sys.exit(1)

    prod_id, nome, imagens_old = row
    print(f"Produto encontrado: ID={prod_id}, Nome={nome}")
    print(f"Imagens antigas: {imagens_old}")

    novas_json = json.dumps(NOVAS_IMAGENS)
    db.execute("UPDATE produtos SET imagens = ? WHERE id = ?", (novas_json, prod_id))
    db.commit()
    print(f"Imagens atualizadas com sucesso! ({len(NOVAS_IMAGENS)} fotos)")

    row2 = db.execute("SELECT imagens FROM produtos WHERE id = ?", (prod_id,)).fetchone()
    print(f"Verificação: {row2[0]}")
    db.close()

if __name__ == '__main__':
    main()
