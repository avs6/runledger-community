'use client'

import Link from 'next/link'
import { Suspense, useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import AuthCard from '@/components/layout/AuthCard'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8201'

function VerifyResult() {
  const token = useSearchParams().get('token') ?? ''
  const [state, setState] = useState<'pending' | 'ok' | 'error'>(token ? 'pending' : 'error')
  const [message, setMessage] = useState(token ? 'Verifying…' : 'This verification link is missing its token.')

  useEffect(() => {
    if (!token) return
    fetch(`${API_URL}/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}))
        setState(res.ok ? 'ok' : 'error')
        setMessage(typeof body.detail === 'string' ? body.detail : (body.message ?? 'Verification failed.'))
      })
      .catch(() => {
        setState('error')
        setMessage('Could not reach the server. Try again.')
      })
  }, [token])

  return (
    <div className="space-y-4">
      <p role={state === 'error' ? 'alert' : undefined} className={`text-sm ${state === 'error' ? 'text-red-600' : 'text-slate-600 dark:text-slate-300'}`}>{message}</p>
      {state !== 'pending' && (
        <Link href="/login" className="text-sm font-medium text-blue-700 hover:underline dark:text-blue-400">Go to sign in</Link>
      )}
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <AuthCard title="Email verification">
      <Suspense fallback={null}>
        <VerifyResult />
      </Suspense>
    </AuthCard>
  )
}
