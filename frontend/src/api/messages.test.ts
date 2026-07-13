import { sendMessage } from './messages'

describe('messages api', () => {
  it('sends messages with an idempotency key', async () => {
    vi.spyOn(crypto, 'randomUUID').mockReturnValue('00000000-0000-4000-8000-000000000001')
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: 1, content: 'Hello' }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await sendMessage(7, 'Hello')

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/rooms/7/messages', {
      method: 'POST',
      headers: expect.any(Headers),
      body: JSON.stringify({ content: 'Hello' }),
    })

    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Idempotency-Key')).toBe('00000000-0000-4000-8000-000000000001')
    expect(headers.get('Content-Type')).toBe('application/json')
  })
})
