type Listener = (event: Event) => void

export class MockWebSocket {
  static instances: MockWebSocket[] = []
  static readonly CONNECTING = 0
  static readonly OPEN = 1
  static readonly CLOSING = 2
  static readonly CLOSED = 3

  readonly url: string
  readyState = MockWebSocket.CONNECTING
  sent: string[] = []
  private listeners = new Map<string, Listener[]>()

  constructor(url: string) {
    this.url = url
    MockWebSocket.instances.push(this)
  }

  addEventListener(type: string, listener: Listener) {
    const listeners = this.listeners.get(type) ?? []
    listeners.push(listener)
    this.listeners.set(type, listeners)
  }

  send(data: string) {
    this.sent.push(data)
  }

  close() {
    this.readyState = MockWebSocket.CLOSED
    this.dispatch('close', new CloseEvent('close'))
  }

  open() {
    this.readyState = MockWebSocket.OPEN
    this.dispatch('open', new Event('open'))
  }

  receive(data: unknown) {
    this.dispatch('message', new MessageEvent('message', { data }))
  }

  fail() {
    this.dispatch('error', new Event('error'))
  }

  closeWith(code: number) {
    this.readyState = MockWebSocket.CLOSED
    this.dispatch('close', new CloseEvent('close', { code }))
  }

  private dispatch(type: string, event: Event) {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(event)
    }
  }
}

export function installMockWebSocket() {
  MockWebSocket.instances = []
  vi.stubGlobal('WebSocket', MockWebSocket)
}
