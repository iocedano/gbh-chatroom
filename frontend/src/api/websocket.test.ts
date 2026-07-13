import { buildRoomWebSocketUrl } from './websocket'

describe('buildRoomWebSocketUrl', () => {
  it('builds the room websocket url from the API url fallback', () => {
    expect(buildRoomWebSocketUrl(12, 'token 123')).toBe(
      'ws://localhost:8000/rooms/12/ws?token=token+123',
    )
  })
})

