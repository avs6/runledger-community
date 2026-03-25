'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { Suspense, useEffect, useState } from 'react'
import { toast } from 'sonner'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

function SsoCallbackContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const [status, setStatus] = useState<'loading' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    const token = searchParams.get('token')
    const error = searchParams.get('error')

    if (error) {
      const messages: Record<string, string> = {
        missing_params: 'Missing authorization parameters.',
        invalid_state: 'Invalid or expired SSO state. Please try again.',
        missing_claims: 'Identity provider did not return required user information.',
        config_not_found: 'SSO configuration not found.',
        server_error: 'An error occurred during sign-in. Please try again.',
      }
      setErrorMsg(messages[error] ?? `SSO error: ${error}`)
      setStatus('error')
      return
    }

    if (!token) {
      setErrorMsg('No SSO token received.')
      setStatus('error')
      return
    }

    async function exchangeAndSignIn() {
      try {
        const res = await fetch(`${API_URL}/auth/sso/exchange`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })

        if (!res.ok) {
          throw new Error('Token exchange failed')
        }

        const data = await res.json()

        const result = await signIn('sso', {
          redirect: false,
          email: data.email,
          apiKey: data.api_key,
          userId: data.user_id,
          workspaceId: data.workspace_id,
          workspaceName: data.workspace_name,
          tenantId: data.tenant_id,
          fullName: data.full_name ?? '',
          isPlatformAdmin: String(data.is_platform_admin),
          tenantRole: data.tenant_role ?? '',
          workspaceRole: data.workspace_role ?? '',
          workspaceIds: JSON.stringify(data.workspace_ids ?? []),
        })

        if (result?.ok) {
          toast.success('Signed in with SSO')
          router.push('/runs')
        } else {
          throw new Error(result?.error ?? 'Sign-in failed')
        }
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : 'Unexpected error during SSO sign-in')
        setStatus('error')
      }
    }

    exchangeAndSignIn()
  }, [searchParams, router])

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center space-y-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent mx-auto" />
          <p className="text-muted-foreground text-sm">Completing sign-in…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="max-w-md w-full mx-auto p-8 text-center space-y-4">
        <div className="text-4xl">⚠️</div>
        <h1 className="text-xl font-semibold">SSO Sign-in Failed</h1>
        <p className="text-muted-foreground text-sm">{errorMsg}</p>
        <button
          onClick={() => router.push('/login')}
          className="text-primary underline text-sm hover:no-underline"
        >
          Back to login
        </button>
      </div>
    </div>
  )
}

export default function SsoCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center bg-background">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <SsoCallbackContent />
    </Suspense>
  )
}
