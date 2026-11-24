/**
 * First-run setup (review P-01): production deployments seed no default account, so the
 * operator creates the first platform admin here.
 *
 *   GET  → { needs_bootstrap, environment }   (public, from GET /auth/bootstrap-status)
 *   POST → POST /admin/bootstrap with the operator-supplied ADMIN_SECRET
 *
 * Server-to-server, so the API needs no CORS for X-Admin-Secret. The API refuses with
 * 409 once any platform admin exists. The bootstrap API key in the response is not
 * returned to the browser: the operator signs in and creates keys on the API Keys page.
 */
import { NextRequest, NextResponse } from 'next/server'
import { isSameOrigin } from '@/lib/bff'

export const dynamic = 'force-dynamic'

const API_URL = (process.env.API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8201').replace(/\/$/, '')

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/auth/bootstrap-status`, { cache: 'no-store' })
    const body = await res.json().catch(() => ({}))
    return NextResponse.json(body, { status: res.status, headers: { 'cache-control': 'no-store' } })
  } catch {
    return NextResponse.json({ detail: 'The RunLedger API is unreachable' }, { status: 502 })
  }
}

interface SetupBody {
  admin_secret?: string
  email?: string
  password?: string
  full_name?: string
  org_name?: string
}

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) {
    return NextResponse.json({ detail: 'Cross-site request refused' }, { status: 403 })
  }
  const body = (await request.json().catch(() => ({}))) as SetupBody
  if (!body.admin_secret || !body.email || !body.password) {
    return NextResponse.json({ detail: 'Admin secret, email and password are required' }, { status: 422 })
  }
  try {
    const res = await fetch(`${API_URL}/admin/bootstrap`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Admin-Secret': body.admin_secret },
      body: JSON.stringify({
        email: body.email,
        password: body.password,
        full_name: body.full_name || null,
        org_name: body.org_name || 'Default Organization',
      }),
      cache: 'no-store',
    })
    const data = (await res.json().catch(() => ({}))) as Record<string, unknown>
    if (!res.ok) {
      const detail =
        res.status === 401 || res.status === 403
          ? 'The admin secret is not correct'
          : typeof data.detail === 'string'
            ? data.detail
            : 'Setup failed'
      return NextResponse.json({ detail }, { status: res.status })
    }
    return NextResponse.json({ ok: true, email: body.email, message: 'Platform admin created. Sign in to continue.' })
  } catch {
    return NextResponse.json({ detail: 'The RunLedger API is unreachable' }, { status: 502 })
  }
}
