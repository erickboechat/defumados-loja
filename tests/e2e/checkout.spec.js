const { test, expect } = require('@playwright/test');
const { setCart, getCart, mockViaCEP, createTestOrder } = require('./helpers');

const CART_ITEMS = [
  { id: 1, nome: 'Insensat 100g', preco: 39.90, qtd: 2 },
  { id: 2, nome: 'Linguiça Toscana', preco: 28.50, qtd: 1 },
];

test.describe('Checkout Flow', () => {
  test.describe('Empty Cart', () => {
    test('redirects to home when cart is empty', async ({ page }) => {
      await page.goto('/');
      await page.evaluate(() => localStorage.removeItem('defumados_carrinho'));
      await page.goto('/checkout');
      await page.waitForURL('/');
      expect(page.url()).toBe('http://127.0.0.1:5000/');
    });
  });

  test.describe('Cart with Items', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/');
      await setCart(page, CART_ITEMS);
    });

    test('checkout page renders with form fields', async ({ page }) => {
      await page.goto('/checkout');
      await expect(page.locator('#checkout-form')).toBeVisible();
      await expect(page.locator('input[name="cep"]')).toBeVisible();
      await expect(page.locator('input[name="endereco"]')).toBeVisible();
      await expect(page.locator('input[name="numero"]')).toBeVisible();
      await expect(page.locator('input[name="nome"]')).toBeVisible();
      await expect(page.locator('input[name="telefone"]')).toBeVisible();
    });

    test('checkout page shows order summary', async ({ page }) => {
      await page.goto('/checkout');
      const subtotal = page.locator('#resumo-subtotal');
      await expect(subtotal).toBeVisible();
      const text = await subtotal.textContent();
      expect(text).toMatch(/[\d,]+/);
    });

    test('submit button is disabled initially', async ({ page }) => {
      await page.goto('/checkout');
      const btn = page.locator('#btn-enviar');
      await expect(btn).toBeDisabled();
    });

    test('LGPD checkbox can be toggled', async ({ page }) => {
      await page.goto('/checkout');
      const checkbox = page.locator('#checkout-consent');
      await expect(checkbox).not.toBeChecked();
      await checkbox.check();
      await expect(checkbox).toBeChecked();
    });

    test('checkout fills all fields and submits via WhatsApp', async ({ page }) => {
      await mockViaCEP(page);

      await page.goto('/checkout');

      await page.fill('input[name="cep"]', '22041080');
      await page.locator('input[name="cep"]').blur();
      await page.waitForTimeout(1500);

      await page.fill('input[name="endereco"]', 'Rua das Flores');
      await page.fill('input[name="numero"]', '123');
      await page.fill('input[name="bairro"]', 'Copacabana');
      await page.fill('input[name="cidade"]', 'Rio de Janeiro');
      await page.fill('input[name="estado"]', 'RJ');
      await page.fill('input[name="nome"]', 'João Silva');
      await page.fill('input[name="telefone"]', '21999887766');

      await page.locator('#checkout-consent').check();

      await page.waitForFunction(() => {
        const btn = document.getElementById('btn-enviar');
        return btn && !btn.disabled;
      }, { timeout: 5000 });

      const subtotal = await page.locator('#resumo-subtotal').textContent();
      expect(subtotal).toMatch(/\d/);

      await page.click('#btn-enviar');

      await page.waitForTimeout(2000);

      const cartAfter = await getCart(page);
      expect(cartAfter).toHaveLength(0);
    });
  });
});

test.describe('Meus Pedidos Flow', () => {
  let uniquePhone;

  test.beforeEach(async ({ page }) => {
    uniquePhone = `219${Date.now().toString().slice(-7)}`;
  });

  test('page renders with search form', async ({ page }) => {
    await page.goto('/meus-pedidos');
    await expect(page.locator('h1')).toContainText('Meus Pedidos');
    await expect(page.locator('input[name="telefone"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('search with no results shows empty state', async ({ page }) => {
    await page.goto('/meus-pedidos');
    await page.fill('input[name="telefone"]', '00000000000');
    await page.click('button[type="submit"]');
    await expect(page.locator('text=Nenhum pedido encontrado')).toBeVisible();
  });

  test('search by phone shows results', async ({ page, request }) => {
    await createTestOrder(request, {
      telefone: uniquePhone,
      nome: 'Maria Teste',
      itens: [{ id: 999, nome: 'Insensat 100g', preco: 39.90, qtd: 1 }],
    });

    await page.goto('/meus-pedidos');
    await page.fill('input[name="telefone"]', uniquePhone);
    await page.click('button[type="submit"]');

    await expect(page.locator('text=pedido(s) encontrado(s)')).toBeVisible({ timeout: 5000 });
    const cards = page.locator('.pedido-card');
    await expect(cards.first()).toBeVisible();
    await expect(page.locator('.pedido-card-id').first()).toContainText('Pedido #');
  });

  test('click on order card navigates to detail', async ({ page, request }) => {
    await createTestOrder(request, {
      telefone: uniquePhone,
      nome: 'Pedro Detalhe',
      itens: [
        { id: 999, nome: 'Linguiça Toscana', preco: 28.50, qtd: 1 },
        { id: 998, nome: 'Copa 500g', preco: 55.00, qtd: 1 },
      ],
    });

    await page.goto('/meus-pedidos');
    await page.fill('input[name="telefone"]', uniquePhone);
    await page.click('button[type="submit"]');

    await expect(page.locator('.pedido-card').first()).toBeVisible({ timeout: 5000 });
    await page.locator('.pedido-card').first().click();
    await page.waitForURL(/\/meus-pedidos\/\d+/);

    await expect(page.locator('.detalhe-card')).toBeVisible();
    await expect(page.locator('.detalhe-status')).toBeVisible();
    await expect(page.locator('.item-linha')).toHaveCount(2);
  });

  test('phone mask works correctly', async ({ page }) => {
    await page.goto('/meus-pedidos');
    const input = page.locator('input[name="telefone"]');
    await input.fill('21999887766');
    const value = await input.inputValue();
    expect(value).toBe('(21) 99988-7766');
  });

  test('detail page shows products and total', async ({ page, request }) => {
    await createTestOrder(request, {
      telefone: uniquePhone,
      nome: 'Ana Resumo',
      itens: [
        { id: 999, nome: 'Copa 500g', preco: 55.00, qtd: 1 },
        { id: 998, nome: 'Costelinha 300g', preco: 42.00, qtd: 1 },
      ],
    });

    await page.goto('/meus-pedidos');
    await page.fill('input[name="telefone"]', uniquePhone);
    await page.click('button[type="submit"]');

    await expect(page.locator('.pedido-card').first()).toBeVisible({ timeout: 5000 });
    await page.locator('.pedido-card').first().click();

    await expect(page.locator('.item-linha')).toHaveCount(2);
    await expect(page.locator('.total-destaque')).toBeVisible();
  });

  test('back to store link works', async ({ page }) => {
    await page.goto('/meus-pedidos');
    await expect(page.locator('.voltar-loja')).toBeVisible();
    await page.click('.voltar-loja');
    await page.waitForURL('/');
    expect(page.url()).toBe('http://127.0.0.1:5000/');
  });

  test('search with empty phone shows all orders or empty', async ({ page }) => {
    await page.goto('/meus-pedidos');
    await page.fill('input[name="telefone"]', '');
    await page.click('button[type="submit"]');
    await expect(page.locator('.pedidos-page')).toBeVisible();
  });
});
