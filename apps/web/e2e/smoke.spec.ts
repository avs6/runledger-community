import { expect, test, type Page } from '@playwright/test'

// Signs in once, then opens every sidebar link and fails on a server error, a Next.js
// error page or an error toast. Credentials come from the environment; the defaults are the
// local seed's platform admin (apps/api seed), never a real account.
const EMAIL = process.env.E2E_EMAIL ?? 'admin@runledger.local'
const PASSWORD = process.env.E2E_PASSWORD ?? 'runledger'

async function signIn(page: Page) {
  await page.goto('/login')
  await page.locator('#email').fill(EMAIL)
  await page.locator('input[type="password"]').first().fill(PASSWORD)
  await page.locator('button[type="submit"]').first().click()
  await page.waitForURL((url) => !url.pathname.startsWith('/login'), { timeout: 30_000 })
}

test('every sidebar page loads without errors', async ({ page }) => {
  await signIn(page)
  const hrefs = await page.locator('aside nav a[href^="/"]').evaluateAll((links) =>
    Array.from(new Set(links.map((a) => (a as HTMLAnchorElement).getAttribute('href') ?? ''))).filter(Boolean),
  )
  expect(hrefs.length, 'sidebar links found').toBeGreaterThan(5)

  const failures: string[] = []
  for (const href of hrefs) {
    const serverErrors: string[] = []
    const onResponse = (res: { status(): number; url(): string }) => {
      if (res.status() >= 500 && !res.url().includes('/_next/')) serverErrors.push(`${res.status()} ${res.url()}`)
    }
    page.on('response', onResponse)
    const resp = await page.goto(href, { waitUntil: 'networkidle' })
    page.off('response', onResponse)
    if (!resp || resp.status() >= 500) failures.push(`${href}: page returned ${resp?.status()}`)
    if (await page.getByText('Application error: a client-side exception has occurred').count()) failures.push(`${href}: client-side exception`)
    if (await page.locator('[data-sonner-toast][data-type="error"]').count()) failures.push(`${href}: error toast`)
    for (const e of serverErrors) failures.push(`${href}: ${e}`)
  }
  expect(failures, failures.join('\n')).toEqual([])
})
