import { API_URL } from './client'

const WS_URL = import.meta.env.VITE_WS_URL

function apiUrlToWebSocketUrl(apiUrl: string) {
  const url = new URL(apiUrl)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  return url.toString().replace(/\/$/, '')
}

export function buildRoomWebSocketUrl(roomId: number, token: string) {
  const baseUrl = WS_URL ?? apiUrlToWebSocketUrl(API_URL)
  const url = new URL(`/rooms/${roomId}/ws`, baseUrl)
  url.searchParams.set('token', token)
  return url.toString()
}
