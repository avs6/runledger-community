import { expect, test, type Page } from '@playwright/test'

// BFF (review P-06): the workspace session key lives only in the httpOnly NextAuth cookie.
// The browser sees a placeholder, API calls go through /api/rl/*, the proxy refuses
// cross-site mutations, and signing out revokes the key server-side.
const EMAIL = process.env.E2E_EMAIL ?? 'admin@runledger.local'
const PASSWORD = process.env.E2E_PASSWORD ?? 'runledger'
const RAW_KEY = /rl_(live|test)_[A-Za-z0-9_-]{16,}/

async function signIn(page: Page) {
  await page.goto('/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('input[type="password"]').first().fill(PASSWORD)
  await page.locator('button[type="submit"]').first().click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 30_000 })
}

test('the session key never reaches browser JS', async ({ page }) => {
  await signIn(page)

  const session = await page.evaluate(() => fetch('/api/auth/session').then((r) => r.json()))
  expect(session.apiKey).toBe('bff-session')
  expect(JSON.stringify(session)).not.toMatch(RAW_KEY)

  const html = await page.content()
  expect(html).not.toMatch(RAW_KEY)

  const cookies = await page.context().cookies()
  const sessionCookie = cookies.find((c) => c.name.endsWith('next-auth.session-token'))
  expect(sessionCookie?.httpOnly, 'session cookie is httpOnly').toBe(true)
  const readable = await page.evaluate(() => document.cookie)
  expect(readable).not.toContain('session-token')
})

test('API calls go through the BFF proxy with the cookie', async ({ page }) => {
  await signIn(page)
  const me = await page.evaluate(() => fetch('/api/rl/auth/me').then(async (r) => ({ status: r.status, body: await r.json() })))
  expect(me.status).toBe(200)
  expect(me.body.email).toBe(EMAIL)
})

test('the BFF refuses unauthenticated and cross-site requests', async ({ page, playwright, baseURL }) => {
  const anon = await playwright.request.newContext({ baseURL })
  expect((await anon.get('/api/rl/auth/me')).status()).toBe(401)
  await anon.dispose()

  await signIn(page)
  const crossSite = await page.request.post('/api/rl/auth/logout', {
    headers: { Origin: 'https://evil.example', 'Sec-Fetch-Site': 'cross-site' },
  })
  expect(crossSite.status()).toBe(403)
  expect((await page.request.get('/api/rl/admin/tenants')).status()).toBe(403)
})

test('signing out revokes the key server-side', async ({ page }) => {
  await signIn(page)
  const cookies = await page.context().cookies()
  await page.goto('/api/auth/signout')
  await page.locator('button[type="submit"], form button').first().click()
  await page.waitForURL((url) => url.pathname.startsWith('/login') || url.pathname === '/', { timeout: 30_000 })

  // Replay the old session cookie: the key inside it was revoked by the signOut event.
  const replay = await page.context().browser()!.newContext({ baseURL: page.url() })
  await replay.addCookies(cookies)
  const res = await replay.request.get('/api/rl/auth/me')
  expect(res.status()).toBe(401)
  await replay.close()
})
