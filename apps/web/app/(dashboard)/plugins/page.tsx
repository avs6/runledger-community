import { redirect } from 'next/navigation'

export default function PluginsRedirectPage() {
  redirect('/integrations?tab=plugins')
}
