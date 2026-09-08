import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getPlaygroundSessions, getPlaygroundHistory } from '@/lib/api'
import type { PlaygroundSessionResponse, PlaygroundRequestResponse } from '@/types/api'
import PlaygroundClient from './PlaygroundClient'

export default async function PlaygroundPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to use the playground.</p>

  let sessions: PlaygroundSessionResponse[] = []
  let history: PlaygroundRequestResponse[] = []
  let historyTotal = 0
  try {
    const [sessData, histData] = await Promise.all([
      getPlaygroundSessions(apiKey, { limit: 10 }),
      getPlaygroundHistory(apiKey, { limit: 50 }),
    ])
    sessions = sessData.sessions
    history = histData.requests
    historyTotal = histData.total
  } catch {
    // pass empty defaults
  }

  return (
    <PlaygroundClient
      initialSessions={sessions}
      initialHistory={history}
      initialHistoryTotal={historyTotal}
    />
  )
}
