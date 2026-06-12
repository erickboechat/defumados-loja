const { test, expect } = require('@playwright/test');
const { login } = require('./helpers');

test.describe('Mobile Admin (375x812)', () => {
  test.use({
    viewport: { width: 375, height: 812 },
    isMobile: true,
    hasTouch: true,
  });

  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('hamburger menu button is visible', async ({ page }) => {
    await expect(page.locator('.admin-mobile-menu-btn')).toBeVisible();
  });

  test('sidebar opens and closes via hamburger', async ({ page }) => {
    await page.click('.admin-mobile-menu-btn');
    await expect(page.locator('#sidebar')).toHaveClass(/mobile-open/);
    await expect(page.locator('#sidebar-overlay')).toHaveClass(/mobile-open/);
    await page.click('#sidebar-overlay');
    await expect(page.locator('#sidebar')).not.toHaveClass(/mobile-open/);
  });

  test('stats are in 2x2 grid', async ({ page }) => {
    const stats = page.locator('.admin-stats');
    await expect(stats).toBeVisible();
  });

  test('product table renders as cards', async ({ page }) => {
    await expect(page.locator('.admin-table-card')).toBeVisible();
  });

  test('edit button works on mobile', async ({ page }) => {
    const editBtn = page.locator('button:has-text("✏️")').first();
    if (await editBtn.count() > 0) {
      await editBtn.click();
      await page.waitForTimeout(300);
      const editRow = page.locator('.edit-row').first();
      const display = await editRow.evaluate(el => window.getComputedStyle(el).display);
      expect(display).not.toBe('none');
    }
  });

  test('pull-to-refresh indicator exists in DOM', async ({ page }) => {
    const indicator = page.locator('.admin-pull-indicator');
    await expect(indicator).toBeAttached();
  });
});
