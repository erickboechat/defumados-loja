#!/usr/bin/env python3
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

from dotenv import load_dotenv

# Garante que a pasta raiz do projeto está no path para importar notifier
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)

STATE_FILE = Path('/tmp/defumadosac_monitor_state.json')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('monitor')


def check_site(url, timeout=15):
    req = Request(url, method='HEAD')
    try:
        resp = urlopen(req, timeout=timeout)
        return resp.status == 200
    except Exception as e:
        logger.warning('Check failed: %s', e)
        return False


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def main():
    site_url = os.environ.get('MONITOR_URL', 'https://defumadosac.com.br/health')
    state = load_state()
    last_state = state.get('last_state', 'unknown')
    last_alert = state.get('last_alert_at', 0)
    cooldown = 300

    is_up = check_site(site_url)

    if not is_up:
        time.sleep(15)
        is_up = check_site(site_url)

    now = time.time()
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if not is_up and last_state != 'down':
        from scripts.notifier import notify_all
        subject = f'[ALERTA] defumadosac.com.br FORA DO AR'
        body = (
            f'O site defumadosac.com.br está FORA DO AR!\n\n'
            f'Data/Hora: {now_str}\n'
            f'URL: {site_url}\n\n'
            f'Acesse o servidor via SSH para investigar:\n'
            f'ssh deploy@IP_DO_SERVIDOR\n'
            f'systemctl status defumadosac\n'
        )
        notify_all(subject, body)
        state['last_state'] = 'down'
        state['last_alert_at'] = now
        state['down_since'] = now
        save_state(state)
        logger.warning('SITE DOWN — alert sent')

    elif is_up and last_state == 'down':
        from scripts.notifier import notify_all
        subject = f'[RECUPERADO] defumadosac.com.br voltou ao ar'
        down_since = state.get('down_since', now)
        downtime = int((now - down_since) / 60)
        body = (
            f'O site defumadosac.com.br está ONLINE novamente!\n\n'
            f'Data/Hora: {now_str}\n'
            f'Tempo total fora do ar: ~{downtime} minutos\n'
        )
        notify_all(subject, body)
        state['last_state'] = 'up'
        state['last_alert_at'] = now
        state.pop('down_since', None)
        save_state(state)
        logger.info('SITE RECOVERED — alert sent')

    elif not is_up and last_state == 'down':
        if now - last_alert > cooldown * 6:
            from scripts.notifier import notify_all
            subject = f'[LEMBRETE] defumadosac.com.br continua fora do ar'
            down_since = state.get('down_since', now)
            downtime = int((now - down_since) / 60)
            body = (
                f'O site defumadosac.com.br CONTINUA fora do ar.\n\n'
                f'Fora do ar há aproximadamente {downtime} minutos.\n'
                f'Último alerta: {datetime.fromtimestamp(last_alert).strftime("%H:%M")}\n'
            )
            notify_all(subject, body)
            state['last_alert_at'] = now
            save_state(state)

    else:
        state['last_state'] = 'up'
        save_state(state)


if __name__ == '__main__':
    main()
