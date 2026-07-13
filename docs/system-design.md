# System Design

This document describes the GBH Chat system design: components, data, flows, technical decisions, current limits, and evolution paths.

## System Goal

GBH Chat allows authenticated users to create rooms, join rooms, read history, and send realtime messages.

Covered functional requirements:

- Registration and login with JWT.
- Basic CRUD for users and rooms.
- Room membership with join/leave.
- Message history per room.
- Message sending over REST with idempotency.
- Message sending and broadcast over WebSocket.
- Rate limiting for auth and messages.
- Health checks for liveness and readiness.

Covered non-functional requirements:

- Layer separation.
- Versioned migrations.
- Automated backend tests.
- Environment-based configuration.
- Documented REST and WebSocket contracts.

## High-Level View

```mermaid
flowchart LR
  Browser["Browser / React App"]
  API["FastAPI API"]
  WS["WebSocket Endpoint"]
  DB[("Postgres")]
  Limiter["Rate Limiter"]

  Browser -- "REST JSON" --> API
  Browser -- "WS messages" --> WS
  API --> DB
  WS --> DB
  API --> Limiter
  WS --> Limiter
```

Components:

- React/Vite frontend: user interface, client-side auth, REST client, and WebSocket client.
- FastAPI REST: auth, users, rooms, membership, history, and REST message sending.
- FastAPI WebSocket: realtime room connection and message broadcast.
- Postgres: source of truth for users, rooms, memberships, and messages.
- Rate limiter: abuse protection through `limits`.

## Containers

```mermaid
flowchart TB
  subgraph Client
    UI["React App"]
  end

  subgraph Backend
    Routes["API Routes"]
    Services["Services"]
    Repositories["Repositories"]
    Sockets["Connection Manager"]
    Settings["Settings / Infra"]
  end

  subgraph Data
    Postgres[("Postgres")]
  end

  UI -- "HTTP REST" --> Routes
  UI -- "WebSocket" --> Routes
  Routes --> Services
  Services --> Repositories
  Repositories --> Postgres
  Services --> Sockets
  Routes --> Settings
  Services --> Settings
```

The API keeps a layered architecture:

```text
routes -> services -> repositories -> models
```

The frontend follows a similar separation:

```text
pages -> hooks -> api
pages -> components
```

References:

- [folder-architecture.md](folder-architecture.md)
- [design-patterns.md](design-patterns.md)

## Data Model

```mermaid
erDiagram
  USERS ||--o{ CHAT_ROOMS : creates
  USERS ||--o{ ROOM_MEMBERS : joins
  USERS ||--o{ MESSAGES : sends
  CHAT_ROOMS ||--o{ ROOM_MEMBERS : has
  CHAT_ROOMS ||--o{ MESSAGES : contains

  USERS {
    int id PK
    string username UK
    string password_hash
    datetime created_at
  }

  CHAT_ROOMS {
    int id PK
    string name
    int created_by FK
    datetime created_at
  }

  ROOM_MEMBERS {
    int id PK
    int room_id FK
    int user_id FK
    datetime joined_at
    datetime left_at
  }

  MESSAGES {
    int id PK
    string content
    int room_id FK
    int sender_id FK
    string idempotency_key
    string idempotency_request_hash
    datetime created_at
  }
```

Notes:

- `users.username` is unique.
- `messages.content` has a maximum of 1000 characters.
- `messages` has a unique constraint on `room_id + sender_id + idempotency_key`.
- `room_members.left_at = null` represents active membership.
- Deleting a room deletes its messages and memberships through ORM cascade.

## Main Flows

### Registration And Login

```mermaid
sequenceDiagram
  participant C as Client
  participant R as Auth Route
  participant S as User/Auth Service
  participant DB as Postgres

  C->>R: POST /auth/register or /auth/login
  R->>R: Check auth rate limit
  R->>S: register/authenticate
  S->>DB: Read/write user
  S-->>R: User
  R-->>C: access_token + user
```

Decisions:

- Passwords are received as plaintext only in the expected HTTPS request.
- The API stores `password_hash`, never plaintext passwords.
- JWT uses `sub` as `user_id`.
- In production, `JWT_SECRET_KEY` must be changed.

### Create Or Join Room

```mermaid
sequenceDiagram
  participant C as Client
  participant R as Rooms Route
  participant S as Chat Room Service
  participant DB as Postgres

  C->>R: POST /rooms or /rooms/{room_id}/join
  R->>R: Validate Bearer token
  R->>S: Create room or join room
  S->>DB: Persist room/member
  S-->>R: ChatRoomRead or RoomMemberRead
  R-->>C: JSON response
```

Decisions:

- Creating a room assigns `created_by` to the authenticated user.
- Join creates or reactivates membership depending on prior state.
- Leave sets `left_at`; it does not delete membership history.

### Load History

```mermaid
sequenceDiagram
  participant C as Client
  participant R as Messages Route
  participant S as Message Service
  participant DB as Postgres

  C->>R: GET /rooms/{room_id}/messages
  R->>R: Validate Bearer token
  R->>S: list_room_messages
  S->>DB: Check room exists
  S->>DB: Check active membership
  S->>DB: Query messages ordered by created_at, id
  DB-->>S: Messages
  S-->>R: MessageRead[]
  R-->>C: Messages with sender_username
```

Decisions:

- Only active members can read history.
- Ordering is ascending by `created_at` and `id`.
- `sender_username` is included to avoid extra frontend lookups.

