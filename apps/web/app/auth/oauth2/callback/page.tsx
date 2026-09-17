'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'

export default function OAuth2CallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state')
    const providerId = searchParams.get('provider_id') ?? sessionStorage.getItem('oauth2_provider_id')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError(`Authentication failed: ${searchParams.get('error_description') || errorParam}`)
      return
    }

    if (!code || !state || !providerId) {
      setError('Missing authentication parameters.')
      return
    }

    sessionStorage.removeItem('oauth2_provider_id')

    signIn('oauth2-callback', {
      code,
      state,
      provider_id: providerId,
      redirect: false,
    }).then((result) => {
      if (result?.error) {
        setError('Authentication failed. Please try again.')
      } else {
        router.push('/dashboard')
      }
    })
  }, [searchParams, router])

  if (error) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#f3f6fa] dark:bg-[#0a0e1a]">
        <div className="w-full max-w-md rounded-2xl border border-red-200 bg-white p-8 shadow-lg dark:border-red-800/60 dark:bg-slate-800">
          <p className="text-center text-red-700 dark:text-red-300">{error}</p>
          <button
            onClick={() => router.push('/login')}
            className="mt-4 w-full rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-500"
          >
            Back to login
          </button>
        </div>
      </main>
    )
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f3f6fa] dark:bg-[#0a0e1a]">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-blue-200 border-t-blue-600" />
        <p className="text-sm text-slate-500 dark:text-slate-400">Completing sign-in...</p>
      </div>
    </main>
  )
}
