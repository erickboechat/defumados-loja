"""Extensions inicializadas separadamente para evitar imports circulares."""
import os
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

csrf = CSRFProtect()

limiter = Limiter(
    get_remote_address,
    default_limits=["2000 per day", "300 per hour", "10 per second"],
    storage_uri=os.environ.get('RATE_LIMIT_STORAGE', 'memory://'),
)
