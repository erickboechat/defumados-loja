# Regras do Projeto — Defumados AC

## Deploy
- Push para `main` dispara deploy automático via GitHub Actions
- Build version em `static/build.json` — atualizar sempre que houver mudança no frontend

## Frontend
- **SEMPRE rodar `npm run build`** após editar `static/admin.css` ou `static/admin.js` — sem isso, as alterações não refletem no admin (os arquivos `.min` ficam desatualizados)
- Site público usa `style.min.css` e `script.min.js` — nunca editar os `.min` diretamente

## Testes
- Rodar `python -m pytest tests/ -v` antes de commitar mudanças em Python
- Rodar `npx playwright test` quando houver mudanças significativas no admin (requer Flask rodando)

## Código
- Templates admin ficam em `templates/admin/`
- Templates público ficam em `templates/`
- CSS/JS admin em `static/admin.*`
- CSS/JS público em `static/style.*` e `static/script.*`
- Models em `models.py`, rotas em `app.py`, config em `config.py`
- Nunca commitar `.env` ou credenciais

## Estrutura de templates
- `templates/base.html` — base do site público (todos os templates públicos estendem)
- `templates/admin/admin_base.html` — base do admin (todos os templates admin estendem, exceto login)
