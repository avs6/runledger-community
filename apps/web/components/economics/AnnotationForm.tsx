'use client'

import { useState } from 'react'
import { createAnnotation } from '@/lib/api'
import type { Annotation } from '@/types/api'

const inputCls =
  'h-9 rounded-md border border-gray-300 bg-white px-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500'

interface Props {
  apiKey: string
  onCreated: (annotation: Annotation) => void
}

export default function AnnotationForm({ apiKey, onCreated }: Props) {
  const [note, setNote] = useState('')
  const [annotationDate, setAnnotationDate] = useState(
    new Date().toISOString().slice(0, 10)
  )
  const [version, setVersion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    setLoading(true)
    setError(null)
    try {
      const annotation = await createAnnotation(apiKey, {
        note: note.trim(),
        annotation_date: annotationDate,
        version: version.trim() || null,
      })
      onCreated(annotation)
      setNote('')
      setVersion('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save annotation')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Date</label>
          <input
            type="date"
            value={annotationDate}
            onChange={(e) => setAnnotationDate(e.target.value)}
            required
            className={inputCls}
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
            Version (optional)
          </label>
          <input
            type="text"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="e.g. v2.1"
            className={inputCls}
          />
        </div>
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">Note</label>
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          required
          rows={2}
          placeholder="e.g. switched gpt-4o → gpt-4o-mini"
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500"
        />
      </div>
      {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
      <button
        type="submit"
        disabled={loading || !note.trim()}
        className="h-9 rounded-md bg-indigo-600 px-4 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? 'Saving…' : 'Add annotation'}
      </button>
    </form>
  )
}
