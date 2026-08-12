import { redirect } from 'next/navigation'

export default async function OrgSettingsPage({
  searchParams,
}: {
  searchParams?: Promise<{ tab?: string }>
}) {
  const params = await searchParams
  const tab = params?.tab === 'slack' ? 'slack' : 'email'
  redirect(`/organization?tab=${tab}`)
}
