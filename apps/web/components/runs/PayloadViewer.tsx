import type { RunDetailResponse } from '@/types/api'

interface Message {
  role: string
  content: string
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, string> = {
    system: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    user: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    assistant: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    tool: 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300',
  }
  return (
    <span
      className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium uppercase ${
        colors[role] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300'
      }`}
    >
      {role}
    </span>
  )
}

function MessageRow({ msg }: { msg: Message }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-gray-100 dark:border-gray-700 p-3">
      <RoleBadge role={msg.role} />
      <p className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
        {msg.content}
      </p>
    </div>
  )
}

interface PayloadViewerProps {
  run: RunDetailResponse
}

export default function PayloadViewer({ run }: PayloadViewerProps) {
  const hasPayload = run.input_payload != null || run.output_payload != null

  if (!hasPayload) {
    return (
      <div className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-4 py-8 text-center">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          No payload captured.{' '}
          <span className="text-gray-400 dark:text-gray-500">
            Set capture policy to <code className="font-mono">SAMPLED</code> or{' '}
            <code className="font-mono">FULL</code> to record message content.
          </span>
        </p>
      </div>
    )
  }

  const messages = run.input_payload ?? []
  const response =
    run.output_payload != null
      ? typeof run.output_payload === 'string'
        ? run.output_payload
        : JSON.stringify(run.output_payload, null, 2)
      : null

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300">Payload</h3>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          Captured: {run.total_input_tokens ?? 0} input /{' '}
          {run.total_output_tokens ?? 0} output tokens
        </span>
      </div>

      {messages.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
            Input
          </span>
          <div className="flex flex-col gap-2">
            {messages.map((msg, i) => (
              <MessageRow key={i} msg={msg as Message} />
            ))}
          </div>
        </div>
      )}

      {response != null && (
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium uppercase tracking-wide text-gray-400 dark:text-gray-500">
            Output
          </span>
          <div className="rounded-md border border-green-100 dark:border-green-900 bg-green-50 dark:bg-green-950/30 p-3">
            <RoleBadge role="assistant" />
            <p className="mt-2 whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
              {response}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
