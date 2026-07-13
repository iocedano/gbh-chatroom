# Design Patterns

This document describes the design patterns used in GBH Chat. They are not academic patterns applied ceremonially; they are practical conventions that keep the code easy to change.

## Layered Architecture

The backend uses layers with separate responsibilities:

```text
API routes -> services -> repositories -> models
```

Current usage:

- `api/routes/*`: receives requests, validates auth through dependencies, calls services, and maps errors to HTTP/WebSocket.
- `services/*`: contains business rules and orchestration.
- `repositories/*`: encapsulates SQLAlchemy queries.
- `models/*`: defines persistence.

Benefits:

- Endpoints stay thin.
- Business rules can be tested without coupling them to transport.
- Query changes do not force changes in HTTP handlers.

## Service Layer

Services represent application use cases.

Examples:

- `services/users.py`: registration, login, and user updates.
- `services/chat_rooms.py`: room CRUD and membership.
- `services/messages.py`: permissions, idempotency, and message persistence.
- `services/realtime.py`: WebSocket event contract and realtime validations.

Convention:

- Routes should not implement complex permission rules.
- Services raise domain exceptions, such as `MessagePermissionError`.
- Routes translate those exceptions into transport responses.

## Repository Pattern

Repositories concentrate data access.

Examples:

- `repositories/messages.py` contains `create_message`, `get_message_by_idempotency_key`, and `list_room_messages`.
- `repositories/room_members.py` contains active membership queries.

Convention:

- Repositories receive an explicit `Session`.
- Repositories return models or `None`.
- Repositories do not decide whether a user can perform an action; that lives in services.

## Dependency Injection

FastAPI provides dependencies for cross-cutting resources.

Current usage:

- `get_db` injects the database session.
- `get_current_user` validates JWT and returns the authenticated user.
- Routers declare dependencies with `Depends`.

Benefits:

- Smaller handlers.
- Tests can replace dependencies.
- Auth and DB wiring are not duplicated in every endpoint.

## DTO / Schema Pattern

Pydantic is used as the boundary between external payloads and internal objects.

Current usage:

- `UserCreate`, `UserLogin`, `UserRead`.
- `ChatRoomCreate`, `ChatRoomUpdate`, `ChatRoomRead`.
- `MessageCreate`, `MessageRead`.
- `RoomMemberRead`.

Convention:

- Input schemas validate length and basic normalization.
- Output schemas do not expose password hashes or sensitive internal fields.
- SQLAlchemy models are not returned without passing through `response_model`.

## Domain Exceptions + Transport Mapping

Services raise errors with domain meaning. Routes decide how to represent them in HTTP or WebSocket.

REST example:

```text
MessagePermissionError -> 403 Forbidden
MessageRoomNotFoundError -> 404 Not Found
MessageIdempotencyConflictError -> 409 Conflict
```

WebSocket example:

```text
membership_required -> error event + close 1008
rate_limit_exceeded -> error event, socket remains open
invalid_message -> error event
```

Benefits:

- The domain is not coupled to FastAPI.
- The same business case can be mapped differently in REST and WebSocket.

## Lightweight Unit Of Work

The SQLAlchemy session travels explicitly from routes to services and repositories.

Current usage:

- `create_message` does `db.add`, `db.commit`, and `db.refresh` in the repository.
- Services handle `IntegrityError` when they need to resolve idempotency races.

This project does not use a dedicated `UnitOfWork` class because the current scope is small. If more complex multi-repository transactions appear, a formal abstraction may make sense.

## Idempotency Pattern

REST message sending requires `Idempotency-Key`.

Scope:

```text
room_id + sender_id + idempotency_key
```

The backend calculates a hash of the normalized request. If the same key is used with the same content, it returns the existing message. If the key is used with different content, it returns a conflict.

WebSocket reuses the same pattern with `client_message_id`.

Reference: [idempotency.md](idempotency.md).

## Rate Limiter Adapter

`infra/rate_limit.py` wraps the `limits` library behind a small interface:

```text
check(key) -> RateLimitResult
```

Current usage:

- Auth: scoped by username and action.
- REST messages: scoped by user and room.
- WebSocket messages: scoped by user and room.

Benefits:

- Routes do not know `limits` internals.
- Changing storage or strategy does not require rewriting handlers.

Reference: [rate-limiting.md](rate-limiting.md).

## Connection Manager

Active WebSocket connections are managed by room.

Responsibilities:

- Register connections by `room_id`.
- Remove connections on disconnect.
- Broadcast only to the correct room.
- Close active sockets when a room is deleted.

This pattern prevents the WebSocket route from maintaining global structures directly.

## Optimistic-Safe Realtime Flow

The current realtime flow avoids optimistic UI for the first version:

```text
client sends message.create
backend validates and persists
backend emits message.created
frontend adds message after receiving message.created
```

Benefits:

- The frontend shows messages confirmed by persistence.
- Duplicates are reduced.
- Deduplication can use `message.id`.

## React Hooks For Side Effects

The frontend concentrates effects in hooks.

Current usage:

- `useAuth` manages authentication state.
- `useRoomWebSocket` manages connection, events, errors, and realtime sending.

Convention:

- Pages orchestrate hooks and API clients.
- Components receive data and callbacks.
- WebSocket details are not mixed into render components.

## API Client Boundary

The frontend centralizes backend calls in `frontend/src/api`.

Current usage:

- `auth.ts`: login/register.
- `rooms.ts`: CRUD and membership.
- `messages.ts`: history and REST sending.
- `websocket.ts`: WebSocket URL construction.
- `client.ts`: base HTTP client.

Benefits:

- URL, header, and parsing changes stay in one place.
- Components and pages do not repeat fetch details.

## Configuration Object

Backend configuration lives in `Settings`, based on `pydantic-settings`.

Current usage:

- Typed environment variables.
- Local defaults.
- Secret validation in production.
- Flexible `CORS_ORIGINS` parsing.

Benefits:

- Centralized configuration.
- Configuration errors fail at startup.
- Defaults support local development.

## Testing Patterns

The backend suite uses fixtures to isolate scenarios.

Applied patterns:

- Isolated test database.
- Helpers to create users, rooms, memberships, messages, and tokens.
- Observable contract tests: status codes, payloads, and WebSocket events.
- Explicit rate limiter resets in tests that modify limits.

Goal:

- Test public behavior and business rules without depending on external data.
