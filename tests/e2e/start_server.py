import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

os.environ['SECRET_KEY'] = 'test-secret-key-e2e-1234567890abcdef'
os.environ['SESSION_COOKIE_SECURE'] = '0'
os.environ['RATE_LIMIT_STORAGE'] = 'memory://'

from app import app
from extensions import limiter

app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
limiter.enabled = False

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
