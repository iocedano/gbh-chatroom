import { screen, waitFor } from '@testing-library/react'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MessageInput } from './MessageInput'

describe('MessageInput', () => {
  it('trims and sends non-empty messages', async () => {
    const onSend = vi.fn().mockResolvedValue(undefined)
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Escribe un mensaje...'), '  hola  ')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    await waitFor(() => {
      expect(onSend).toHaveBeenCalledWith('hola')
      expect(screen.getByPlaceholderText('Escribe un mensaje...')).toHaveValue('')
    })
  })

  it('does not send blank messages', async () => {
    const onSend = vi.fn().mockResolvedValue(undefined)
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Escribe un mensaje...'), '   ')

    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    expect(onSend).not.toHaveBeenCalled()
  })

  it('shows send errors and keeps the message', async () => {
    const onSend = vi.fn().mockRejectedValue(new Error('No conectado'))
    render(<MessageInput onSend={onSend} />)

    await userEvent.type(screen.getByPlaceholderText('Escribe un mensaje...'), 'hola')
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }))

    expect(await screen.findByText('No conectado')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Escribe un mensaje...')).toHaveValue('hola')
  })

  it('respects the disabled state', () => {
    render(<MessageInput onSend={vi.fn()} disabled />)

    expect(screen.getByPlaceholderText('Escribe un mensaje...')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled()
    expect(screen.getByText('0/1000')).toBeInTheDocument()
  })
})

