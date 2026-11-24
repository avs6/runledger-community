/**
 * BFF proxy: /api/rl/<path> → API_URL/<path> (review P-06, technical review security #1).
 *
 * The dashboard's workspace session key is kept only in the encrypted, httpOnly NextAuth
 * session cookie. Browser code calls this same-origin route; the route decrypts the
 * cookie server-side and adds `Authorization: Bearer <session key>`. An XSS can no
 * longer read a long-lived key with gateway (spend) rights from JS.
 *
 * Guards:
 *   - No session cookie (or no key in it) → 401, so the client redirects to /login.
 *   - Unsafe methods must come from this origin (Origin / Sec-Fetch-Site), on top of
 *     NextAuth's SameSite=Lax cookie, so another site can't drive mutations (CSRF).
 *   - Only API paths are proxied: /admin/* (admin secret) and /internal/* (service
 *     channel) are refused, and any Authorization or Cookie header from the browser is
 *     dropped in favour of the session key.
 * Responses stream through, so CSV exports and SSE work; Set-Cookie from the API is
 * never forwarded.
 */
import { getToken } from 'next-auth/jwt'
import { NextRequest, NextResponse } from 'next/server'
import { isSameOrigin } from '@/lib/bff'

export const dynamic = 'force-dynamic'

const API_URL = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201').replace(/\/$/, '')

const BLOCKED_PREFIXES = ['admin', 'internal']
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])

const FORWARD_REQUEST_HEADERS = ['content-type', 'accept', 'idempotency-key', 'if-none-match', 'last-event-id']
const FORWARD_RESPONSE_HEADERS = [
  'content-type',
  'content-disposition',
  'cache-control',
  'etag',
  'x-total-count',
  'retry-after',
  'x-ratelimit-limit-requests',
  'x-ratelimit-remaining-requests',
  'x-ratelimit-limit-tokens',
  'x-ratelimit-remaining-tokens',
  'x-ratelimit-reset',
]

function json(status: number, detail: string) {
  return NextResponse.json({ detail }, { status, headers: { 'cache-control': 'no-store' } })
}

async function proxy(request: NextRequest, { params }: { params: { path?: string[] } }) {
  const segments = params.path ?? []
  if (!segments.length || segments.some((s) => s === '..' || s === '.')) return json(400, 'Invalid API path')
  if (BLOCKED_PREFIXES.includes(segments[0])) return json(403, 'This path is not available through the dashboard')

  if (!SAFE_METHODS.has(request.method) && !isSameOrigin(request)) {
    return json(403, 'Cross-site request refused')
  }

  const token = await getToken({ req: request })
  const apiKey = token?.apiKey as string | undefined
  if (!apiKey) return json(401, 'Not signed in')

  const upstream = `${API_URL}/${segments.map(encodeURIComponent).join('/')}${request.nextUrl.search}`
  const headers: Record<string, string> = { Authorization: `Bearer ${apiKey}` }
  for (const name of FORWARD_REQUEST_HEADERS) {
    const value = request.headers.get(name)
    if (value) headers[name] = value
  }
  // RunLedger request metadata (tags, end user, region) passes through.
  request.headers.forEach((value, name) => {
    if (name.startsWith('x-runledger-')) headers[name] = value
  })

  let body: ArrayBuffer | undefined
  if (!SAFE_METHODS.has(request.method)) {
    body = await request.arrayBuffer()
  }

  let response: Response
  try {
    response = await fetch(upstream, {
      method: request.method,
      headers,
      body: body && body.byteLength ? body : undefined,
      cache: 'no-store',
      redirect: 'follow',
    })
  } catch {
    return json(502, 'The RunLedger API is unreachable')
  }

  const outHeaders = new Headers({ 'cache-control': 'no-store' })
  for (const name of FORWARD_RESPONSE_HEADERS) {
    const value = response.headers.get(name)
    if (value) outHeaders.set(name, value)
  }
  response.headers.forEach((value, name) => {
    if (name.startsWith('x-runledger-')) outHeaders.set(name, value)
  })
  if (response.status === 204 || response.status === 304 || request.method === 'HEAD') {
    return new Response(null, { status: response.status, headers: outHeaders })
  }

  // Stream only event streams and file downloads. Ordinary JSON is buffered and sent with a
  // Content-Length: a chunked body the page never reads (e.g. a 404 it only checks the
  // status of) otherwise stays open and keeps the page from ever going network-idle.
  const contentType = response.headers.get('content-type') ?? ''
  const isEventStream = contentType.includes('text/event-stream')
  const isDownload = (response.headers.get('content-disposition') ?? '').includes('attachment') || contentType.includes('text/csv')
  if (isEventStream) {
    outHeaders.set('cache-control', 'no-cache')
    outHeaders.set('x-accel-buffering', 'no')
  }
  if (isEventStream || isDownload) {
    return new Response(response.body, { status: response.status, headers: outHeaders })
  }
  const payload = await response.arrayBuffer()
  outHeaders.set('content-length', String(payload.byteLength))
  return new Response(payload, { status: response.status, headers: outHeaders })
}

export const GET = proxy
export const HEAD = proxy
export const POST = proxy
export const PUT = proxy
export const PATCH = proxy
export const DELETE = proxy
