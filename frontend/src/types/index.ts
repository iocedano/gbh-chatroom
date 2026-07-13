export interface User {
  id: number
  username: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface ChatRoom {
  id: number
  name: string
  created_by: number
  created_at: string
}

export interface Message {
  id: number
  client_message_id?: string
  content: string
  room_id: number
  sender_id: number
  sender_username?: string
  created_at: string
}

export interface StoredAuth {
  token: string
  user: User
}

export interface MessageCreatedEvent {
  type: 'message.created'
  message: Message
}

export interface WebSocketErrorEvent {
  type: 'error'
  error: {
    code: string
    message: string
    client_message_id?: string | null
  }
}

export type RoomWebSocketEvent = MessageCreatedEvent | WebSocketErrorEvent
