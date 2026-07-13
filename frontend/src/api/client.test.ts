import { api } from './client'

function mockJsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
}

describe('api', () => {
  it('adds json content type and bearer token when available', async () => {
    localStorage.setItem('auth', JSON.stringify({ token: 'token-123' }))
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await api('/rooms', {
      method: 'POST',
      body: JSON.stringify({ name: 'general' }),
    })

    expect(fetchMock).toHaveBeenCalledWith('http://localhost:8000/rooms', {
      method: 'POST',
      body: JSON.stringify({ name: 'general' }),
      headers: expect.any(Headers),
    })

    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.get('Authorization')).toBe('Bearer token-123')
  })

  it('preserves explicit headers', async () => {
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    await api('/rooms/1/messages', {
      method: 'POST',
      headers: { 'Idempotency-Key': 'client-1' },
      body: JSON.stringify({ content: 'Hello' }),
    })

    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.get('Idempotency-Key')).toBe('client-1')
  })

  it('throws ApiError with response detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(mockJsonResponse({ detail: 'No autorizado' }, { status: 401 })),
    )

    await expect(api('/rooms')).rejects.toMatchObject({
      name: 'ApiError',
      message: 'No autorizado',
      status: 401,
    })
  })

  it('returns undefined for 204 responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))

    await expect(api('/rooms/1/leave', { method: 'POST' })).resolves.toBeUndefined()
  })

  it('ignores invalid stored auth json', async () => {
    localStorage.setItem('auth', '{bad json')
    const fetchMock = vi.fn().mockResolvedValue(mockJsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    await api('/rooms')

    const headers = fetchMock.mock.calls[0][1].headers as Headers
    expect(headers.has('Authorization')).toBe(false)
  })
})
