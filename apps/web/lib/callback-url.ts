// Where to send the user after sign-in.
//
// The auth middleware redirects signed-out visitors to /login?callbackUrl=<full URL>.
// Only same-origin paths are honoured (no open redirect), and auth pages themselves
// are never a destination. SSO sign-in leaves the site, so the target is kept in
// sessionStorage across the round trip.

const DEFAULT_AFTER_LOGIN = '/workflows'
const STORAGE_KEY = 'runledger.callbackUrl'
const AUTH_PATHS = ['/login', '/auth/', '/forgot-password', '/reset-password', '/verify-email']

export function safeCallbackPath(raw: string | null | undefined): string | null {
  if (!raw || typeof window === 'undefined') return null
  let url: URL
  try {
    url = new URL(raw, window.location.origin)
  } catch {
    return null
  }
  if (url.origin !== window.location.origin) return null
  const path = `${url.pathname}${url.search}${url.hash}`
  if (!path.startsWith('/') || path.startsWith('//')) return null
  if (AUTH_PATHS.some((p) => url.pathname === p || url.pathname.startsWith(p.endsWith('/') ? p : `${p}/`))) {
    return null
  }
  return path
}

/** Target from the current page's ?callbackUrl=, or the default. */
export function callbackFromLocation(): string {
  if (typeof window === 'undefined') return DEFAULT_AFTER_LOGIN
  const raw = new URLSearchParams(window.location.search).get('callbackUrl')
  return safeCallbackPath(raw) ?? DEFAULT_AFTER_LOGIN
}

/** Remember the target before leaving for an SSO provider. */
export function rememberCallback(): void {
  try {
    const raw = new URLSearchParams(window.location.search).get('callbackUrl')
    const path = safeCallbackPath(raw)
    if (path) window.sessionStorage.setItem(STORAGE_KEY, path)
    else window.sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // Storage unavailable: fall back to the default page after SSO.
  }
}

/** Target saved before SSO (cleared once read), or the default. */
export function takeRememberedCallback(): string {
  try {
    const saved = window.sessionStorage.getItem(STORAGE_KEY)
    window.sessionStorage.removeItem(STORAGE_KEY)
    return safeCallbackPath(saved) ?? DEFAULT_AFTER_LOGIN
  } catch {
    return DEFAULT_AFTER_LOGIN
  }
}