### Send Message Over REST

```mermaid
sequenceDiagram
  participant C as Client
  participant R as Messages Route
  participant L as Rate Limiter
  participant S as Message Service
  participant DB as Postgres

  C->>R: POST /rooms/{room_id}/messages + Idempotency-Key
  R->>R: Validate Bearer token
  R->>L: Check rest:{room_id}:{user_id}
  L-->>R: Allowed
  R->>S: create_message
  S->>DB: Check room and active membership
  S->>DB: Lookup idempotency key
  alt Existing same request
    DB-->>S: Existing message
    S-->>R: Existing message
  else New message
    S->>DB: Insert message
    DB-->>S: Message
    S-->>R: Message
  else Same key, different content
    S-->>R: MessageIdempotencyConflictError
  end
  R-->>C: MessageRead or error
```

Decisions:

- `Idempotency-Key` is required for REST.
- The backend calculates the idempotency hash.
- Reusing a key with different content returns `409 Conflict`.
- The current rate limit check happens before the idempotent lookup.

Reference: [idempotency.md](idempotency.md).

### Send Message Over WebSocket

```mermaid
sequenceDiagram
  participant C as Client
  participant W as WebSocket Route
  participant RT as Realtime Service
  participant L as Rate Limiter
  participant DB as Postgres
  participant M as Connection Manager

  C->>W: WS /rooms/{room_id}/ws?token=...
  W->>RT: Authenticate token and check membership
  RT->>DB: Validate user and active membership
  W-->>C: Accept socket
  W->>M: Register connection in room

  C->>W: message.create
  W->>RT: Parse and validate event
  RT->>DB: Recheck active membership
  RT->>L: Check ws:{room_id}:{user_id}
  RT->>DB: Create idempotent message
  RT-->>W: message.created payload
  W->>M: Broadcast to room
  M-->>C: message.created
```

Decisions:

- Token is passed through the query string because browser WebSocket headers are limited.
- Membership is validated on connect and before every message.
- The client sends `client_message_id`; the backend derives `sender_id` from JWT.
- Broadcast is limited to `room_id`.
- If the room is deleted, active connections for that room are closed.

Reference: [websocket.md](websocket.md).

## Security

Current controls:

- JWT bearer for protected routes.
- `get_current_user` centralizes token validation.
- Password hashing before users are persisted.
- `JWT_SECRET_KEY` must differ from the default in production.
- CORS is configurable by environment.
- Active membership validation for reading/sending messages.
- The client cannot define `sender_id`.
- Rate limiting on registration, login, and message sending.
- Idempotency to avoid duplicates on retries.
- Logging for relevant failures without exposing secrets.

Production risks/pending work:

- Require HTTPS in front of the API and frontend.
- Use a strong JWT secret and planned rotation.
- Use Redis for rate limiting in multi-instance deployments.
- Review token expiration/revocation policies.
- Add centralized logs and metrics.

## Scalability And Availability

Current state:

- API is stateless for REST.
- WebSocket keeps in-memory state per process.
- Rate limiting uses `memory://` by default.
- Postgres is the source of truth.

Implications:

- Scaling REST horizontally is straightforward if all processes share the same DB.
- Scaling WebSocket requires sticky sessions or shared pub/sub for cross-instance broadcast.
- With `memory://`, each instance enforces rate limits independently.
- For production multi-instance deployments, use Redis for rate limiting and possibly realtime pub/sub.

Recommended evolution:

```text
Single instance
  -> API replicas behind load balancer
  -> Redis for rate limit
  -> Redis pub/sub or message broker for WebSocket broadcast
  -> Metrics/tracing/log aggregation
```

## Consistency And Concurrency

Messages:

- Persistence happens before broadcast.
- A message emitted through WebSocket already exists in DB.
- Idempotency protects REST and WebSocket retries.
- A unique DB constraint protects concurrent races with the same key.

Membership:

- Revalidated on every `message.create`.
- A user who leaves can no longer read/send.
- Open sockets lose access on the next send and receive close `1008`.

## Observability

Current:

- Structured logs for failed auth, idempotency conflicts, WebSocket errors, and DB health.
- `/health` for liveness without DB.
- `/health/db` for readiness with `SELECT 1`.

Recommended:

- Correlation/request IDs.
- Latency metrics by endpoint.
- Counters for `message.created`, WebSocket errors, and rate limits.
- Dashboard for active WebSocket connections by room/instance.

## Local Deployment

Docker Compose starts:

- `postgres`: Postgres 17.
- `api`: FastAPI, Alembic upgrade, and Uvicorn.
- `frontend`: Vite dev server.

```mermaid
flowchart LR
  Frontend["frontend:5173"] --> API["api:8000"]
  API --> Postgres["postgres:5432"]
```

The API container waits for the Postgres health check before starting.

## Current Tradeoffs

- Offset pagination is simple, but cursor pagination would be better for large history.
- In-memory WebSocket state is enough for one instance, but not for multi-instance broadcast.
- In-memory rate limiting is convenient in development, but Redis is needed with replicas.
- There is no optimistic UI for messages; this reduces duplicates, but can feel less instant.
- REST and WebSocket use separate rate limit counters for the same user/room.
- There is no message search or read receipts.

## References

- [folder-architecture.md](folder-architecture.md)
- [design-patterns.md](design-patterns.md)
- [websocket.md](websocket.md)
- [idempotency.md](idempotency.md)
- [rate-limiting.md](rate-limiting.md)
