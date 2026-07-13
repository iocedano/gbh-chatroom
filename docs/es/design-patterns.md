# Design Patterns

Este documento describe los patrones de diseno usados en GBH Chat. No son patrones academicos aplicados por ceremonia; son convenciones practicas para mantener el codigo facil de cambiar.

## Layered Architecture

El backend usa capas con responsabilidades separadas:

```text
API routes -> services -> repositories -> models
```

Uso actual:

- `api/routes/*`: recibe requests, valida auth con dependencias, llama servicios y mapea errores a HTTP/WebSocket.
- `services/*`: contiene reglas de negocio y orquestacion.
- `repositories/*`: encapsula queries SQLAlchemy.
- `models/*`: define persistencia.

Beneficio:

- Los endpoints se mantienen delgados.
- Las reglas de negocio se pueden testear sin acoplarlas al transporte.
- Cambios en queries no obligan a tocar handlers HTTP.

## Service Layer

Los servicios representan casos de uso de la aplicacion.

Ejemplos:

- `services/users.py`: registro, login y actualizacion de usuarios.
- `services/chat_rooms.py`: CRUD de salas y membresia.
- `services/messages.py`: permisos, idempotencia y persistencia de mensajes.
- `services/realtime.py`: contrato de eventos WebSocket y validaciones realtime.

Convencion:

- Las rutas no deberian implementar reglas de permisos complejas.
- Los servicios lanzan excepciones de dominio, como `MessagePermissionError`.
- Las rutas traducen esas excepciones a respuestas del transporte.

## Repository Pattern

Los repositorios concentran acceso a datos.

Ejemplos:

- `repositories/messages.py` contiene `create_message`, `get_message_by_idempotency_key` y `list_room_messages`.
- `repositories/room_members.py` contiene queries sobre membresia activa.

Convencion:

- Repositorios reciben una `Session` explicita.
- Repositorios devuelven modelos o `None`.
- Repositorios no deciden si un usuario puede hacer una accion; eso vive en servicios.

## Dependency Injection

FastAPI provee dependencias para recursos transversales.

Uso actual:

- `get_db` inyecta la sesion de base de datos.
- `get_current_user` valida JWT y devuelve el usuario autenticado.
- Routers declaran dependencias con `Depends`.

Beneficio:

- Handlers mas pequenos.
- Tests pueden reemplazar dependencias.
- Auth y DB no se duplican en cada endpoint.

## DTO / Schema Pattern

Pydantic se usa como frontera entre payloads externos y objetos internos.

Uso actual:

- `UserCreate`, `UserLogin`, `UserRead`.
- `ChatRoomCreate`, `ChatRoomUpdate`, `ChatRoomRead`.
- `MessageCreate`, `MessageRead`.
- `RoomMemberRead`.

Convencion:

- Schemas de entrada validan longitud y normalizacion basica.
- Schemas de salida no exponen hashes de password ni campos internos sensibles.
- Modelos SQLAlchemy no se devuelven sin pasar por `response_model`.

## Domain Exceptions + Transport Mapping

Los servicios levantan errores con significado de dominio. Las rutas deciden como representarlos en HTTP o WebSocket.

Ejemplo REST:

```text
MessagePermissionError -> 403 Forbidden
MessageRoomNotFoundError -> 404 Not Found
MessageIdempotencyConflictError -> 409 Conflict
```

Ejemplo WebSocket:

```text
membership_required -> error event + close 1008
rate_limit_exceeded -> error event, socket sigue abierto
invalid_message -> error event
```

Beneficio:

- El dominio no queda acoplado a FastAPI.
- El mismo caso de negocio puede mapearse distinto en REST y WebSocket.

## Unit Of Work Ligero

La sesion SQLAlchemy viaja explicitamente desde rutas a servicios y repositorios.

Uso actual:

- `create_message` hace `db.add`, `db.commit` y `db.refresh` en el repositorio.
- Los servicios manejan `IntegrityError` cuando necesitan resolver carreras de idempotencia.

Este proyecto no usa una clase `UnitOfWork` dedicada porque el alcance actual es pequeno. Si aparecen transacciones multi-repositorio mas complejas, puede tener sentido introducir una abstraccion formal.

## Idempotency Pattern

El envio REST de mensajes requiere `Idempotency-Key`.

Scope:

```text
room_id + sender_id + idempotency_key
```

El backend calcula un hash del request normalizado. Si la misma key se usa con el mismo contenido, devuelve el mensaje existente. Si se usa con contenido distinto, responde conflicto.

WebSocket reutiliza el mismo patron con `client_message_id`.

Referencia: [idempotency.md](idempotency.md).

## Rate Limiter Adapter

`infra/rate_limit.py` envuelve la libreria `limits` detras de una interfaz pequena:

```text
check(key) -> RateLimitResult
```

Uso actual:

- Auth: scope por username y accion.
- REST messages: scope por usuario y sala.
- WebSocket messages: scope por usuario y sala.

Beneficio:

- Las rutas no conocen detalles de `limits`.
- Cambiar storage o estrategia no requiere reescribir handlers.

Referencia: [rate-limiting.md](rate-limiting.md).

## Connection Manager

Las conexiones WebSocket activas se administran con un manager por sala.

Responsabilidades:

- Registrar conexiones por `room_id`.
- Remover conexiones al desconectar.
- Emitir broadcast solo a la sala correcta.
- Cerrar sockets activos cuando una sala se elimina.

Este patron evita que la ruta WebSocket tenga que mantener estructuras globales directamente.

## Optimistic-Safe Realtime Flow

El flujo realtime actual evita UI optimista para el primer corte:

```text
cliente envia message.create
backend valida y persiste
backend emite message.created
frontend agrega mensaje al recibir message.created
```

Beneficio:

- El frontend muestra mensajes confirmados por persistencia.
- Se reducen duplicados.
- La deduplicacion puede hacerse por `message.id`.

## React Hooks For Side Effects

El frontend concentra efectos en hooks.

Uso actual:

- `useAuth` maneja estado de autenticacion.
- `useRoomWebSocket` maneja conexion, eventos, errores y envio realtime.

Convencion:

- Paginas orquestan hooks y clientes API.
- Componentes reciben datos y callbacks.
- Detalles de WebSocket no se mezclan con componentes de render.

## API Client Boundary

El frontend centraliza llamadas al backend en `frontend/src/api`.

Uso actual:

- `auth.ts`: login/register.
- `rooms.ts`: CRUD y membresia.
- `messages.ts`: historial y envio REST.
- `websocket.ts`: construccion de URL WebSocket.
- `client.ts`: cliente base HTTP.

Beneficio:

- Cambios de URL, headers o parsing quedan en un lugar.
- Componentes y paginas no repiten detalles de fetch.

## Configuration Object

La configuracion backend vive en `Settings`, basado en `pydantic-settings`.

Uso actual:

- Variables de entorno tipadas.
- Defaults locales.
- Validacion de secretos en produccion.
- Parsing flexible de `CORS_ORIGINS`.

Beneficio:

- Configuracion centralizada.
- Errores de configuracion fallan al inicio.
- Los defaults sirven para desarrollo local.

## Testing Patterns

La suite backend usa fixtures para aislar escenarios.

Patrones aplicados:

- Base de datos de test aislada.
- Helpers para crear usuarios, salas, membresias, mensajes y tokens.
- Tests por contrato observable: status codes, payloads y eventos WebSocket.
- Reset explicito de rate limiters en tests que modifican limites.

Objetivo:

- Probar comportamiento publico y reglas de negocio sin depender de datos externos.
