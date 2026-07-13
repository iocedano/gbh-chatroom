import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { listMessages } from '../api/messages'
import { joinRoom, leaveRoom } from '../api/rooms'
import { ErrorBanner } from '../components/ErrorBanner'
import { MessageInput } from '../components/MessageInput'
import { MessageList } from '../components/MessageList'
import { useAuth } from '../hooks/useAuth'
import { useRoomWebSocket } from '../hooks/useRoomWebSocket'
import type { Message } from '../types'

export function ChatPage() {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const { token, user, logout } = useAuth()
  const parsedRoomId = Number(roomId)

  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [leaving, setLeaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loadMessages = useCallback(async () => {
    if (!Number.isInteger(parsedRoomId) || parsedRoomId <= 0) {
      setError('Invalid room')
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
      const message = err instanceof ApiError ? err.message : 'Could not load chat'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [logout, navigate, parsedRoomId])

  useEffect(() => {
    void loadMessages()
  }, [loadMessages])

  const handleMessageCreated = useCallback((nextMessage: Message) => {
    setMessages((current) => {
      if (current.some((message) => message.id === nextMessage.id)) {
        return current
      }

      return [...current, nextMessage]
    })
  }, [])

  const {
    status: websocketStatus,
    error: websocketError,
    sendMessage: sendRealtimeMessage,
  } = useRoomWebSocket({
    roomId: parsedRoomId,
    token,
    enabled: !loading && !error && !leaving,
    onMessageCreated: handleMessageCreated,
  })

  async function handleSend(content: string) {
    await sendRealtimeMessage(content)
  }

  async function handleLeave() {
    if (!Number.isInteger(parsedRoomId) || parsedRoomId <= 0) return

    setLeaving(true)
    setError(null)

    try {
      await leaveRoom(parsedRoomId)
      navigate('/rooms', { replace: true })
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        logout()
        navigate('/', { replace: true })
        return
      }
      const message = err instanceof ApiError ? err.message : 'Could not leave room'
      setError(message)
    } finally {
      setLeaving(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <div className="flex items-center gap-3">
            <Link to="/rooms" className="text-sm text-blue-600 hover:text-blue-700">
              ← Rooms
            </Link>
            <h1 className="text-xl font-semibold text-gray-900">Room #{parsedRoomId}</h1>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void loadMessages()}
              disabled={loading || leaving}
              className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Refresh
            </button>
            <button
              type="button"
              onClick={() => void handleLeave()}
              disabled={loading || leaving}
              className="rounded-md border border-red-300 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {leaving ? 'Leaving...' : 'Leave room'}
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-4 py-6">
        <ErrorBanner message={error} />
        <ErrorBanner message={websocketError} />
        {!loading && !error && (
          <p className="text-xs text-gray-500">
            {websocketStatus === 'connected'
              ? 'Connected in real time'
              : websocketStatus === 'connecting'
                ? 'Connecting to real-time chat...'
                : 'Real-time chat disconnected'}
          </p>
        )}
        <MessageList messages={messages} currentUserId={user?.id ?? null} loading={loading} />
        <MessageInput
          onSend={handleSend}
          disabled={loading || leaving || Boolean(error) || websocketStatus !== 'connected'}
        />
      </main>
    </div>
  )
}
