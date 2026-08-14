import { redirect } from 'next/navigation'

export default function McpPage() {
  redirect('/mcp-registry?tab=setup')
}
