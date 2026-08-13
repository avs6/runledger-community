import { redirect } from 'next/navigation'

export default function PluginsRedirectPage() {
  redirect('/onboarding?section=connections')
}
