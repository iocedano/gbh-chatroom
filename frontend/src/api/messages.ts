import { api } from './client'
import type { Message } from '../types'

export function listMessages(roomId: number) {
  return api<Message[]>(`/rooms/${roomId}/messages`)
}

export function sendMessage(roomId: number, content: string) {
  return api<Message>(`/rooms/${roomId}/messages`, {
    method: 'POST',
    headers: {
      'Idempotency-Key': crypto.randomUUID(),
    },
    body: JSON.stringify({ content }),
  })
}
