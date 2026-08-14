import { redirect } from 'next/navigation'

export default function SearchToolsPage() {
  redirect('/tool-registry?tab=search')
}
