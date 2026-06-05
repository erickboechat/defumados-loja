# 🚀 Guia de Deploy — Defumados AC

Guia completo para colocar o site **defumadosac.com.br** no ar, do zero.

---

## Índice

1. [Escolher e contratar um servidor](#1-escolher-e-contratar-um-servidor)
2. [Acessar o servidor pela primeira vez](#2-acessar-o-servidor-pela-primeira-vez)
3. [Configurar o DNS do domínio](#3-configurar-o-dns-do-domínio)
4. [Rodar o script de setup automático](#4-rodar-o-script-de-setup-automático)
5. [Configurar as variáveis de ambiente](#5-configurar-as-variáveis-de-ambiente)
6. [Configurar HTTPS (SSL) com Certbot](#6-configurar-https-ssl-com-certbot)
7. [Configurar o serviço do sistema](#7-configurar-o-serviço-do-sistema)
8. [Testar se está tudo funcionando](#8-testar-se-está-tudo-funcionando)
9. [Configurar backup automático](#9-configurar-backup-automático)
10. [Atualizar o site após mudanças](#10-atualizar-o-site-após-mudanças)
11. [Solução de problemas comuns](#11-solução-de-problemas-comuns)

---

## 1. Escolher e contratar um servidor

### Requisitos mínimos
- **SO:** Ubuntu 22.04 LTS
- **RAM:** 1 GB
- **Disco:** 10 GB SSD
- **CPU:** 1 vCPU

### Provedores recomendados
| Provedor | Preço mínimo | Link |
|----------|-------------|------|
| **Hetzner** | ~€4/mês | https://www.hetzner.com/cloud |
| **DigitalOcean** | ~$6/mês | https://www.digitalocean.com |
| **Vultr** | ~$6/mês | https://www.vulrt.com |
| **Contabo** | ~€6/mês | https://contabo.com |
| **KingHost** | ~R$50/mês | https://www.kinghost.net/vps |

### Passo a passo (exemplo com Hetzner)
1. Crie uma conta em https://www.hetzner.com/cloud
2. Clique em **"NEW SERVER"**
3. Escolha:
   - **Location:** Nuremberg ou Falkenstein
   - **Image:** Ubuntu 22.04
   - **Type:** CX22 (2 vCPU, 4 GB RAM) — o mínimo recomendado
   - **Firewall:** crie um novo com regras para **SSH (22)**, **HTTP (80)**, **HTTPS (443)**
   - **SSH Key:** adicione sua chave pública (se não souber o que é, use senha)
4. Anote o **IP do servidor** que aparecerá na tela

> 💡 **Alternativa mais barata:** CX11 (1 vCPU, 2 GB RAM) por ~€4/mês

---

## 2. Acessar o servidor pela primeira vez

### Windows — usando PowerShell
Abra o PowerShell e digite:
```powershell
ssh root@SEU_IP
```
Substitua `SEU_IP` pelo IP do servidor.
- Se pedir senha, digite a senha que você definiu na criação
- Na primeira vez, vai aparecer um aviso de fingerprint — digite `yes` e Enter

### Mac / Linux — usando Terminal
```bash
ssh root@SEU_IP
```

### Após conectar
Você verá algo como `root@seu-servidor:~#`. Pronto, você está dentro do servidor.

---

## 3. Configurar o DNS do domínio

Você precisa apontar o domínio **defumadosac.com.br** para o IP do seu servidor.

### Onde fazer
- Se você comprou o domínio no **Registro.br**: acesse https://registro.br e configure os DNS
- Se você comprou na **GoDaddy**, **HostGator**, etc.: acesse o painel de DNS do provedor
- Se você usa **Cloudflare**: configure os DNS lá

### O que configurar
Crie dois registros **A** (tipo A):

| Nome | Tipo | Valor (IP do servidor) | TTL |
|------|------|----------------------|-----|
| `@` | A | `SEU_IP_AQUI` | 300 (5 min) |
| `www` | A | `SEU_IP_AQUI` | 300 (5 min) |

> ⏱ A propagação do DNS pode levar de 5 minutos a 24 horas.

---

## 4. Rodar o script de setup automático

### 4.1. Primeiro, você precisa colocar os arquivos do site no servidor

#### Opção A: Git (recomendado)
1. Crie um repositório no GitHub (https://github.com/new) — pode ser privado
2. No seu computador local, faça o primeiro commit e push:
   ```powershell
   cd C:\defumados-loja
   git init
   git add .
   git commit -m "Primeiro commit"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/defumados-loja.git
   git push -u origin main
   ```
3. Anote a URL do repositório: `https://github.com/SEU_USUARIO/defumados-loja.git`

#### Opção B: Transferência manual (SCP)
No seu computador local, abra PowerShell e execute:
```powershell
scp -r C:\defumados-loja root@SEU_IP:/root/defumados-loja
```

### 4.2. Execute o script de setup

> **IMPORTANTE:** Antes de executar, edite o script para colocar seu usuário do GitHub na variável `REPO_URL`.

No servidor (via SSH):
```bash
# Editar o script com seu repositório
nano /root/defumados-loja/scripts/setup_ubuntu.sh
```
Mude a linha `REPO_URL="https://github.com/SEU_USUARIO/defumados-loja.git"` para seu repositório.

```bash
# Dar permissão de execução
chmod +x /root/defumados-loja/scripts/setup_ubuntu.sh

# Executar
cd /root/defumados-loja/scripts
./setup_ubuntu.sh
```

O script vai:
1. Atualizar o sistema
2. Instalar Python, Nginx, Git, Certbot
3. Criar o usuário `deploy`
4. Clonar/instalar o projeto
5. Criar o ambiente virtual Python
6. Instalar dependências
7. Copiar o `.env.example` para `.env`
8. Configurar o Nginx

Se o script falhar no meio (por exemplo, se o git clone falhar porque você não configurou o repositório), corrija o problema e execute de novo.

---

## 5. Configurar as variáveis de ambiente

Este é o passo **MAIS IMPORTANTE**. O arquivo `.env` contém senhas e chaves secretas.

> ⚠️ **NUNCA** compartilhe o `.env` ou comite ele no git.

### 5.1. Editar o .env

No servidor:
```bash
sudo nano /home/deploy/defumados-loja/.env
```

O arquivo deve ficar assim (preencha com seus valores):

```ini
# Flask
FLASK_DEBUG=0
SECRET_KEY=UmaChaveMuitoSeguraCom64CaracteresAleatorios1234567890!!!

# Admin
ADMIN_USER=admin
ADMIN_PASSWORD=SuaSenhaForteDeAdmin123

# WhatsApp
WHATSAPP_NUMBER=5521986358184

# Produção (não mexa se não souber o que está fazendo)
SESSION_COOKIE_SECURE=1
RATE_LIMIT_STORAGE=memory://
```

### 5.2. Gerar uma SECRET_KEY segura

Para gerar uma chave realmente segura, execute no servidor:

```bash
cd /home/deploy/defumados-loja
source venv/bin/activate
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copie o resultado e cole no lugar de `SECRET_KEY` no `.env`.

### 5.3. Salvar e sair

No **nano**:
1. `Ctrl+O` (salvar)
2. `Enter` (confirmar)
3. `Ctrl+X` (sair)

---

## 6. Configurar HTTPS (SSL) com Certbot

### 6.1. Antes de começar
Certifique-se de que o DNS já propagou:
```bash
ping defumadosac.com.br
```
O resultado deve mostrar o IP do seu servidor. Se não mostrar, aguarde e tente mais tarde (pode levar horas).

### 6.2. Executar Certbot
```bash
sudo certbot --nginx -d defumadosac.com.br -d www.defumadosac.com.br
```

O Certbot vai:
1. Validar que você é o dono do domínio
2. Gerar os certificados SSL
3. Modificar automaticamente o Nginx para usar HTTPS
4. Configurar renovação automática

Siga as instruções na tela:
- Informe um email (para alertas de expiração)
- Escolha a opção de redirecionar HTTP para HTTPS (opção 2)

### 6.3. Verificar renovação automática
```bash
sudo certbot renew --dry-run
```
Se mostrar "Congratulations", a renovação automática está funcionando.

---

## 7. Configurar o serviço do sistema

O serviço garante que o site:
- Inicie automaticamente quando o servidor ligar
- Reinicie automaticamente se cair

### 7.1. Copiar o arquivo de serviço
```bash
sudo cp /home/deploy/defumados-loja/scripts/defumadosac.service /etc/systemd/system/
```

### 7.2. Ativar e iniciar o serviço
```bash
sudo systemctl daemon-reload
sudo systemctl enable defumadosac
sudo systemctl start defumadosac
```

### 7.3. Verificar se está rodando
```bash
sudo systemctl status defumadosac
```
Você deve ver:
```
● defumadosac.service - Defumados AC - Loja Virtual
     Loaded: loaded (/etc/systemd/system/defumadosac.service; enabled; vendor preset: enabled)
     Active: active (running) since ...
```

Se não estiver `active (running)`, veja os logs:
```bash
sudo journalctl -u defumadosac -n 50
```

---

## 8. Testar se está tudo funcionando

### No navegador
1. Acesse `https://defumadosac.com.br` — deve mostrar a loja
2. Acesse `https://defumadosac.com.br/admin` — deve mostrar o login
3. Teste um checkout completo (adicione um produto, vá ao carrinho, finalize)
4. Acesse `https://defumadosac.com.br/meus-pedidos` e consulte

### Testar o serviço
```bash
# Ver logs em tempo real
sudo journalctl -u defumadosac -f

# Ver últimas linhas do log da aplicação
tail -n 50 /home/deploy/defumados-loja/app.log
```

### Testar páginas de erro
- `https://defumadosac.com.br/pagina-inexistente` — deve mostrar página 404 personalizada

---

## 9. Configurar backup automático

### 9.1. Instalar o backup no cron

```bash
# Editar o crontab do usuário deploy
sudo -u deploy crontab -e
```

Na primeira vez, escolha o editor **nano** (opção 1).

Adicione esta linha ao final:
```cron
0 3 * * * cd /home/deploy/defumados-loja && python scripts/backup_db.py
```

Isso executa o backup todos os dias às 3h da manhã.

### 9.2. Verificar se o backup funciona
```bash
cd /home/deploy/defumados-loja
python scripts/backup_db.py
```

Verifique se o arquivo foi criado:
```bash
ls -la backups/
```
Você deve ver um arquivo como `loja_2026-06-05_03-00-00.db.gz`.

### 9.3. Como restaurar um backup (emergência)
```bash
# Descomprimir
gunzip backups/loja_DATA.db.gz

# Parar o serviço
sudo systemctl stop defumadosac

# Substituir o banco
cp backups/loja_DATA.db loja.db

# Iniciar novamente
sudo systemctl start defumadosac
```

> 💡 **Dica:** Periodicamente, baixe uma cópia do backup para seu computador como segurança extra.

---

## 10. Atualizar o site após mudanças

Quando você fizer alterações no código localmente e quiser enviar para produção:

### 10.1. Se usou Git (recomendado)
No seu computador:
```bash
cd C:\defumados-loja
git add .
git commit -m "Descrição das alterações"
git push
```

No servidor (SSH):
```bash
cd /home/deploy/defumados-loja
git pull
sudo systemctl restart defumadosac
```

### 10.2. Se transferiu manualmente
No seu computador:
```powershell
scp -r C:\defumados-loja root@SEU_IP:/home/deploy/defumados-loja
```

No servidor:
```bash
sudo systemctl restart defumadosac
```

---

## 11. Solução de problemas comuns

### Site não carrega
```bash
# Verificar se o serviço está rodando
sudo systemctl status defumadosac

# Verificar logs
sudo journalctl -u defumadosac -n 50 --no-pager
cat /home/deploy/defumados-loja/app.log | tail -50

# Verificar Nginx
sudo nginx -t
sudo systemctl status nginx
```

### Erro 502 Bad Gateway
O Flask não está respondendo. Provavelmente o serviço caiu:
```bash
sudo systemctl restart defumadosac
```

### Erro de permissão negada
```bash
# Corrigir permissões
sudo chown -R deploy:deploy /home/deploy/defumados-loja
chmod -R 755 /home/deploy/defumados-loja/static
chmod -R 755 /home/deploy/defumados-loja/public
```

### CSRF token inválido
- O cookie de sessão expirou (vigência: 2 horas)
- Recarregue a página e tente novamente

### Não consigo fazer login no admin
```bash
# Verifique o .env
cat /home/deploy/defumados-loja/.env | grep ADMIN
```

### Quero ver os pedidos no banco
```bash
cd /home/deploy/defumados-loja
source venv/bin/activate
python3 -c "
import sqlite3
conn = sqlite3.connect('loja.db')
cur = conn.execute('SELECT id, nome, cliente_telefone, data_criacao, total, status FROM pedidos ORDER BY id DESC')
for row in cur.fetchall():
    print(f'#{row[0]} | {row[1]} | {row[2]} | {row[3]} | R${row[4]:.2f} | {row[5]}')
"
```

---

## Comandos rápidos de manutenção

| Ação | Comando |
|------|---------|
| Reiniciar o site | `sudo systemctl restart defumadosac` |
| Parar o site | `sudo systemctl stop defumadosac` |
| Ver status | `sudo systemctl status defumadosac` |
| Ver logs em tempo real | `sudo journalctl -u defumadosac -f` |
| Ver logs do Nginx | `sudo tail -f /var/log/nginx/access.log` |
| Renovar SSL manualmente | `sudo certbot renew` |
| Fazer backup manual | `cd /home/deploy/defumados-loja && python scripts/backup_db.py` |
| Atualizar código (git) | `cd /home/deploy/defumados-loja && git pull && sudo systemctl restart defumadosac` |

---

## Arquitetura final

```
Internet
    │
    ▼
  [DNS: defumadosac.com.br → IP do servidor]
    │
    ▼
  [Nginx (porta 443 HTTPS)]
    │
    ├── /static/  →  arquivos estáticos (diretamente do disco)
    ├── /uploads/ →  imagens (diretamente do disco)
    └── /*        →  proxy reverso
                        │
                        ▼
                    [Waitress (porta 5000)]
                        │
                        ▼
                    [Flask (app.py)]
                        │
                        ▼
                    [SQLite (loja.db)]
```

---

> **Precisa de ajuda?** Abra uma issue em https://github.com/anomalyco/opencode/issues ou contrate um profissional de DevOps.
