# GBH Chat

GBH Chat is a chat application with a FastAPI API, Postgres, Alembic migrations, a React/Vite frontend, and realtime messaging over WebSocket.

Spanish documentation lives in [docs/es/README.md](docs/es/README.md).

## Requirements

- Docker and Docker Compose to run the full stack.
- Python 3.13 if you run the API outside Docker.
- Node.js and npm if you run the frontend outside Docker.

## Quick Setup With Docker

From the repository root:

```sh
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:5432`

The API container runs migrations before starting Uvicorn.

## Local Setup

Start Postgres with Docker if you want to run the API and frontend on your machine:

```sh
docker compose up postgres
```

Local API:

```sh
cd app
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
uvicorn main:app --reload
```

Local frontend:

```sh
cd frontend
npm install
npm run dev
```

Useful frontend variables:

```text
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

If `VITE_WS_URL` is not set, the frontend derives `ws://` or `wss://` from `VITE_API_URL`.

## Environment Variables

The API reads variables from the environment or from `app/.env`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Environment: `development`, `staging`, or `production` |
| `DATABASE_URL` | `postgresql+psycopg2://chat_user:chat_password@localhost:5432/chat_app` | Postgres SQLAlchemy URL |
| `JWT_SECRET_KEY` | `change-me-in-development` | Secret used to sign JWTs. Must be changed in production |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | JSON or comma-separated list |
| `MESSAGE_RATE_LIMIT_MAX_EVENTS` | `20` | Messages allowed per window |
| `MESSAGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | Message rate limit window |
| `AUTH_RATE_LIMIT_MAX_EVENTS` | `10` | Register/login attempts per window and username |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Auth rate limit window |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | `limits` storage; use Redis for multi-instance deployments |
| `RATE_LIMIT_STRATEGY` | `moving-window` | `fixed-window`, `moving-window`, or `sliding-window-counter` |

## Migrations

Apply migrations from the repository root:

```sh
alembic -c app/alembic.ini upgrade head
```

Or from `app/`:

```sh
alembic -c alembic.ini upgrade head
```

Create a new migration after changing models:

```sh
cd app
alembic -c alembic.ini revision --autogenerate -m "describe_change"
```

Always review the generated file before applying it.

## Tests

Full backend suite:

```sh
cd app
pytest
```

You can also run a specific file:

```sh
cd app
pytest tests/test_messages.py
```

## Authentication

Protected routes use:

```http
Authorization: Bearer <access_token>
```

Common errors:

- `401 Unauthorized`: missing token, invalid token, or incorrect credentials.
- `422 Unprocessable Entity`: payload does not match the schema.
- `429 Too Many Requests`: auth or message limit exceeded.

## REST Contracts

Examples use ISO 8601 for `created_at` and `joined_at` fields.

### `POST /auth/register`

Auth: not required.

Body:

```json
{
  "username": "ana",
  "password": "password123"
}
```

Response `201`:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "ana",
    "created_at": "2026-07-13T15:10:30.123456Z"
  }
}
```

Errors: `409` if the username already exists, `422` for invalid payload, `429` for rate limiting.

### `POST /auth/login`

Auth: not required.

Body:

```json
{
  "username": "ana",
  "password": "password123"
}
```

Response `200`: same shape as registration.

Errors: `401` for invalid credentials, `422` for invalid payload, `429` for rate limiting.

### `GET /users/me`

Auth: required.

Response `200`:

```json
{
  "id": 1,
  "username": "ana",
  "created_at": "2026-07-13T15:10:30.123456Z"
}
```

Errors: `401`.

### `PATCH /users/me`

Auth: required.

Body:

```json
{
  "username": "ana2",
  "password": "new-password123"
}
```

Both fields are optional.

Response `200`: `UserRead`.

Errors: `401`, `409` if the username already exists, `422`.

### `DELETE /users/me`

Auth: required.

Response `204`: no body.

Errors: `401`.

### `GET /users`

Auth: required.

Query: `offset` default `0`, `limit` default `100`, max `100`.

Response `200`:

```json
[
  {
    "id": 1,
    "username": "ana",
    "created_at": "2026-07-13T15:10:30.123456Z"
  }
]
```

Errors: `401`, `422` for invalid query.

### `GET /users/{user_id}`

Auth: required.

Response `200`: `UserRead`.

Errors: `401`, `404` if the user does not exist.

### `POST /rooms`

Auth: required.

Body:

```json
{
  "name": "General"
}
```

Response `201`:

```json
{
  "id": 1,
  "name": "General",
  "created_by": 1,
  "created_at": "2026-07-13T15:10:30.123456Z"
}
```

Errors: `401`, `409` if a room with that name already exists, `422`.

### `GET /rooms`

Auth: required.

Query: `offset` default `0`, `limit` default `100`, max `100`.

Response `200`: list of `ChatRoomRead`.

Errors: `401`, `422`.

### `GET /rooms/{room_id}`

Auth: required.

Response `200`: `ChatRoomRead`.

Errors: `401`, `404`.

### `PATCH /rooms/{room_id}`

Auth: required. Only the creator can edit.

Body:

```json
{
  "name": "Equipo"
}
```

Response `200`: `ChatRoomRead`.

