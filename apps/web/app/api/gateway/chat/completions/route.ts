import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

function gatewayBaseUrl() {
  if (process.env.GATEWAY_RUNTIME_URL) return process.env.GATEWAY_RUNTIME_URL
  if (process.env.NEXT_PUBLIC_GATEWAY_RUNTIME_URL) return process.env.NEXT_PUBLIC_GATEWAY_RUNTIME_URL
  if ((process.env.API_URL || '').includes('runledger-api')) return 'http://runledger-gateway-rs:8210'
  return 'http://localhost:8210'
}

export async function POST(request: NextRequest) {
  const authorization = request.headers.get('authorization')
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
