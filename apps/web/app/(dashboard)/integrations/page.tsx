import { redirect } from 'next/navigation'

export default function IntegrationsRedirectPage() {
  redirect('/onboarding?section=connections')
}
