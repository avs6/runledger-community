import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { getPlaygroundSessions, getPlaygroundHistory, getPlaygroundModels } from '@/lib/api'
import type { PlaygroundModel, PlaygroundSessionResponse, PlaygroundRequestResponse } from '@/types/api'
import PlaygroundClient from './PlaygroundClient'

export default async function PlaygroundPage() {
  const session = await getServerSession(authOptions)
  const apiKey = (session as Record<string, string> | null)?.apiKey
  if (!apiKey) return <p className="p-8 text-slate-500">Sign in to use the playground.</p>

  let sessions: PlaygroundSessionResponse[] = []
  let history: PlaygroundRequestResponse[] = []
  let historyTotal = 0
  let models: PlaygroundModel[] = []
  let loadError: string | null = null
  try {
    const [sessData, histData, modelData] = await Promise.all([
      getPlaygroundSessions(apiKey, { limit: 10 }),
      getPlaygroundHistory(apiKey, { limit: 50 }),
      getPlaygroundModels(apiKey),
    ])
    sessions = sessData.sessions
    history = histData.requests
    historyTotal = histData.total
    models = modelData.items
  } catch (err) {
    loadError = err instanceof Error ? err.message : 'Failed to load the Playground'
  }
  if (loadError) return <p role="alert" className="p-8 text-status-error">{loadError}</p>

  return (
    <PlaygroundClient
      initialSessions={sessions}
      initialHistory={history}
      initialHistoryTotal={historyTotal}
      models={models}
    />
  )
}
