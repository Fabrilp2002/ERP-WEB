import { test, expect } from '@playwright/test'

/**
 * Smoke tests sin login — verifican que las páginas públicas cargan
 * y que el bundle de Next está sirviendo correctamente.
 *
 * Para correr:
 *   E2E_BASE_URL=https://erp-web-app-delta.vercel.app npm run test:e2e
 */

test.describe('Smoke — sin login', () => {
  test('/login renderiza el formulario', async ({ page }) => {
    const response = await page.goto('/login')
    expect(response?.status()).toBeLessThan(400)
    // Tiene que existir un input de email/usuario y uno de password
    await expect(page.locator('input[type="email"], input[name="email"], input[name="username"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
  })

  test('/api/version responde con commit actual', async ({ page }) => {
    const response = await page.goto('/api/version')
    expect(response?.status()).toBe(200)
    const body = await response!.json()
    expect(body).toHaveProperty('commit')
    expect(typeof body.commit).toBe('string')
    expect(body.commit.length).toBeGreaterThanOrEqual(7)
  })

  test('rutas protegidas redirigen a /login', async ({ page }) => {
    const response = await page.goto('/dashboard')
    expect(response?.status()).toBeLessThan(400)
    // Sin token, el AppLayout hace router.replace('/login')
    await expect(page).toHaveURL(/\/login/)
  })
})
