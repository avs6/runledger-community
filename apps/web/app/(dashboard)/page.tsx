import { redirect } from 'next/navigation'

// This route group index conflicts with app/page.tsx (both map to /).
// Redirect to the actual dashboard home page.
export default function DashboardIndexRedirect() {
  redirect('/dashboard')
}
