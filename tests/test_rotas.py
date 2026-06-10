def test_index(client):
    resp = client.get('/')
    assert resp.status_code == 200
    assert resp.content_type.startswith('text/html')


def test_produto_inexistente_retorna_404(client):
    resp = client.get('/produto/99999')
    assert resp.status_code == 404


def test_sitemap(client):
    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert resp.content_type == 'application/xml'
    assert b'<urlset' in resp.data


def test_robots_txt(client):
    resp = client.get('/robots.txt')
    assert resp.status_code == 200
    assert b'Sitemap' in resp.data


def test_csrf_token(client):
    resp = client.get('/csrf-token')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'token' in data


def test_api_produtos(client):
    resp = client.get('/api/produtos')
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)


def test_404_handler(client):
    resp = client.get('/pagina-que-nao-existe')
    assert resp.status_code == 404


def test_nossa_historia(client):
    resp = client.get('/nossa-historia')
    assert resp.status_code == 200


def test_contato_page(client):
    resp = client.get('/contato')
    assert resp.status_code == 200


def test_politicas_page(client):
    resp = client.get('/politicas')
    assert resp.status_code == 200


def test_health_check(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
    assert data['db'] == 'ok'
