# Rate Limiting for Message Sending

This project limits how fast a user can send messages in a room. The goal is to protect the API from spam and abusive high-volume sends without blocking normal chat usage.

The implementation lives in `app/infra/rate_limit.py`, wraps the `limits` library, and is applied to REST (`POST /rooms/{room_id}/messages`), WebSocket (`message.create`), and auth entry points.

## Algorithm

The backend uses the `limits` library with the **moving window** strategy by default.

For each scope key, the limiter:

1. Checks whether another event fits inside the configured window.
2. Records the event when it is allowed.
3. Rejects the event when the limit has already been reached.

Rejected requests include a `retry_after_seconds` value derived from the window reset time returned by `limits`.

```text
window_seconds = 60
max_events = 20

t=0s   -> allowed  (1/20)
t=3s   -> allowed  (2/20)
...
t=55s  -> allowed  (20/20)
t=56s  -> rejected (retry after oldest event leaves the window)
t=61s  -> allowed  (event at t=0s expired)
```

The default `memory://` storage is process-local and appropriate for development and single-instance deployments. See [Multi-Instance Deployments](#multi-instance-deployments) for production notes.

## Core Types

### `LimitsRateLimiter`

```python
message_rate_limiter = LimitsRateLimiter(
    max_events=settings.message_rate_limit_max_events,
    window_seconds=settings.message_rate_limit_window_seconds,
    storage_uri=settings.rate_limit_storage_uri,
    strategy=settings.rate_limit_strategy,
)
```

Public API:

- `check(key: str) -> RateLimitResult`: evaluate and consume one event for `key` when allowed.
- `reset() -> None`: recreate the configured storage and limiter. Used in tests.

`InMemoryRateLimiter` remains as a compatibility alias for older imports.

### `RateLimitResult`

- `allowed: bool`: whether the request may proceed.
- `retry_after_seconds: int`: seconds to wait before retrying when `allowed` is `False`.

## Configuration

Environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `MESSAGE_RATE_LIMIT_MAX_EVENTS` | `20` | Maximum message sends per window |
| `MESSAGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | Message rate limit window size in seconds |
| `AUTH_RATE_LIMIT_MAX_EVENTS` | `10` | Maximum register/login attempts per window and username |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Auth rate limit window size in seconds |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | `limits` storage URI. Use `redis://...` for shared production limits |
| `RATE_LIMIT_STRATEGY` | `moving-window` | One of `fixed-window`, `moving-window`, or `sliding-window-counter` |

Settings are defined in `app/infra/settings.py` and read once at process startup.

## Scope Keys

Rate limits are scoped **per user and per room**. The limiter key format depends on the transport:

```text
REST:      rest:{room_id}:{user_id}
WebSocket: ws:{room_id}:{user_id}
Register:  register:{username}
Login:     login:{username}
```

This means:

- The same user has independent limits in different rooms.
- Different users in the same room have independent limits.
- REST and WebSocket traffic use separate counters, even for the same user and room.
- Register and login attempts use separate counters per username.

## REST Behavior

Endpoint:

```http
POST /rooms/{room_id}/messages
```

When the limit is exceeded:

- Status: `429 Too Many Requests`
- Body: `{"detail": "Message rate limit exceeded"}`
- Header: `Retry-After: <seconds>`

Implementation: `app/api/routes/messages.py`

## WebSocket Behavior

Event:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

When the limit is exceeded:

- The message is not persisted.
- The server emits an `error` event with `code = "rate_limit_exceeded"`.
- The socket stays open.

```json
{
  "type": "error",
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Message rate limit exceeded",
    "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c"
  }
}
```

Implementation:

- Transport layer: `app/api/routes/websocket.py`
- Domain handling: `app/services/realtime.py`

## Request Order

Current order for REST message creation:

```text
1. Authenticate user
2. Check rate limit
3. Validate room, membership, and idempotency inside message service
4. Create or return existing message
```

Current order for WebSocket `message.create`:

```text
1. Authenticate user
2. Validate active room membership
3. Check rate limit
4. Validate payload and idempotency
5. Create message and broadcast
```

## Relationship With Idempotency

Rate limiting and idempotency solve different problems:

- **Rate limiting** protects the API from abusive volume.
- **Idempotency** protects legitimate retries from creating duplicate messages.

See [docs/idempotency.md](idempotency.md) for the full idempotency contract.

Important behavior today:

- A retry with the same `Idempotency-Key` or `client_message_id` still consumes rate limit budget if it reaches the limiter before the idempotent lookup.
- If you want retries of the same logical operation to bypass rate limiting, move the limiter check after the idempotent "return existing message" path.

Recommended order when both protections are active:

```text
1. Authenticate user
2. Validate room exists
3. Validate active room membership
4. Validate idempotency key / client_message_id
5. If the existing message matches, return it without consuming rate limit
6. If this is a new message, apply rate limit
7. Create message
```

## Multi-Instance Deployments

With `RATE_LIMIT_STORAGE_URI=memory://`, each application instance enforces its own limit, so effective throughput scales with the number of replicas.

For shared limits across instances, configure Redis using the same scope key format:

```text
RATE_LIMIT_STORAGE_URI=redis://redis:6379/0

rest:{room_id}:{user_id}
ws:{room_id}:{user_id}
register:{username}
login:{username}
```

Keep the `check(key) -> RateLimitResult` interface so route handlers do not need to change.

## Extending the Pattern

To rate limit a new operation:

1. Create one `LimitsRateLimiter` instance per limit policy.
2. Choose a stable scope key that identifies the protected actor and resource.
3. Call `check(key)` at the route or service boundary.
4. Map `RateLimitResult` to the transport response:
   - REST: `429` + `Retry-After`
   - WebSocket: `error` event with a stable `code`

Example scope keys:

```text
login:{username}
invite:{room_id}:{user_id}
```

## Testing

Tests override the shared limiter instances to keep scenarios deterministic:

```python
messages_route.message_rate_limiter.max_events = 2
messages_route.message_rate_limiter.window_seconds = 60
messages_route.message_rate_limiter.reset()
```

Relevant tests live in `app/tests/test_p1_backend.py`:

- `test_rest_message_rate_limit_returns_429`
- `test_websocket_message_rate_limit_returns_error_event`

## Source Files

| File | Responsibility |
| --- | --- |
| `app/infra/rate_limit.py` | `LimitsRateLimiter` and `RateLimitResult` |
| `app/infra/settings.py` | Environment configuration |
| `app/api/routes/auth.py` | Auth rate limiting |
| `app/api/routes/messages.py` | REST rate limiting |
| `app/api/routes/websocket.py` | WebSocket rate limiting wiring |
| `app/services/realtime.py` | WebSocket domain-level limit check |
