#!/usr/bin/env python3
"""
Ponto de entrada para produção — usa Waitress.

Uso:
    python run_production.py

Para testar localmente com HTTP (desenvolvimento):
    SESSION_COOKIE_SECURE=0 python run_production.py
"""
import os
from dotenv import load_dotenv

load_dotenv()

from waitress import serve
from app import app

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))

    print(f"Servidor iniciado em http://{host}:{port}")
    print("Recomendado: rodar atrás de Nginx com SSL.")

    serve(
        app,
        host=host,
        port=port,
        threads=4,
        url_scheme='https',
    )
