import { api } from './client'
import type { ChatRoom } from '../types'

export function listRooms() {
  return api<ChatRoom[]>('/rooms')
}

export function createRoom(name: string) {
  return api<ChatRoom>('/rooms', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

export function joinRoom(roomId: number) {
  return api(`/rooms/${roomId}/join`, { method: 'POST' })
}

export function leaveRoom(roomId: number) {
  return api(`/rooms/${roomId}/leave`, { method: 'POST' })
}
