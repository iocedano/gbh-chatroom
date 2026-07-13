import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiError } from '../api/client'
import { renderWithAuth, userFixture } from '../test/test-utils'
import { LoginForm } from './LoginForm'
import { login as loginRequest } from '../api/auth'

vi.mock('../api/auth', () => ({
  login: vi.fn(),
}))

describe('LoginForm', () => {
  it('logs in with the returned token and user', async () => {
    vi.mocked(loginRequest).mockResolvedValue({
      access_token: 'token-123',
      token_type: 'bearer',
      user: userFixture,
    })
    const login = vi.fn()

    renderWithAuth(<LoginForm />, { login })

    await userEvent.type(screen.getByLabelText('Username'), 'ada')
    await userEvent.type(screen.getByLabelText('Password'), 'password123')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    await waitFor(() => {
      expect(loginRequest).toHaveBeenCalledWith('ada', 'password123')
      expect(login).toHaveBeenCalledWith({ token: 'token-123', user: userFixture })
    })
  })

  it('shows API errors', async () => {
    vi.mocked(loginRequest).mockRejectedValue(new ApiError('Invalid credentials', 401))

    renderWithAuth(<LoginForm />)

    await userEvent.type(screen.getByLabelText('Username'), 'ada')
    await userEvent.type(screen.getByLabelText('Password'), 'bad-password')
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('Invalid credentials')).toBeInTheDocument()
  })
})

