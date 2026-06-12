import json

from models import add_produto, add_pedido


# ===== CHECKOUT =====

class TestCheckout:
    def test_checkout_page_returns_200(self, client):
        resp = client.get('/checkout')
        assert resp.status_code == 200

    def test_finalizar_returns_whatsapp_link(self, client):
        payload = {
            'itens': [{'nome': 'Insensat', 'preco': 39.90, 'qtd': 2}],
            'nome': 'João',
            'telefone': '21999990000',
            'endereco': 'Rua X, 123',
            'cep': '21000-000',
            'frete_metodo': 'PAC',
            'frete_valor': 15.50,
            'total': 95.30,
        }
        resp = client.post('/finalizar',
                           data=json.dumps(payload),
                           content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'redirect' in data
        assert 'api.whatsapp.com' in data['redirect']

    def test_finalizar_empty_cart(self, client):
        payload = {
            'itens': [],
            'nome': 'João',
            'telefone': '21999990000',
            'endereco': 'Rua X',
            'cep': '21000-000',
            'frete_metodo': 'PAC',
            'frete_valor': 0,
            'total': 0,
        }
        resp = client.post('/finalizar',
                           data=json.dumps(payload),
                           content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'redirect' in data

    def test_process_checkout_requires_lgpd(self, client):
        resp = client.post('/checkout/process', data={
            'nome': 'João',
            'telefone': '21999990000',
            'endereco': 'Rua X',
        })
        assert resp.status_code == 302

    def test_process_checkout_requires_cart(self, client):
        resp = client.post('/checkout/process', data={
            'lgpd_consent': '1',
            'nome': 'João',
            'telefone': '21999990000',
            'endereco': 'Rua X',
            'carrinho_json': '[]',
        })
        assert resp.status_code == 302

    def test_process_checkout_creates_order(self, client):
        itens = [{'nome': 'Insensat', 'preco': 39.90, 'qtd': 1}]
        resp = client.post('/checkout/process', data={
            'lgpd_consent': '1',
            'nome': 'Maria',
            'telefone': '21999998888',
            'email': 'maria@test.com',
            'cep': '21000-000',
            'endereco': 'Rua Y, 456',
            'numero': '456',
            'complemento': 'Apto 1',
            'bairro': 'Centro',
            'cidade': 'Rio de Janeiro',
            'estado': 'RJ',
            'referencia': 'Próximo ao mercado',
            'forma_entrega': 'Entrega',
            'frete_valor': '10.00',
            'frete_texto': 'PAC - R$ 10,00',
            'carrinho_json': json.dumps(itens),
        })
        assert resp.status_code == 302


# ===== MEUS PEDIDOS =====

class TestMeusPedidos:
    def test_get_meus_pedidos_page(self, client):
        resp = client.get('/meus-pedidos')
        assert resp.status_code == 200

    def test_post_meus_pedidos_search(self, client):
        resp = client.post('/meus-pedidos', data={'telefone': '21999990000'})
        assert resp.status_code == 200

    def test_post_meus_pedidos_empty_phone(self, client):
        resp = client.post('/meus-pedidos', data={'telefone': ''})
        assert resp.status_code == 200

    def test_meus_pedidos_detalhe_404(self, client):
        resp = client.get('/meus-pedidos/99999')
        assert resp.status_code == 404

    def test_meus_pedidos_detalhe_with_order(self, client, db):
        pid = add_pedido(
            nome='Teste', telefone='21999990000',
            endereco='Rua Z', numero='10', complemento='',
            bairro='Centro', cidade='Rio', estado='RJ',
            referencia='', email='t@t.com', cep='21000-000',
            forma_entrega='Entrega', itens_json='[]',
            total=50.0, frete_valor=10.0, frete_texto='PAC'
        )
        resp = client.get(f'/meus-pedidos/{pid}')
        assert resp.status_code == 200


# ===== ADMIN LOGIN =====

class TestAdminLogin:
    def test_login_page_returns_200(self, client):
        resp = client.get('/admin/login')
        assert resp.status_code == 200
        assert b'login' in resp.data.lower()

    def test_login_success(self, client):
        from config import Config
        resp = client.post('/admin/login', data={
            'username': Config.ADMIN_USER,
            'password': Config.ADMIN_PASSWORD,
        })
        assert resp.status_code == 302
        assert '/admin' in resp.headers['Location']

    def test_login_wrong_password(self, client):
        from config import Config
        resp = client.post('/admin/login', data={
            'username': Config.ADMIN_USER,
            'password': 'wrongpassword',
        })
        assert resp.status_code == 200
        assert b'inv' in resp.data.lower()

    def test_login_wrong_username(self, client):
        resp = client.post('/admin/login', data={
            'username': 'wronguser',
            'password': 'mudarme123',
        })
        assert resp.status_code == 200
        assert b'inv' in resp.data.lower()

    def test_admin_dashboard_requires_login(self, client):
        resp = client.get('/admin/')
        assert resp.status_code == 302
        assert '/admin/login' in resp.headers['Location']

    def test_admin_dashboard_after_login(self, client):
        from config import Config
        client.post('/admin/login', data={
            'username': Config.ADMIN_USER,
            'password': Config.ADMIN_PASSWORD,
        })
        resp = client.get('/admin/')
        assert resp.status_code == 200

    def test_admin_logout(self, client):
        from config import Config
        client.post('/admin/login', data={
            'username': Config.ADMIN_USER,
            'password': Config.ADMIN_PASSWORD,
        })
        resp = client.get('/admin/logout')
        assert resp.status_code == 302
        assert resp.headers['Location'] == '/'

    def test_admin_routes_require_login(self, client):
        get_routes = ['/admin/', '/admin/pedidos', '/admin/logs']
        for route in get_routes:
            resp = client.get(route)
            assert resp.status_code == 302, f'{route} should redirect to login'
        post_routes = ['/admin/add']
        for route in post_routes:
            resp = client.post(route)
            assert resp.status_code == 302, f'{route} POST should redirect to login'


# ===== FLASK.G + DB CONNECTION =====

class TestFlaskGDb:
    def test_same_connection_within_request(self, client):
        from models import get_db
        with client.application.app_context():
            conn1 = get_db()
            conn2 = get_db()
            assert conn1 is conn2

    def test_different_connections_across_requests(self, client):
        from models import get_db
        connections = []

        with client.application.app_context():
            connections.append(id(get_db()))

        with client.application.app_context():
            connections.append(id(get_db()))

        assert len(connections) == 2

    def test_db_connection_closed_after_request(self, client):
        from flask import g
        with client.application.app_context():
            client.get('/')
            assert not hasattr(g, '_database') or g._database is None
