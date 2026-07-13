import { render, type RenderOptions } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import type { ReactElement, ReactNode } from 'react'
import { AuthContext, type AuthContextValue } from '../context/auth-context'
import type { Message, StoredAuth, User } from '../types'

export const userFixture: User = {
  id: 1,
  username: 'ada',
  created_at: '2026-07-13T00:00:00Z',
}

export const authFixture: StoredAuth = {
  token: 'token-123',
  user: userFixture,
}

export const messageFixture: Message = {
  id: 10,
  client_message_id: 'client-10',
  content: 'Hola',
  room_id: 2,
  sender_id: userFixture.id,
  sender_username: userFixture.username,
  created_at: '2026-07-13T00:01:00Z',
}

export function createAuthValue(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    token: null,
    isAuthenticated: false,
    isCheckingSession: false,
    login: vi.fn(),
    logout: vi.fn(),
    ...overrides,
  }
}

export function renderWithAuth(ui: ReactElement, auth: Partial<AuthContextValue> = {}) {
  return render(
    <AuthContext.Provider value={createAuthValue(auth)}>{ui}</AuthContext.Provider>,
  )
}

export function renderWithRouter(
  ui: ReactElement,
  {
    route = '/',
    ...options
  }: RenderOptions & { route?: string } = {},
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
  }

  return render(ui, { wrapper: Wrapper, ...options })
}

