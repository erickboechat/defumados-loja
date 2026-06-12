const { test, expect } = require('@playwright/test');
const { login } = require('./helpers');

test.describe('Admin Login', () => {
  test('login page renders with form', async ({ page }) => {
    await page.goto('/admin/login');
    await expect(page.locator('input[name="username"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('login with wrong credentials shows error', async ({ page }) => {
    await page.goto('/admin/login');
    await page.fill('input[name="username"]', 'wrong');
    await page.fill('input[name="password"]', 'wrong');
    await page.click('button[type="submit"]');
    await expect(page.locator('.login-error, .alert-error')).toBeVisible();
  });

  test('login with correct credentials redirects to dashboard', async ({ page }) => {
    await login(page);
    await expect(page).toHaveURL(/\/admin$/);
    await expect(page.locator('.admin-stats')).toBeVisible();
  });
});

test.describe('Admin Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('dashboard shows stats cards', async ({ page }) => {
    await expect(page.locator('.admin-stats')).toBeVisible();
    const stats = page.locator('.admin-stat');
    await expect(stats).toHaveCount(4);
  });

  test('dashboard shows product table', async ({ page }) => {
    await expect(page.locator('.admin-table-card')).toBeVisible();
  });

  test('add product form is collapsed by default', async ({ page }) => {
    const form = page.locator('#add-produto-form');
    await expect(form).toHaveCSS('display', 'none');
  });

  test('clicking add product header expands form', async ({ page }) => {
    await page.click('#add-produto-header');
    const form = page.locator('#add-produto-form');
    await expect(form).toBeVisible();
  });

  test('search bar is visible', async ({ page }) => {
    await expect(page.locator('.admin-search-bar')).toBeVisible();
  });

  test('edit button toggles inline edit row', async ({ page }) => {
    const editBtn = page.locator('button:has-text("✏️")').first();
    if (await editBtn.count() > 0) {
      await editBtn.click();
      const editRow = page.locator('.edit-row').first();
      await expect(editRow).toBeVisible();
      await editBtn.click();
      await expect(editRow).not.toBeVisible();
    }
  });
});

test.describe('Admin Search', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('search form filters products', async ({ page }) => {
    await page.fill('.admin-search-bar input[name="q"]', 'test');
    await page.click('.admin-search-bar button[type="submit"]');
    await expect(page).toHaveURL(/q=test/);
  });

  test('clear button resets search', async ({ page }) => {
    await page.fill('.admin-search-bar input[name="q"]', 'test');
    await page.click('.admin-search-bar button[type="submit"]');
    await expect(page).toHaveURL(/q=test/);
    const clearBtn = page.locator('a:has-text("Limpar")');
    if (await clearBtn.count() > 0) {
      await clearBtn.click();
      await expect(page).toHaveURL(/\/admin$/);
    }
  });
});

test.describe('Global Search (Cmd+K)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('keyboard shortcut opens search modal', async ({ page }) => {
    await page.keyboard.press('Control+k');
    const modal = page.locator('.admin-modal-overlay.open');
    await expect(modal).toBeVisible();
    await expect(page.locator('.admin-search-input')).toBeFocused();
  });

  test('Escape closes search modal', async ({ page }) => {
    await page.keyboard.press('Control+k');
    await expect(page.locator('.admin-modal-overlay.open')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('.admin-modal-overlay.open')).not.toBeVisible();
  });

  test('search button in topbar opens modal', async ({ page }) => {
    await page.click('.admin-topbar-search-btn');
    await expect(page.locator('.admin-modal-overlay.open')).toBeVisible();
  });
});

test.describe('Orders Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('orders page loads', async ({ page }) => {
    await page.goto('/admin/pedidos');
    await expect(page.locator('.admin-content')).toBeVisible();
  });

  test('search bar on orders page', async ({ page }) => {
    await page.goto('/admin/pedidos');
    await expect(page.locator('.admin-search-bar')).toBeVisible();
  });

  test('export button is visible', async ({ page }) => {
    await page.goto('/admin/pedidos');
    const exportBtn = page.locator('a:has-text("📥 Exportar CSV")');
    if (await exportBtn.count() > 0) {
      await expect(exportBtn).toBeVisible();
    }
  });
});

test.describe('Delete Product (Modal Confirm)', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('delete button opens confirmation modal', async ({ page }) => {
    const deleteForm = page.locator('form.admin-confirm-form').first();
    if (await deleteForm.count() > 0) {
      await deleteForm.locator('button[type="submit"]').click();
      const modal = page.locator('.admin-modal-overlay.open');
      await expect(modal).toBeVisible();
      await expect(page.locator('.admin-modal-body')).toContainText('Excluir');
      await page.click('.admin-modal-cancel');
      await expect(modal).not.toBeVisible();
    }
  });
});

test.describe('Health Check', () => {
  test('health endpoint returns ok', async ({ request }) => {
    const resp = await request.get('/health');
    expect(resp.ok()).toBeTruthy();
    const data = await resp.json();
    expect(data.status).toBe('ok');
  });
});
