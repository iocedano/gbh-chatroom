import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageInput } from './MessageInput'

describe('MessageInput', () => {
  it('trims and sends non-empty messages', async () => {
    const onSend = vi.fn().mockResolvedValue(undefined)
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Type a message...'), '  hello  ')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledWith('hello')
      expect(screen.getByPlaceholderText('Type a message...')).toHaveValue('')
    })
  })

  it('does not send blank messages', async () => {
    const onSend = vi.fn().mockResolvedValue(undefined)
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Type a message...'), '   ')

    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(onSend).not.toHaveBeenCalled()
  })

  it('shows send errors and keeps the message', async () => {
    const onSend = vi.fn().mockRejectedValue(new Error('Not connected'))
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Type a message...'), 'hello')
    await userEvent.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Not connected')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Type a message...')).toHaveValue('hello')
  })

  it('respects the disabled state', () => {
    render(<MessageInput onSend={vi.fn()} disabled />)

    expect(screen.getByPlaceholderText('Type a message...')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
    expect(screen.getByText('0/1000')).toBeInTheDocument()
  })
})

