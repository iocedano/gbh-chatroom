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
  content: string
  room_id: number
  sender_id: number
  created_at: string
}

export interface StoredAuth {
  token: string
  user: User
}
