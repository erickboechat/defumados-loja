import json
import pytest


def test_init_db_cria_tabelas(db):
    tabelas = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    nomes = [t['name'] for t in tabelas]
    assert 'produtos' in nomes
    assert 'pedidos' in nomes
    assert 'avisos_estoque' in nomes


class TestProdutos:
    def test_add_produto(self, db):
        from models import add_produto
        add_produto('Bacon Artesanal', 29.90, 'Bacon defumado premium',
                    ['bacon.jpg'], 1, peso='500g', ingredientes='Porco, sal')
        rows = db.execute('SELECT * FROM produtos').fetchall()
        assert len(rows) == 1
        assert rows[0]['nome'] == 'Bacon Artesanal'
        assert rows[0]['preco'] == 29.90

    def test_get_produtos(self, db):
        from models import add_produto, get_produtos
        add_produto('Produto A', 10.0, '', [], 1)
        add_produto('Produto B', 20.0, '', [], 1)
        produtos = get_produtos(todos=True)
        assert len(produtos) >= 2

    def test_get_produto_retorna_none_se_invalido(self, db):
        from models import get_produto
        assert get_produto(9999) is None

    def test_get_produtos_paginados(self, db):
        from models import add_produto, get_produtos_paginados
        for i in range(20):
            add_produto(f'Produto {i}', 10.0, '', [], 1)
        pagina1, total = get_produtos_paginados(page=1, per_page=10, todos=True)
        assert len(pagina1) == 10
        assert total == 2

    def test_edit_produto(self, db):
        from models import add_produto, edit_produto, get_produto
        add_produto('Original', 10.0, 'Desc', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        edit_produto(pid, 'Editado', 15.0, 'Nova desc', 1, peso='1kg')
        p = get_produto(pid)
        assert p['nome'] == 'Editado'
        assert p['preco'] == 15.0

    def test_toggle_visivel(self, db):
        from models import add_produto, toggle_visivel
        add_produto('Teste', 10.0, '', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        toggle_visivel(pid)
        row = db.execute('SELECT visivel FROM produtos WHERE id=?', (pid,)).fetchone()
        assert row['visivel'] == 0
        toggle_visivel(pid)
        row = db.execute('SELECT visivel FROM produtos WHERE id=?', (pid,)).fetchone()
        assert row['visivel'] == 1

    def test_toggle_estoque(self, db):
        from models import add_produto, toggle_estoque
        add_produto('Teste', 10.0, '', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        toggle_estoque(pid)
        row = db.execute('SELECT estoque FROM produtos WHERE id=?', (pid,)).fetchone()
        assert row['estoque'] == 0
        toggle_estoque(pid)
        row = db.execute('SELECT estoque FROM produtos WHERE id=?', (pid,)).fetchone()
        assert row['estoque'] == 1

    def test_deletar_produto(self, db):
        from models import add_produto, deletar_produto
        add_produto('Temp', 10.0, '', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        deletar_produto(pid)
        row = db.execute('SELECT id FROM produtos WHERE id=?', (pid,)).fetchone()
        assert row is None


class TestPedidos:
    def _add_pedido(self, db, telefone='21999999999'):
        from models import add_pedido
        itens = json.dumps([{'nome': 'Bacon', 'qtd': 2, 'preco': 29.90}])
        return add_pedido(
            'Cliente Teste', telefone, 'Rua A', '100', '', 'Centro', 'Rio', 'RJ',
            '', 'cliente@email.com', '300', 'entrega', itens, 59.80, 0.0, ''
        )

    def test_add_pedido(self, db):
        from models import get_pedido
        pedido_id = self._add_pedido(db)
        pedido = get_pedido(pedido_id)
        assert pedido is not None
        assert pedido['cliente_nome'] == 'Cliente Teste'
        assert pedido['total'] == 59.80
        assert pedido['status'] == 'registrado'

    def test_get_pedidos_retorna_lista(self, db):
        from models import get_pedidos
        pedidos = get_pedidos()
        assert isinstance(pedidos, list)

    def test_update_pedido_status(self, db):
        from models import get_pedido, update_pedido_status
        pid = self._add_pedido(db)
        update_pedido_status(pid, 'entregue')
        pedido = get_pedido(pid)
        assert pedido['status'] == 'entregue'

    def test_delete_pedido(self, db):
        from models import get_pedido, delete_pedido
        pid = self._add_pedido(db)
        delete_pedido(pid)
        assert get_pedido(pid) is None

    def test_get_pedidos_by_telefone(self, db):
        for _ in range(3):
            self._add_pedido(db, telefone='21988887777')
        from models import get_pedidos_by_telefone
        pedidos = get_pedidos_by_telefone('21988887777')
        assert len(pedidos) == 3


class TestAvisos:
    def test_add_aviso(self, db):
        from models import add_aviso, add_produto, count_avisos_pendentes, get_avisos_pendentes
        add_produto('Teste', 10.0, '', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        add_aviso(pid, 'João', 'joao@email.com', '21999991111')
        assert count_avisos_pendentes(pid) >= 1
        avisos = get_avisos_pendentes(pid)
        assert any(a['produto_id'] == pid for a in avisos)

    def test_marcar_notificados(self, db):
        from models import add_aviso, add_produto, marcar_notificados, get_avisos_pendentes
        add_produto('Teste', 10.0, '', [], 1)
        pid = db.execute('SELECT id FROM produtos ORDER BY id DESC LIMIT 1').fetchone()['id']
        add_aviso(pid, 'Maria', 'maria@email.com', '21900000000')
        marcar_notificados(pid)
        restantes = get_avisos_pendentes(pid)
        assert len(restantes) == 0
