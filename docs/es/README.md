# GBH Chat

La documentacion principal en ingles esta en [../../README.md](../../README.md).

GBH Chat es una app de chat con API FastAPI, Postgres, migraciones Alembic, frontend React/Vite y mensajeria en tiempo real por WebSocket.

## Requisitos

- Docker y Docker Compose para correr todo el stack.
- Python 3.13 si corres la API fuera de Docker.
- Node.js y npm si corres el frontend fuera de Docker.

## Setup Rapido Con Docker

Desde la raiz del repo:

```sh
docker compose up --build
```

Servicios:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- Postgres: `localhost:5432`

El contenedor de API ejecuta migraciones antes de iniciar Uvicorn.

## Setup Local

Levanta Postgres con Docker si quieres correr API y frontend en tu maquina:

```sh
docker compose up postgres
```

API local:

```sh
cd app
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic -c alembic.ini upgrade head
uvicorn main:app --reload
```

Frontend local:

```sh
cd frontend
npm install
npm run dev
```

Variables utiles del frontend:

```text
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

Si `VITE_WS_URL` no existe, el frontend deriva `ws://` o `wss://` desde `VITE_API_URL`.

## Variables De Entorno

La API lee variables desde el entorno o desde `app/.env`.

| Variable | Default | Uso |
| --- | --- | --- |
| `APP_ENV` | `development` | Entorno: `development`, `staging` o `production` |
| `DATABASE_URL` | `postgresql+psycopg2://chat_user:chat_password@localhost:5432/chat_app` | URL SQLAlchemy de Postgres |
| `JWT_SECRET_KEY` | `change-me-in-development` | Secreto para firmar JWT. Debe cambiar en produccion |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Minutos de vigencia del token |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Lista JSON o separada por comas |
| `MESSAGE_RATE_LIMIT_MAX_EVENTS` | `20` | Mensajes permitidos por ventana |
| `MESSAGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | Ventana de rate limit de mensajes |
| `AUTH_RATE_LIMIT_MAX_EVENTS` | `10` | Intentos de registro/login por ventana y username |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Ventana de rate limit de auth |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | Storage de `limits`; usa Redis en despliegues multi-instancia |
| `RATE_LIMIT_STRATEGY` | `moving-window` | `fixed-window`, `moving-window` o `sliding-window-counter` |

## Migraciones

Aplicar migraciones desde la raiz:

```sh
alembic -c app/alembic.ini upgrade head
```

O desde `app/`:

```sh
alembic -c alembic.ini upgrade head
```

Crear una migracion nueva despues de cambiar modelos:

```sh
cd app
alembic -c alembic.ini revision --autogenerate -m "describe_change"
```

Revisa siempre el archivo generado antes de aplicarlo.

## Tests

Suite backend completa:

```sh
cd app
pytest
```

Tambien puedes correr un archivo puntual:

```sh
cd app
pytest tests/test_messages.py
```

## Autenticacion

Las rutas protegidas usan:

```http
Authorization: Bearer <access_token>
```

Errores comunes:

- `401 Unauthorized`: token ausente, invalido o credenciales incorrectas.
- `422 Unprocessable Entity`: payload no cumple el schema.
- `429 Too Many Requests`: limite de auth o mensajes excedido.

## Contratos REST

Los ejemplos usan ISO 8601 para campos `created_at` y `joined_at`.

### `POST /auth/register`

Auth: no requerida.

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

Errores: `409` si el username ya existe, `422` por payload invalido, `429` por rate limit.

### `POST /auth/login`

Auth: no requerida.

Body:

```json
{
  "username": "ana",
  "password": "password123"
}
```

Response `200`: mismo shape que registro.

Errores: `401` por credenciales invalidas, `422` por payload invalido, `429` por rate limit.

### `GET /users/me`

Auth: requerida.

Response `200`:

```json
{
  "id": 1,
  "username": "ana",
  "created_at": "2026-07-13T15:10:30.123456Z"
}
```

Errores: `401`.

### `PATCH /users/me`

Auth: requerida.

Body:

```json
{
  "username": "ana2",
  "password": "new-password123"
}
```

Ambos campos son opcionales.

Response `200`: `UserRead`.

Errores: `401`, `409` si el username ya existe, `422`.

### `DELETE /users/me`

Auth: requerida.

Response `204`: sin body.

Errores: `401`.

### `GET /users`

Auth: requerida.

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

Errores: `401`, `422` por query invalido.

### `GET /users/{user_id}`

Auth: requerida.

Response `200`: `UserRead`.

Errores: `401`, `404` si no existe.

### `POST /rooms`

Auth: requerida.

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

Errores: `401`, `409` si ya existe una sala con ese nombre, `422`.

### `GET /rooms`

Auth: requerida.

Query: `offset` default `0`, `limit` default `100`, max `100`.

Response `200`: lista de `ChatRoomRead`.

Errores: `401`, `422`.

### `GET /rooms/{room_id}`

Auth: requerida.

Response `200`: `ChatRoomRead`.

Errores: `401`, `404`.

### `PATCH /rooms/{room_id}`

Auth: requerida. Solo el creador puede editar.

Body:

```json
{
  "name": "Equipo"
}
```

Response `200`: `ChatRoomRead`.

Errores: `401`, `403`, `404`, `409`, `422`.

### `DELETE /rooms/{room_id}`

Auth: requerida. Solo el creador puede eliminar.

Response `204`: sin body. Las conexiones WebSocket activas de esa sala se cierran.

Errores: `401`, `403`, `404`.

### `POST /rooms/{room_id}/join`

Auth: requerida.

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

Errores: `401`, `400` si ya es miembro activo, `404`.

### `POST /rooms/{room_id}/leave`

Auth: requerida.

Response `200`: `RoomMemberRead` con `left_at` informado.

Errores: `401`, `400` si no es miembro activo, `404`.

### `POST /rooms/{room_id}/messages`

Auth: requerida. Membresia activa requerida.

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

Errores: `401`, `403` si no es miembro activo, `404`, `400` por idempotency key invalida, `409` si la key se reutiliza con otro contenido, `422` si falta `Idempotency-Key` o el payload es invalido, `429`.

### `GET /rooms/{room_id}/messages`

Auth: requerida. Membresia activa requerida.

Query: `offset` default `0`, `limit` default `100`, max `100`.

Response `200`: lista de `MessageRead`; cada mensaje incluye `sender_username`.

Errores: `401`, `403`, `404`, `422`.

### `GET /health`

Auth: no requerida.

Response `200`:

```json
{
  "status": "ok"
}
```

Liveness liviano; no consulta la base de datos.

### `GET /health/db`

Auth: no requerida.

Response `200`:

```json
{
  "database": "ok"
}
```

Readiness; ejecuta `SELECT 1`. Si la base falla, la API responde error `5xx`.

## Flujo End-To-End De Mensajes

1. Crear usuario con `POST /auth/register` o autenticar con `POST /auth/login`.
2. Crear una sala con `POST /rooms` o unirse con `POST /rooms/{room_id}/join`.
3. Cargar historial con `GET /rooms/{room_id}/messages`.
4. Enviar por REST con `POST /rooms/{room_id}/messages` y un `Idempotency-Key` estable para retries.
5. Abrir `WS /rooms/{room_id}/ws?token=<access_token>`.
6. Enviar eventos `message.create` con `client_message_id`.
7. Escuchar eventos `message.created` y deduplicar por `message.id`.
8. Manejar errores WebSocket: `invalid_message`, `membership_required`, `rate_limit_exceeded` y `client_message_id_conflict`.

Orden recomendado para clientes: cargar historial primero y conectar el WebSocket despues. Enviar mensajes nuevos por WebSocket cuando el socket este conectado; usar REST como fallback si el producto lo necesita.

## WebSocket

Endpoint:

```text
WS /rooms/{room_id}/ws?token=<access_token>
```

Evento cliente-servidor:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

Evento servidor-clientes:

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

Referencia completa: [websocket.md](websocket.md).

## Documentacion Tecnica

- [websocket.md](websocket.md): contrato realtime, errores y QA manual.
- [idempotency.md](idempotency.md): contrato de `Idempotency-Key` y deduplicacion.
- [rate-limiting.md](rate-limiting.md): configuracion, scopes y comportamiento REST/WebSocket.
- [folder-architecture.md](folder-architecture.md): estructura de carpetas y responsabilidades.
- [design-patterns.md](design-patterns.md): patrones de diseno usados en backend y frontend.
- [system-design.md](system-design.md): diseno de sistema, flujos, datos, seguridad y escalabilidad.

## Arquitectura

Capas principales:

- `app/api/routes`: endpoints REST y WebSocket.
- `app/services`: reglas de negocio, auth, idempotencia, membresia y realtime.
- `app/repositories`: acceso a datos con SQLAlchemy.
- `app/models`: modelos de base de datos.
- `app/schemas`: contratos Pydantic de entrada y salida.
- `app/infra`: database, settings y rate limiting.
- `app/sockets`: connection manager para conexiones WebSocket por sala.
- `frontend/src/api`: cliente HTTP/WebSocket.
- `frontend/src/hooks`: auth y ciclo de vida realtime.
- `frontend/src/pages` y `frontend/src/components`: UI.

Decisiones tecnicas:

- Auth usa JWT bearer con `sub` como `user_id`.
- Passwords se almacenan solo como hash generado por la capa de seguridad.
- El backend deriva identidad desde el token; el cliente nunca envia `sender_id`.
- Mensajes REST requieren `Idempotency-Key`, con scope `room_id + sender_id + key`.
- Mensajes WebSocket usan `client_message_id` y lo almacenan como idempotency key.
- Rate limiting usa `limits` con estrategia `moving-window` por defecto.
- `GET /health` es liveness sin DB; `GET /health/db` es readiness con DB.
- Persistencia se versiona con Alembic y Postgres.