Errors: `401`, `403`, `404`, `409`, `422`.

### `DELETE /rooms/{room_id}`

Auth: required. Only the creator can delete.

Response `204`: no body. Active WebSocket connections for that room are closed.

Errors: `401`, `403`, `404`.

### `POST /rooms/{room_id}/join`

Auth: required.

Response `200`:

```json
{
  "id": 1,
  "room_id": 1,
  "user_id": 1,
  "joined_at": "2026-07-13T15:10:30.123456Z",
  "left_at": null
}
```

Errors: `401`, `400` if the user is already an active member, `404`.

### `POST /rooms/{room_id}/leave`

Auth: required.

Response `200`: `RoomMemberRead` with `left_at` set.

Errors: `401`, `400` if the user is not an active member, `404`.

### `POST /rooms/{room_id}/messages`

Auth: required. Active membership required.

Headers:

```http
Idempotency-Key: <unique-client-key>
```

Body:

```json
{
  "content": "Hola"
}
```

Response `201`:

```json
{
  "id": 123,
  "content": "Hola",
  "room_id": 1,
  "sender_id": 1,
  "sender_username": "ana",
  "created_at": "2026-07-13T15:10:30.123456Z"
}
```

Errors: `401`, `403` if the user is not an active member, `404`, `400` for an invalid idempotency key, `409` if the key is reused with different content, `422` if `Idempotency-Key` is missing or the payload is invalid, `429`.

### `GET /rooms/{room_id}/messages`

Auth: required. Active membership required.

Query: `offset` default `0`, `limit` default `100`, max `100`.

Response `200`: list of `MessageRead`; each message includes `sender_username`.

Errors: `401`, `403`, `404`, `422`.

### `GET /health`

Auth: not required.

Response `200`:

```json
{
  "status": "ok"
}
```

Lightweight liveness check; does not query the database.

### `GET /health/db`

Auth: not required.

Response `200`:

```json
{
  "database": "ok"
}
```

Readiness check; runs `SELECT 1`. If the database fails, the API returns a `5xx` error.

## End-To-End Message Flow

1. Create a user with `POST /auth/register` or authenticate with `POST /auth/login`.
2. Create a room with `POST /rooms` or join one with `POST /rooms/{room_id}/join`.
3. Load history with `GET /rooms/{room_id}/messages`.
4. Send over REST with `POST /rooms/{room_id}/messages` and a stable `Idempotency-Key` for retries.
5. Open `WS /rooms/{room_id}/ws?token=<access_token>`.
6. Send `message.create` events with `client_message_id`.
7. Listen for `message.created` events and deduplicate by `message.id`.
8. Handle WebSocket errors: `invalid_message`, `membership_required`, `rate_limit_exceeded`, and `client_message_id_conflict`.

Recommended client order: load history first and connect the WebSocket afterwards. Send new messages over WebSocket when connected; use REST as a fallback if the product needs it.

## WebSocket

Endpoint:

```text
WS /rooms/{room_id}/ws?token=<access_token>
```

Client-to-server event:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

Server-to-clients event:

```json
{
  "type": "message.created",
  "message": {
    "id": 123,
    "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
    "content": "Hola",
    "room_id": 1,
    "sender_id": 7,
    "sender_username": "ana",
    "created_at": "2026-07-13T15:10:30.123456Z"
  }
}
```

Full reference: [docs/websocket.md](docs/websocket.md).

## Technical Documentation

- [docs/websocket.md](docs/websocket.md): realtime contract, errors, and manual QA.
- [docs/idempotency.md](docs/idempotency.md): `Idempotency-Key` contract and deduplication.
- [docs/rate-limiting.md](docs/rate-limiting.md): configuration, scopes, and REST/WebSocket behavior.
- [docs/folder-architecture.md](docs/folder-architecture.md): folder structure and responsibilities.
- [docs/design-patterns.md](docs/design-patterns.md): design patterns used in the backend and frontend.
- [docs/system-design.md](docs/system-design.md): system design, flows, data, security, and scalability.
- [docs/es/README.md](docs/es/README.md): Spanish documentation entry point.

## Architecture

Main layers:

- `app/api/routes`: REST and WebSocket endpoints.
- `app/services`: business rules, auth, idempotency, membership, and realtime behavior.
- `app/repositories`: data access with SQLAlchemy.
- `app/models`: database models.
- `app/schemas`: Pydantic input and output contracts.
- `app/infra`: database, settings, and rate limiting.
- `app/sockets`: connection manager for room-scoped WebSocket connections.
- `frontend/src/api`: HTTP/WebSocket client.
- `frontend/src/hooks`: auth and realtime lifecycle.
- `frontend/src/pages` and `frontend/src/components`: UI.

Technical decisions:

- Auth uses JWT bearer tokens with `sub` as `user_id`.
- Passwords are stored only as hashes generated by the security layer.
- The backend derives identity from the token; the client never sends `sender_id`.
- REST messages require `Idempotency-Key`, scoped by `room_id + sender_id + key`.
- WebSocket messages use `client_message_id` and store it as the idempotency key.
- Rate limiting uses `limits` with `moving-window` by default.
- `GET /health` is liveness without DB; `GET /health/db` is readiness with DB.
- Persistence is versioned with Alembic and Postgres.
