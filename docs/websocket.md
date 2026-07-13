# WebSocket Messaging

Este documento describe el contrato y los detalles tecnicos de la mensajeria en tiempo real para backend y frontend.

## Objetivo

El chat usa WebSocket para enviar y recibir mensajes en tiempo real por sala. El historial inicial sigue cargandose por REST, y los mensajes nuevos se envian por WebSocket.

Flujo general:

1. El cliente entra a la sala por REST.
2. El cliente carga historial por REST.
3. El cliente abre `WS /rooms/{room_id}/ws?token=<access_token>`.
4. El cliente envia eventos `message.create`.
5. El backend persiste el mensaje.
6. El backend emite `message.created` a las conexiones activas de esa sala.

## Endpoint

```text
WS /rooms/{room_id}/ws?token=<access_token>
```

`token` debe ser el JWT retornado por login. Se envia por query string porque `WebSocket` en navegador no permite configurar facilmente el header `Authorization`.

## Autenticacion y Autorizacion

El backend usa el JWT existente como fuente de autenticidad:

- Decodifica `token` con `decode_access_token`.
- Lee `sub` y lo convierte en `user_id`.
- Busca el usuario autenticado.
- Valida que el usuario sea miembro activo del room.
- Acepta la conexion solo si las validaciones pasan.

El cliente nunca envia `sender_id`. El backend siempre deriva `sender_id` del JWT.

La membresia activa se valida dos veces:

- Antes de aceptar el WebSocket.
- Antes de procesar cada `message.create`.

Esto cubre el caso donde un usuario abre un WebSocket valido y luego deja la sala desde otra pestana, otro dispositivo o una llamada REST.

Si el usuario deja la sala mientras el socket sigue abierto:

1. El siguiente `message.create` revalida membresia.
2. El backend emite `error` con `code = "membership_required"`.
3. El backend cierra el socket con codigo `1008`.
4. El endpoint remueve la conexion del connection manager.

Si el creador elimina una sala con sockets activos, el backend cierra las conexiones activas de esa sala con codigo `1008` y remueve el room del connection manager.

## `client_message_id`

WebSocket usa un `client_message_id` generado por el cliente para deduplicar retries.

No se usa el `id` de base de datos para esto porque ese ID se conoce solamente despues de persistir el mensaje. El `client_message_id` existe antes del envio, se mantiene estable durante retries, y representa una operacion logica de envio.

Terminologia:

- `id`: ID canonico del mensaje generado por la base de datos.
- `client_message_id`: UUID generado por el cliente antes de enviar.
- `idempotency_key`: columna existente donde se almacena `client_message_id` para WebSocket.

Reglas:

- Mismo `room_id + sender_id + client_message_id` con mismo contenido: retorna/publica el mensaje existente.
- Mismo `room_id + sender_id + client_message_id` con contenido distinto: error de conflicto.
- Mismo contenido con distinto `client_message_id`: crea mensajes distintos.

## Eventos

### Enviar Mensaje

Cliente -> servidor:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

### Mensaje Creado

Servidor -> clientes del mismo room:

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

El backend persiste el mensaje antes de emitir `message.created`.

### Error

Servidor -> cliente:

```json
{
  "type": "error",
  "error": {
    "code": "invalid_message",
    "message": "Message content cannot be blank",
    "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c"
  }
}
```

Codigos actuales:

- `invalid_json`
- `invalid_payload`
- `unsupported_event`
- `invalid_client_message_id`
- `invalid_message`
- `client_message_id_conflict`
- `rate_limit_exceeded`
- `room_not_found`
- `membership_required`

`message.create` esta limitado por usuario y sala. Cuando se excede el limite, el backend emite `error` con `code = "rate_limit_exceeded"` y no persiste el mensaje.

## Backend

Archivos principales:

- `app/api/routes/websocket.py`: capa de transporte WebSocket.
- `app/services/realtime.py`: autenticacion, autorizacion, parsing logico de eventos y construccion de payloads.
- `app/services/messages.py`: persistencia realtime mediante `create_realtime_message`.
- `app/sockets/connection_manager.py`: conexiones activas agrupadas por `room_id`.

