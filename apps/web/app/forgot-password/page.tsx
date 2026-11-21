'use client'

import Link from 'next/link'
import { useState } from 'react'
import AuthCard from '@/components/layout/AuthCard'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8201'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${API_URL}/auth/password-reset/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      if (res.status === 429) {
        setError('Too many requests. Try again later.')
      } else {
        setSent(true)
      }
    } catch {
      setError('Could not reach the server. Try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthCard title="Reset your password" subtitle="We'll email you a single-use reset link.">
      {sent ? (
        <div className="space-y-4">
          <p className="text-sm text-slate-600 dark:text-slate-300">
            If an account exists for <b>{email}</b>, a reset link is on its way. The link expires soon.
            If email delivery isn&apos;t configured on this server, ask an administrator to reset your password.
          </p>
          <Link href="/login" className="text-sm font-medium text-blue-700 hover:underline dark:text-blue-400">Back to sign in</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>{loading ? 'Sending…' : 'Send reset link'}</Button>
          <Link href="/login" className="block text-center text-sm text-slate-500 hover:underline">Back to sign in</Link>
        </form>
      )}
    </AuthCard>
  )
}
