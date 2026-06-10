import os
import sys
import tempfile
import pytest

os.environ['SECRET_KEY'] = 'test-secret-key-1234567890'
os.environ['FLASK_DEBUG'] = '0'
os.environ['SESSION_COOKIE_SECURE'] = '0'
os.environ['RATE_LIMIT_STORAGE'] = 'memory://'

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def app():
    _fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(_fd)
    from config import Config
    Config.DATABASE = db_path
    from models import init_db
    init_db()
    from app import app as _app
    _app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    ctx = _app.app_context()
    ctx.push()
    yield _app
    ctx.pop()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from models import get_db
    return get_db()
