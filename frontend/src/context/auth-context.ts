import { createContext } from 'react'
import type { StoredAuth, User } from '../types'

export interface AuthContextValue {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isCheckingSession: boolean
  login: (auth: StoredAuth) => void
  logout: () => void
}

export const AUTH_STORAGE_KEY = 'auth'

export const AuthContext = createContext<AuthContextValue | null>(null)

export function readStoredAuth(): StoredAuth | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY)
  if (!raw) return null

  try {
    return JSON.parse(raw) as StoredAuth
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return null
  }
}
