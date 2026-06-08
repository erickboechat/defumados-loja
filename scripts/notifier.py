import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger('monitor')

# Carrega .env da raiz do projeto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(env_path)


def send_email(subject, body):
    gmail_user = os.environ.get('GMAIL_USER')
    gmail_pass = os.environ.get('GMAIL_APP_PASSWORD')
    alert_email = os.environ.get('ALERT_EMAIL')

    if not all([gmail_user, gmail_pass, alert_email]):
        logger.warning('Email not configured — skipping')
        return False

    msg = MIMEMultipart()
    msg['From'] = gmail_user
    msg['To'] = alert_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        logger.info('Email sent to %s', alert_email)
        return True
    except Exception as e:
        logger.error('Failed to send email: %s', e)
        return False


def send_whatsapp(body):
    account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
    auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
    twilio_from = os.environ.get('TWILIO_WHATSAPP_NUMBER')
    admin_to = os.environ.get('ADMIN_WHATSAPP')

    if not all([account_sid, auth_token, twilio_from, admin_to]):
        logger.warning('Twilio not configured — skipping WhatsApp')
        return False

    try:
        from twilio.rest import Client
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=body,
            from_=f'whatsapp:{twilio_from}',
            to=f'whatsapp:{admin_to}'
        )
        logger.info('WhatsApp sent (sid: %s)', message.sid)
        return True
    except Exception as e:
        logger.error('Failed to send WhatsApp: %s', e)
        return False


def notify_all(subject, body):
    send_email(subject, body)
    send_whatsapp(body)
