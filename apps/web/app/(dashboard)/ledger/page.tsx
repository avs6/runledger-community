'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function LedgerRedirect() {
  const router = useRouter()
  useEffect(() => { router.replace('/settings?tab=compliance') }, [router])
  return null
}
