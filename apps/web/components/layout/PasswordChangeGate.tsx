'use client'

import { useEffect } from 'react'
import { useSession } from 'next-auth/react'
import { usePathname, useRouter } from 'next/navigation'

/** Sends users signed in with an admin-issued temporary password to the account
 *  page until they set their own (the API also reports must_change_password). */
export default function PasswordChangeGate() {
  const { data: session } = useSession()
  const pathname = usePathname()
  const router = useRouter()
  useEffect(() => {
    if (session?.mustChangePassword && pathname !== '/account') {
      router.replace('/account?changePassword=1')
    }
  }, [session?.mustChangePassword, pathname, router])
  return null
}