Responsabilidades:

- El router recibe la conexion, lee eventos, envia errores, cierra sockets y delega logica de dominio.
- `realtime.py` valida JWT, membresia, evento `message.create` y traduce errores de dominio a eventos realtime.
- El connection manager mantiene conexiones por sala y hace broadcast solamente dentro del mismo `room_id`.

Flujo de `message.create`:

```text
receive JSON
validate payload object
validate event type
validate client_message_id
revalidate active membership
validate content
dedupe by client_message_id
persist message
broadcast message.created to room
```

## Sanitizacion de Contenido

REST y WebSocket usan el schema `MessageCreate`:

- `content` se recorta con `strip()`.
- Mensajes vacios o solo whitespace se rechazan.
- El maximo permitido es 1000 caracteres.
- HTML se almacena como texto literal en backend. Los clientes deben renderizarlo como texto o escaparlo antes de insertarlo en HTML.

## Frontend

Archivos principales:

- `frontend/src/api/websocket.ts`: construccion de URL WebSocket.
- `frontend/src/hooks/useRoomWebSocket.ts`: ciclo de vida del socket y envio de mensajes.
- `frontend/src/pages/ChatPage.tsx`: carga historial, habilita WebSocket e integra mensajes entrantes.
- `frontend/src/components/MessageList.tsx`: render de mensajes, `sender_username` y auto-scroll basico.
- `frontend/src/types/index.ts`: tipos de mensajes y eventos WebSocket.

Variables:

```text
VITE_WS_URL=ws://localhost:8000
```

Si `VITE_WS_URL` no existe, el frontend deriva la URL desde `VITE_API_URL`:

- `http://localhost:8000` -> `ws://localhost:8000`
- `https://api.example.com` -> `wss://api.example.com`

Flujo en `ChatPage`:

1. Validar `roomId`.
2. Ejecutar `joinRoom(roomId)`.
3. Cargar historial con `listMessages(roomId)`.
4. Abrir WebSocket cuando no hay loading ni error.
5. Deshabilitar input hasta que el socket este conectado.
6. Enviar mensajes por `useRoomWebSocket.sendMessage`.
7. Agregar mensajes al estado solo al recibir `message.created`.
8. Deduplicar mensajes por `id`.

El frontend no hace UI optimista en el primer corte. Esto evita duplicados y mantiene el UI alineado con mensajes ya persistidos.

## Username en Mensajes

El evento WebSocket `message.created` incluye `sender_username`.

El historial REST actual puede seguir devolviendo solo `sender_id`. Por eso el frontend trata `sender_username` como opcional:

```ts
message.sender_username ?? `Usuario #${message.sender_id}`
```

Pendiente recomendado: extender `GET /rooms/{room_id}/messages` para devolver `sender_username` tambien en historial.

## QA Manual

Backend:

- Conectar sin token: rechazo.
- Conectar con token invalido: rechazo.
- Usuario no miembro no puede conectar.
- Usuario miembro puede conectar.
- Mensaje valido se persiste antes de broadcast.
- Dos conexiones en el mismo room reciben `message.created`.
- Conexion en otro room no recibe mensajes de esta sala.
- Retry con mismo `client_message_id` y mismo contenido no duplica.
- Retry con mismo `client_message_id` y otro contenido devuelve conflicto.
- Enviar por encima del limite devuelve `rate_limit_exceeded`.
- Desconexion limpia la conexion sin romper otros broadcasts.

Frontend:

- Login con dos usuarios.
- Ambos entran a la misma sala.
- Usuario A envia mensaje.
- Usuario B lo ve sin refrescar.
- Usuario A tambien ve confirmacion por evento.
- Al refrescar, el historial REST contiene los mensajes enviados por WebSocket.
- Salir de sala desde otra pestana y luego intentar enviar: se muestra error/cierre por membresia.
