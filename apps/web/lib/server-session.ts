/**
 * Server-only access to the dashboard session key (review P-06 / technical review
 * security #1).
 *
 * The workspace session key lives only inside the NextAuth JWT, an encrypted, httpOnly
 * cookie. The browser never sees it: `session.apiKey` is the placeholder
 * `BFF_SESSION_KEY`, browser calls go through the `/api/rl/*` proxy, and server code
 * resolves the real key here.
 *
 * Importing this module registers a resolver that `lib/api/client.ts` uses when server
 * components call `apiFetch(path, session.apiKey)` with the placeholder. `lib/auth.ts`
 * imports it, and every server page imports `authOptions` from there, so the resolver is
 * in place before any server-side fetch.
 */
import { decode, type JWT } from 'next-auth/jwt'

const COOKIE_NAMES = ['__Secure-next-auth.session-token', 'next-auth.session-token']

type CookieGetter = (name: string) => string | undefined

/** Decode the NextAuth session cookie (handles NextAuth's chunked `.0`, `.1` cookies). */
export async function decodeSessionCookie(get: CookieGetter): Promise<JWT | null> {
  const secret = process.env.NEXTAUTH_SECRET
  if (!secret) return null
  for (const name of COOKIE_NAMES) {
    let value = get(name)
    if (!value) {
      const parts: string[] = []
      for (let i = 0; ; i++) {
        const chunk = get(`${name}.${i}`)
        if (!chunk) break
        parts.push(chunk)
      }
      if (parts.length) value = parts.join('')
    }
    if (!value) continue
    try {
      return await decode({ token: value, secret })
    } catch {
      return null
    }
  }
  return null
}

/** The real session key for the current request (RSC, route handlers, server actions). */
export async function getSessionApiKey(): Promise<string | null> {
  try {
    const { cookies } = await import('next/headers')
    const jar = cookies()
    const token = await decodeSessionCookie((name) => jar.get(name)?.value)
    return (token?.apiKey as string | undefined) ?? null
  } catch {
    return null
  }
}

declare global {
  // eslint-disable-next-line no-var
  var __runledgerSessionKey: (() => Promise<string | null>) | undefined
}

globalThis.__runledgerSessionKey = getSessionApiKey
