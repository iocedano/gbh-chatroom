import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError } from '../api/client'
import { getCurrentUser } from '../api/users'
import { AUTH_STORAGE_KEY, AuthContext, readStoredAuth, type AuthContextValue } from './auth-context'
import type { StoredAuth } from '../types'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<StoredAuth | null>(() => readStoredAuth())
  const [isCheckingSession, setIsCheckingSession] = useState(() => auth !== null)
  const authToken = auth?.token ?? null

  const login = useCallback((nextAuth: StoredAuth) => {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextAuth))
    setAuth(nextAuth)
    setIsCheckingSession(false)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    setAuth(null)
    setIsCheckingSession(false)
  }, [])

  useEffect(() => {
    if (authToken === null) {
      setIsCheckingSession(false)
      return
    }

    let isActive = true
    setIsCheckingSession(true)

    getCurrentUser()
      .then((user) => {
        if (!isActive) return

        const nextAuth = { token: authToken, user }
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(nextAuth))
        setAuth(nextAuth)
      })
      .catch((err) => {
        if (!isActive) return

        if (err instanceof ApiError && (err.status === 401 || err.status === 403)) {
          localStorage.removeItem(AUTH_STORAGE_KEY)
          setAuth(null)
        }
      })
      .finally(() => {
        if (isActive) {
          setIsCheckingSession(false)
        }
      })

    return () => {
      isActive = false
    }
  }, [authToken])

  const value = useMemo<AuthContextValue>(
    () => ({
      user: auth?.user ?? null,
      token: auth?.token ?? null,
      isAuthenticated: auth !== null,
      isCheckingSession,
      login,
      logout,
    }),
    [auth, isCheckingSession, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
