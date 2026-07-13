import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { listMessages, sendMessage } from '../api/messages'
import { joinRoom } from '../api/rooms'
import { ErrorBanner } from '../components/ErrorBanner'
import { MessageInput } from '../components/MessageInput'
import { MessageList } from '../components/MessageList'
import { useAuth } from '../hooks/useAuth'
import type { Message } from '../types'

export function ChatPage() {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const parsedRoomId = Number(roomId)

  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadMessages = useCallback(async () => {
    if (!Number.isInteger(parsedRoomId) || parsedRoomId <= 0) {
      setError('Sala inválida')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      await joinRoom(parsedRoomId)
      const data = await listMessages(parsedRoomId)
      setMessages(data)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout()
        navigate('/', { replace: true })
        return
      }
      const message = err instanceof ApiError ? err.message : 'No se pudo cargar el chat'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [logout, navigate, parsedRoomId])

  useEffect(() => {
    void loadMessages()
  }, [loadMessages])

  async function handleSend(content: string) {
    const created = await sendMessage(parsedRoomId, content)
    setMessages((current) => [...current, created])
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <Link to="/rooms" className="text-sm text-blue-600 hover:text-blue-700">
              ← Salas
            </Link>
            <h1 className="text-xl font-semibold text-gray-900">Sala #{parsedRoomId}</h1>
          </div>
          <button
            type="button"
            onClick={() => void loadMessages()}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
          >
            Actualizar
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-6">
        <ErrorBanner message={error} />
        <MessageList messages={messages} currentUserId={user?.id ?? null} loading={loading} />
        <MessageInput onSend={handleSend} disabled={loading || Boolean(error)} />
      </main>
    </div>
  )
}
