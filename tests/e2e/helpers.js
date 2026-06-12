const { expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:5000';
const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'mudarme123';

async function login(page) {
  await page.goto('/admin/login');
  await page.fill('input[name="username"]', ADMIN_USER);
  await page.fill('input[name="password"]', ADMIN_PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/admin/);
}

async function loginViaAPI(request) {
  const resp = await request.post('/admin/login', {
    form: { username: ADMIN_USER, password: ADMIN_PASS },
  });
  return resp;
}

async function setCart(page, items) {
  await page.evaluate((cart) => {
    localStorage.setItem('defumados_carrinho', JSON.stringify(cart));
  }, items);
}

async function getCart(page) {
  return page.evaluate(() => {
    return JSON.parse(localStorage.getItem('defumados_carrinho') || '[]');
  });
}

async function mockViaCEP(page) {
  await page.route('**/viacep.com.br/**', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        logradouro: 'Rua das Flores',
        bairro: 'Copacabana',
        localidade: 'Rio de Janeiro',
        uf: 'RJ',
        erro: false,
      }),
    });
  });
}

async function createTestOrder(request, overrides = {}) {
  const data = {
    lgpd_consent: '1',
    nome: overrides.nome || 'Cliente Teste E2E',
    telefone: overrides.telefone || '21999887766',
    email: overrides.email || 'teste@teste.com',
    cep: overrides.cep || '22041-080',
    endereco: overrides.endereco || 'Rua das Flores',
    numero: overrides.numero || '123',
    complemento: overrides.complemento || '',
    bairro: overrides.bairro || 'Copacabana',
    cidade: overrides.cidade || 'Rio de Janeiro',
    estado: overrides.estado || 'RJ',
    referencia: overrides.referencia || '',
    forma_entrega: overrides.forma_entrega || 'Entrega',
    frete_valor: overrides.frete_valor || '15.00',
    frete_texto: overrides.frete_texto || 'Entrega Padrão - R$ 15,00',
    carrinho_json: JSON.stringify(overrides.itens || [
      { id: 999, nome: 'Produto Teste', preco: 39.90, qtd: 2 }
    ]),
  };
  const resp = await request.post('/checkout/process', { form: data });
  return resp;
}

module.exports = { login, loginViaAPI, setCart, getCart, mockViaCEP, createTestOrder, BASE_URL, ADMIN_USER, ADMIN_PASS };
