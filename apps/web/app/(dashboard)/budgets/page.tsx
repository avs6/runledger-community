'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function BudgetsRedirect() {
  const router = useRouter()
  useEffect(() => { router.replace('/finance') }, [router])
  return null
}
