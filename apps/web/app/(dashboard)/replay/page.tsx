'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function ReplayRedirect() {
  const router = useRouter()
  useEffect(() => { router.replace('/evaluation') }, [router])
  return null
}
