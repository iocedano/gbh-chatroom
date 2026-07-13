import type { Message } from '../types'

interface MessageListProps {
  messages: Message[]
  currentUserId: number | null
  loading?: boolean
}

function formatSender(senderId: number, currentUserId: number | null) {
  if (currentUserId !== null && senderId === currentUserId) {
    return 'Tú'
  }
  return `Usuario #${senderId}`
}

export function MessageList({ messages, currentUserId, loading = false }: MessageListProps) {
  if (loading) {
    return <p className="text-sm text-gray-500">Cargando mensajes...</p>
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center rounded-md border border-dashed border-gray-300 bg-white p-6 text-sm text-gray-500">
        Sé el primero en escribir en esta sala.
      </div>
    )
  }

  return (
    <ul className="flex-1 space-y-3 overflow-y-auto rounded-md border border-gray-200 bg-white p-4">
      {messages.map((message) => {
        const isOwn = currentUserId !== null && message.sender_id === currentUserId

        return (
          <li
            key={message.id}
            className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
              isOwn ? 'ml-auto bg-blue-100 text-blue-900' : 'mr-auto bg-gray-100 text-gray-900'
            }`}
          >
            <div className="mb-1 flex items-center gap-2 text-xs text-gray-500">
              <span className="font-medium">{formatSender(message.sender_id, currentUserId)}</span>
              <span>{new Date(message.created_at).toLocaleString()}</span>
            </div>
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          </li>
        )
      })}
    </ul>
  )
}
