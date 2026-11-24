import { getToken } from 'next-auth/jwt'
import { NextRequest, NextResponse } from 'next/server'
import { BFF_SESSION_KEY } from '@/lib/api/client'
import { isSameOrigin } from '@/lib/bff'

export const dynamic = 'force-dynamic'

function gatewayBaseUrl() {
  if (process.env.GATEWAY_RUNTIME_URL) return process.env.GATEWAY_RUNTIME_URL
  if (process.env.NEXT_PUBLIC_GATEWAY_RUNTIME_URL) return process.env.NEXT_PUBLIC_GATEWAY_RUNTIME_URL
  if ((process.env.API_URL || '').includes('runledger-api')) return 'http://runledger-gateway-rs:8210'
  return 'http://localhost:8210'
}

/**
 * Playground → gateway-rs. A caller-supplied key is passed through; the dashboard's own
 * placeholder (or no header) is swapped for the session key from the httpOnly cookie,
 * so the browser never holds it (review P-06).
 */
async function resolveAuthorization(request: NextRequest): Promise<string | null> {
  const header = request.headers.get('authorization')
  if (header && header !== `Bearer ${BFF_SESSION_KEY}`) return header
  if (!isSameOrigin(request)) return null
  const token = await getToken({ req: request })
  return token?.apiKey ? `Bearer ${token.apiKey}` : null
}

export async function POST(request: NextRequest) {
  const authorization = await resolveAuthorization(request)
  if (!authorization) {
    return NextResponse.json({ detail: 'Missing bearer token' }, { status: 401 })
  }

  const upstream = `${gatewayBaseUrl().replace(/\/$/, '')}/gateway/chat/completions`
  const body = await request.text()
  const response = await fetch(upstream, {
    method: 'POST',
    headers: {
      'Content-Type': request.headers.get('content-type') || 'application/json',
      Authorization: authorization,
      'X-RunLedger-End-User-Id': request.headers.get('x-runledger-end-user-id') || '',
      'X-RunLedger-Tags': request.headers.get('x-runledger-tags') || '',
      'X-RunLedger-Region': request.headers.get('x-runledger-region') || '',
    },
    body,
    cache: 'no-store',
  })

  const contentType = response.headers.get('content-type') || 'application/json'

  if (contentType.includes('text/event-stream') && response.body) {
    return new Response(response.body, {
      status: response.status,
      headers: {
        'content-type': 'text/event-stream',
        'cache-control': 'no-cache',
        connection: 'keep-alive',
      },
    })
  }

  const payload = await response.arrayBuffer()
  return new NextResponse(payload, {
    status: response.status,
    headers: {
      'content-type': contentType,
      'cache-control': 'no-store',
    },
  })
}
