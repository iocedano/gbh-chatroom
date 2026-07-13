import { useCallback, useEffect, useRef, useState } from 'react'
import { buildRoomWebSocketUrl } from '../api/websocket'
import type { Message, RoomWebSocketEvent } from '../types'

type RoomWebSocketStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error'

interface UseRoomWebSocketOptions {
  roomId: number
  token: string | null
  enabled: boolean
  onMessageCreated: (message: Message) => void
}

interface UseRoomWebSocketResult {
  status: RoomWebSocketStatus
  error: string | null
  sendMessage: (content: string) => Promise<void>
}

function parseRoomWebSocketEvent(data: string): RoomWebSocketEvent | null {
  try {
    const event = JSON.parse(data) as RoomWebSocketEvent
    if (event.type === 'message.created' || event.type === 'error') {
      return event
    }
  } catch {
    return null
  }

  return null
}

export function useRoomWebSocket({
  roomId,
  token,
  enabled,
  onMessageCreated,
}: UseRoomWebSocketOptions): UseRoomWebSocketResult {
  const socketRef = useRef<WebSocket | null>(null)
  const onMessageCreatedRef = useRef(onMessageCreated)
  const [status, setStatus] = useState<RoomWebSocketStatus>('idle')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    onMessageCreatedRef.current = onMessageCreated
  }, [onMessageCreated])

  useEffect(() => {
    if (!enabled || !token || !Number.isInteger(roomId) || roomId <= 0) {
      setStatus('idle')
      return
    }

    setStatus('connecting')
    setError(null)

    const socket = new WebSocket(buildRoomWebSocketUrl(roomId, token))
    socketRef.current = socket

    socket.addEventListener('open', () => {
      setStatus('connected')
      setError(null)
    })

    socket.addEventListener('message', (messageEvent) => {
      if (typeof messageEvent.data !== 'string') return

      const event = parseRoomWebSocketEvent(messageEvent.data)
      if (event === null) return

      if (event.type === 'message.created') {
        onMessageCreatedRef.current(event.message)
        return
      }

      setError(event.error.message)
    })

    socket.addEventListener('error', () => {
      setStatus('error')
      setError('No se pudo conectar al chat en tiempo real')
    })

    socket.addEventListener('close', (event) => {
      if (socketRef.current === socket) {
        socketRef.current = null
      }

      setStatus((currentStatus) => (currentStatus === 'error' ? currentStatus : 'disconnected'))

      if (event.code === 1008) {
        setError((currentError) => currentError ?? 'No tienes acceso activo a esta sala')
      }
    })

    return () => {
      if (socketRef.current === socket) {
        socketRef.current = null
      }

      socket.close()
    }
  }, [enabled, roomId, token])

  const sendMessage = useCallback(async (content: string) => {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      throw new Error('El chat en tiempo real no está conectado')
    }

    socket.send(
      JSON.stringify({
        type: 'message.create',
        client_message_id: crypto.randomUUID(),
        content,
      }),
    )
  }, [])

  return { status, error, sendMessage }
}
