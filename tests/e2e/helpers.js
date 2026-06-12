const { expect } = require('@playwright/test');

const BASE_URL = 'http://127.0.0.1:5000';
const ADMIN_USER = process.env.ADMIN_USER || 'admin';
const ADMIN_PASS = process.env.ADMIN_PASS || 'mudarme123';

async function login(page) {
  await page.goto('/admin/login');
  await page.fill('input[name="username"]', ADMIN_USER);
  await page.fill('input[name="password"]', ADMIN_PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL('**/admin');
}

async function loginViaAPI(request) {
  const resp = await request.post('/admin/login', {
    form: { username: ADMIN_USER, password: ADMIN_PASS },
  });
  return resp;
}

module.exports = { login, loginViaAPI, BASE_URL, ADMIN_USER, ADMIN_PASS };
