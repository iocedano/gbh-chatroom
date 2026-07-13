import { act, render, screen, waitFor } from '@testing-library/react'
import { getCurrentUser } from '../api/users'
import { authFixture, userFixture } from '../test/test-utils'
import { AuthProvider } from './AuthProvider'
import { AUTH_STORAGE_KEY } from './auth-context'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../api/client'

vi.mock('../api/users', () => ({
  getCurrentUser: vi.fn(),
}))

function AuthProbe() {
  const auth = useAuth()

  return (
    <div>
      <span data-testid="username">{auth.user?.username ?? 'anon'}</span>
      <span data-testid="token">{auth.token ?? 'no-token'}</span>
      <span data-testid="checking">{String(auth.isCheckingSession)}</span>
      <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
      <button type="button" onClick={() => auth.login(authFixture)}>
        login
      </button>
      <button type="button" onClick={auth.logout}>
        logout
      </button>
    </div>
  )
}

describe('AuthProvider', () => {
  it('validates and refreshes stored auth', async () => {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authFixture))
    vi.mocked(getCurrentUser).mockResolvedValue({ ...userFixture, username: 'ada-updated' })

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    expect(screen.getByTestId('checking')).toHaveTextContent('true')

    await waitFor(() => {
      expect(screen.getByTestId('checking')).toHaveTextContent('false')
      expect(screen.getByTestId('username')).toHaveTextContent('ada-updated')
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    expect(JSON.parse(localStorage.getItem(AUTH_STORAGE_KEY) ?? '{}')).toMatchObject({
      token: authFixture.token,
      user: { username: 'ada-updated' },
    })
  })

  it('clears stored auth on unauthorized validation', async () => {
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authFixture))
    vi.mocked(getCurrentUser).mockRejectedValue(new ApiError('Unauthorized', 401))

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
      expect(screen.getByTestId('token')).toHaveTextContent('no-token')
    })

    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull()
  })

  it('persists login and clears logout', async () => {
    vi.mocked(getCurrentUser).mockResolvedValue(userFixture)

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await act(async () => {
      screen.getByRole('button', { name: 'login' }).click()
    })

    expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBe(JSON.stringify(authFixture))

    await act(async () => {
      screen.getByRole('button', { name: 'logout' }).click()
    })

    expect(screen.getByTestId('authenticated')).toHaveTextContent('false')
    expect(localStorage.getItem(AUTH_STORAGE_KEY)).toBeNull()
  })
})

