# Folder Architecture

This document describes how the repository is organized and what each folder is responsible for.

## Overview

```text
.
|-- app/                 # FastAPI backend
|-- frontend/            # React/Vite frontend
|-- docs/                # Technical documentation in English
|-- docs/es/             # Spanish documentation
|-- docker-compose.yml   # Local stack with Postgres, API, and frontend
|-- README.md            # Setup, REST contracts, and architecture summary
`-- TODO_BACKEND.md      # Backend technical checklist
```

The main split is by runtime:

- `app/` contains the API, backend domain logic, persistence, migrations, and tests.
- `frontend/` contains the browser application and its HTTP/WebSocket clients.
- `docs/` contains deeper technical references than the README.
- `docs/es/` contains the Spanish documentation.

## Backend: `app/`

```text
app/
|-- api/
|   |-- dependencies.py
|   |-- middleware/
|   `-- routes/
|-- alembic/
|   `-- versions/
|-- infra/
|-- models/
|-- repositories/
|-- schemas/
|-- services/
|-- sockets/
|-- tests/
|-- main.py
|-- requirements.txt
`-- alembic.ini
```

### `app/main.py`

FastAPI entry point.

Responsibilities:

- Create the `FastAPI` instance.
- Configure CORS.
- Register REST and WebSocket routers.
- Expose health checks.

### `app/api/`

HTTP/WebSocket transport layer.

- `routes/`: REST and WebSocket endpoints. They translate requests into service calls and map domain exceptions to HTTP codes or WebSocket events.
- `dependencies.py`: shared FastAPI dependencies such as `get_current_user`.
- `middleware/`: reusable HTTP middleware when the project needs it.

Practical rule: this layer should stay thin. Transport validation and error mapping live here; business rules live in `services/`.

### `app/services/`

Application/domain layer.

Responsibilities:

- Auth, hashing, JWT creation, and token validation.
- Room, membership, and permission rules.
- Message creation and listing.
- Idempotency.
- Realtime WebSocket flow.
- Translation of domain cases into specific exceptions.

Services orchestrate repositories and encapsulate product decisions. For example, `messages.py` validates membership, builds the idempotency hash, and handles conflicts before persisting.

### `app/repositories/`

Data access layer.

Responsibilities:

- Encapsulate SQLAlchemy queries.
- Create, read, update, and list models.
- Keep persistence details out of routes and services.

Practical rule: repositories should not decide permissions or business rules. They receive parameters already validated by services.

### `app/models/`

SQLAlchemy models.

Responsibilities:

- Define tables, columns, relationships, indexes, and constraints.
- Represent state persisted in Postgres.

Models are the source for Alembic autogeneration, although every generated migration must be reviewed.

### `app/schemas/`

Pydantic input/output schemas.

Responsibilities:

- Validate reusable REST and WebSocket payloads.
- Normalize simple fields, such as `content.strip()` or room names.
- Define public responses without exposing secrets or hashes.

### `app/infra/`

Shared infrastructure.

Responsibilities:

- Configuration (`settings.py`).
- Database connection and sessions (`database.py`).
- Rate limiting (`rate_limit.py`).

This folder contains cross-cutting technical integrations, not entity-specific rules.

### `app/sockets/`

State and utilities for WebSocket connections.

Responsibilities:

- Group active connections by `room_id`.
- Broadcast within a room.
- Close connections for a deleted room.

### `app/alembic/`

Database migrations.

- `versions/`: versioned schema change history.
- `env.py`: Alembic configuration for loading models and the database URL.

### `app/tests/`

Backend test suite.

Responsibilities:

- Tests for auth, users, rooms, memberships, messages, idempotency, rate limiting, and WebSocket.
- Database fixtures and entity helpers.
- Validate public contracts and error cases.

## Frontend: `frontend/`

```text
frontend/
|-- public/
|-- src/
|   |-- api/
|   |-- assets/
|   |-- components/
|   |-- hooks/
|   |-- pages/
|   |-- types/
|   |-- App.tsx
|   |-- index.css
|   `-- main.tsx
|-- package.json
`-- vite.config.ts
```

### `frontend/src/api/`

Integration clients for the backend.

Responsibilities:

- Build HTTP requests.
- Centralize `VITE_API_URL`.
- Build WebSocket URLs.
- Keep fetch details out of components.

### `frontend/src/hooks/`

Reusable state and effects.

Responsibilities:

- Client-side auth.
- Per-room WebSocket lifecycle.
- Sending and receiving realtime events.

### `frontend/src/pages/`

Route-connected screens.

Responsibilities:

- Orchestrate the data needed by a view.
- Combine hooks, API clients, and components.
- Handle page-level loading and error states.

### `frontend/src/components/`

Reusable or screen-specific UI components.

Responsibilities:

- Render forms, lists, banners, and inputs.
- Emit callbacks to pages/hooks.
- Keep visual logic separate from HTTP integrations.

### `frontend/src/types/`

Shared TypeScript types.

Responsibilities:

- Frontend contracts for users, rooms, messages, and WebSocket events.
- Reduce duplication across API clients, hooks, and components.
