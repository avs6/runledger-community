const MODEL_COLORS = [
  '#2563eb',
  '#06b6d4',
  '#22c55e',
  '#f97316',
  '#a855f7',
  '#ec4899',
  '#eab308',
  '#14b8a6',
  '#6366f1',
  '#84cc16',
  '#ef4444',
  '#0ea5e9',
]

const MODEL_COLOR_OVERRIDES: Record<string, string> = {
  'llama3.1:8b': '#22c55e',
  'llama3.2': '#16a34a',
  'llama3.2:3b': '#4ade80',
  'deepseek-r1:14b': '#f97316',
  'deepseek-r1:8b': '#fb923c',
  'qwen2.5-coder:14b': '#06b6d4',
  'qwen3.5:latest': '#0ea5e9',
  'gemma3:latest': '#a855f7',
  'nomic-embed-text': '#ec4899',
  'gpt-5': '#2563eb',
  'claude': '#7c3aed',
  'gemini': '#0891b2',
}

export const MODEL_FAMILY_COLORS: Record<string, string> = {
  'GPT-5': '#2563eb',
  Claude: '#7c3aed',
  Gemini: '#0891b2',
  'Local Llama': '#22c55e',
  DeepSeek: '#f97316',
  Qwen: '#06b6d4',
  Gemma: '#a855f7',
  Embeddings: '#ec4899',
  'Cached Responses': '#16a34a',
  'Rejected Requests': '#ef4444',
  Other: '#64748b',
}

function hash(value: string) {
  let result = 0
  for (let i = 0; i < value.length; i += 1) {
    result = (result * 31 + value.charCodeAt(i)) >>> 0
  }
  return result
}

export function modelColor(model: string | null | undefined) {
  const key = (model ?? 'unknown').toLowerCase()
  for (const [match, color] of Object.entries(MODEL_COLOR_OVERRIDES)) {
    if (key.includes(match)) return color
  }
  return MODEL_COLORS[hash(key) % MODEL_COLORS.length]
}

export function classifyModel(model: string | null | undefined, opts?: { provider?: string | null; status?: string | null; cachedTokens?: number | null; success?: boolean | null }) {
  const haystack = `${model ?? ''} ${opts?.provider ?? ''}`.toLowerCase()
  if (opts?.success === false || opts?.status === 'failed' || opts?.status === 'rejected') return 'Rejected Requests'
  if ((opts?.cachedTokens ?? 0) > 0) return 'Cached Responses'
  if (haystack.includes('gpt') || haystack.includes('openai')) return 'GPT-5'
  if (haystack.includes('claude') || haystack.includes('anthropic')) return 'Claude'
  if (haystack.includes('gemini') || haystack.includes('google')) return 'Gemini'
  if (haystack.includes('deepseek')) return 'DeepSeek'
  if (haystack.includes('qwen')) return 'Qwen'
  if (haystack.includes('gemma')) return 'Gemma'
  if (haystack.includes('embed') || haystack.includes('nomic')) return 'Embeddings'
  if (haystack.includes('llama') || haystack.includes('ollama') || haystack.includes('local')) return 'Local Llama'
  return 'Other'
}
