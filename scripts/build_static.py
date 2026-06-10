#!/usr/bin/env python3
"""
Gera versões minificadas de style.css e script.js.
Uso: python scripts/build_static.py
"""
import os
import sys
from pathlib import Path

static_dir = Path(__file__).resolve().parent.parent / 'static'


def minify_css(content):
    """Minifica CSS básico (remove comentários, espaços extras)"""
    import re
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{}:;,])\s*', r'\1', content)
    content = re.sub(r';}', r'}', content)
    return content.strip()


def minify_js(content):
    """Minifica JS básico (remove comentários, espaços extras)"""
    import re

    # Protege template literals (backtick) contra regex destrutivo
    templates = []
    def save_template(m):
        idx = len(templates)
        templates.append(m.group(0))
        return f'\x00T{idx}\x00'

    content = re.sub(r'`[^`]*`', save_template, content)

    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'\s+', ' ', content)
    content = re.sub(r'\s*([{}();,:=+\-*/!<>])\s*', r'\1', content)

    # Restaura template literals
    for i, t in enumerate(templates):
        content = content.replace(f'\x00T{i}\x00', t)

    return content.strip()


def main():
    import json
    from datetime import datetime

    files = [
        ('style.css', 'style.min.css', minify_css),
        ('script.js', 'script.min.js', minify_js),
    ]

    for src_name, dst_name, minifier in files:
        src = static_dir / src_name
        dst = static_dir / dst_name

        if not src.exists():
            print(f'[SKIP] {src_name} não encontrado')
            continue

        original = src.read_text(encoding='utf-8')
        minified = minifier(original)
        dst.write_text(minified, encoding='utf-8')

        original_kb = len(original) / 1024
        minified_kb = len(minified) / 1024
        saved = (1 - len(minified) / len(original)) * 100
        print(f'[OK] {src_name} -> {dst_name}')
        print(f'     {original_kb:.1f}KB -> {minified_kb:.1f}KB ({saved:.0f}% economia)')

    # Gera build.json com timestamp para cache busting
    version = datetime.now().strftime('%Y%m%d%H%M%S')
    (static_dir / 'build.json').write_text(
        json.dumps({'version': version}), encoding='utf-8'
    )
    print(f'[OK] build.json -> v{version}')
    print('Build concluído.')


if __name__ == '__main__':
    main()
