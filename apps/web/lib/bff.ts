/** Helpers for the BFF route handlers under app/api (review P-06). */
import type { NextRequest } from 'next/server'

/** True when an unsafe request demonstrably comes from this dashboard's own origin. */
export function isSameOrigin(request: NextRequest): boolean {
  const fetchSite = request.headers.get('sec-fetch-site')
  if (fetchSite && fetchSite !== 'same-origin' && fetchSite !== 'none') return false
  const origin = request.headers.get('origin')
  if (!origin) return fetchSite === 'same-origin'
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host')
  try {
    return new URL(origin).host === host
  } catch {
    return false
  }
}
