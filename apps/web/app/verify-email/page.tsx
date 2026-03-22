'use client'

import { Suspense, useEffect, useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function VerifyContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token found.')
      return
    }

    fetch(`${API_URL}/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(async res => {
        if (res.ok) {
          setStatus('success')
        } else {
          const data = await res.json().catch(() => ({}))
          setStatus('error')
          setMessage(data.detail ?? 'Invalid or expired verification link.')
        }
      })
      .catch(() => {
        setStatus('error')
        setMessage('Network error. Please try again.')
      })
  }, [token])

  return (
    <div className="w-full max-w-sm text-center space-y-6">
      {status === 'loading' && (
        <>
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-teal-400" />
          <p className="text-slate-300 text-lg font-medium">Verifying your email…</p>
        </>
      )}

      {status === 'success' && (
        <>
          <CheckCircle2 className="mx-auto h-14 w-14 text-teal-400" />
          <div>
            <p className="text-white text-xl font-semibold">Email verified!</p>
            <p className="mt-2 text-slate-400 text-sm">Your account is active. You can now sign in.</p>
          </div>
          <Button
            className="w-full bg-gradient-to-r from-teal-600 to-cyan-600 text-white hover:from-teal-500 hover:to-cyan-500"
            onClick={() => router.push('/login')}
          >
            Go to Sign In
          </Button>
        </>
      )}

      {status === 'error' && (
        <>
          <XCircle className="mx-auto h-14 w-14 text-red-400" />
          <div>
            <p className="text-white text-xl font-semibold">Verification failed</p>
            <p className="mt-2 text-slate-400 text-sm">{message}</p>
          </div>
          <Link href="/login">
            <Button variant="outline" className="w-full border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800">
              Back to Sign In
            </Button>
          </Link>
        </>
      )}
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6">
      <Suspense fallback={
        <div className="text-center">
          <Loader2 className="mx-auto h-12 w-12 animate-spin text-teal-400" />
        </div>
      }>
        <VerifyContent />
      </Suspense>
    </div>
  )
}
