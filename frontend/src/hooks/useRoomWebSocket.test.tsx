import { act, renderHook, waitFor } from '@testing-library/react'
import { messageFixture } from '../test/test-utils'
import { installMockWebSocket, MockWebSocket } from '../test/mocks/websocket'
import { useRoomWebSocket } from './useRoomWebSocket'

describe('useRoomWebSocket', () => {
  it('stays idle when disabled', () => {
    installMockWebSocket()

    const { result } = renderHook(() =>
      useRoomWebSocket({
        roomId: 1,
        token: 'token-123',
        enabled: false,
        onMessageCreated: vi.fn(),
      }),
    )

    expect(result.current.status).toBe('idle')
    expect(MockWebSocket.instances).toHaveLength(0)
  })

  it('connects and handles created messages', async () => {
    installMockWebSocket()
    const onMessageCreated = vi.fn()

    const { result } = renderHook(() =>
      useRoomWebSocket({
        roomId: 2,
        token: 'token-123',
        enabled: true,
        onMessageCreated,
      }),
    )

    expect(result.current.status).toBe('connecting')
    expect(MockWebSocket.instances[0].url).toBe(
      'ws://localhost:8000/rooms/2/ws?token=token-123',
    )

    act(() => {
      MockWebSocket.instances[0].open()
    })

    expect(result.current.status).toBe('connected')

    act(() => {
      MockWebSocket.instances[0].receive(
        JSON.stringify({ type: 'message.created', message: messageFixture }),
      )
    })

    expect(onMessageCreated).toHaveBeenCalledWith(messageFixture)
  })

  it('sends messages through the open socket', async () => {
    installMockWebSocket()
    vi.spyOn(crypto, 'randomUUID').mockReturnValue('00000000-0000-4000-8000-000000000001')

    const { result } = renderHook(() =>
      useRoomWebSocket({
        roomId: 2,
        token: 'token-123',
        enabled: true,
        onMessageCreated: vi.fn(),
      }),
    )

    act(() => {
      MockWebSocket.instances[0].open()
    })

    await act(async () => {
      await result.current.sendMessage('Hello')
    })

    expect(MockWebSocket.instances[0].sent).toEqual([
      JSON.stringify({
        type: 'message.create',
        client_message_id: '00000000-0000-4000-8000-000000000001',
        content: 'Hello',
      }),
    ])
  })

  it('throws when sending without an open socket', async () => {
    installMockWebSocket()

    const { result } = renderHook(() =>
      useRoomWebSocket({
        roomId: 2,
        token: 'token-123',
        enabled: true,
        onMessageCreated: vi.fn(),
      }),
    )

    await expect(result.current.sendMessage('Hello')).rejects.toThrow(
      'Real-time chat is not connected',
    )
  })

  it('surfaces server and access errors', async () => {
    installMockWebSocket()

    const { result } = renderHook(() =>
      useRoomWebSocket({
        roomId: 2,
        token: 'token-123',
        enabled: true,
        onMessageCreated: vi.fn(),
      }),
    )

    act(() => {
      MockWebSocket.instances[0].receive(
        JSON.stringify({
          type: 'error',
          error: { code: 'invalid_message', message: 'Invalid message' },
        }),
      )
    })

    expect(result.current.error).toBe('Invalid message')

    act(() => {
      MockWebSocket.instances[0].closeWith(1008)
    })

    await waitFor(() => {
      expect(result.current.status).toBe('disconnected')
      expect(result.current.error).toBe('Invalid message')
    })
  })
})
