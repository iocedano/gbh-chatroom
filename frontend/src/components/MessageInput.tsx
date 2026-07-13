import { useState, type FormEvent } from 'react'
import { ErrorBanner } from './ErrorBanner'

interface MessageInputProps {
  onSend: (content: string) => Promise<void>
  disabled?: boolean
}

const MAX_LENGTH = 1000

export function MessageInput({ onSend, disabled = false }: MessageInputProps) {
  const [content, setContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = content.trim()
    if (!trimmed) return

    setError(null)
    setLoading(true)

    try {
      await onSend(trimmed)
      setContent('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Could not send message'
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <ErrorBanner message={error} />
      <div className="flex gap-2">
        <input
          type="text"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Type a message..."
          maxLength={MAX_LENGTH}
          disabled={disabled || loading}
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
        <button
          type="submit"
          disabled={disabled || loading || !content.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? 'Sending...' : 'Send'}
        </button>
      </div>
      <p className="text-right text-xs text-gray-400">
        {content.length}/{MAX_LENGTH}
      </p>
    </form>
  )
}
