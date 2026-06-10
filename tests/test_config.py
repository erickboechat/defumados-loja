def test_config_imports():
    from config import Config, WHATSAPP_NUMBER, WHATSAPP_URL
    assert Config.SECRET_KEY == 'test-secret-key-1234567890'
    assert WHATSAPP_NUMBER == '5521986358184'
    assert '5521986358184' in WHATSAPP_URL


def test_admin_pass_hash():
    from werkzeug.security import check_password_hash
    from config import Config
    assert check_password_hash(Config.ADMIN_PASS_HASH, Config.ADMIN_PASSWORD)
