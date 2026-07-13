# WebSocket Technical Plan

Este documento describe el plan tecnico para implementar mensajeria en tiempo real. El foco principal es backend; el frontend se mantiene como una integracion delgada sobre el contrato WebSocket.

## Decision Principal: `client_message_id`

Para WebSocket conviene usar un `client_message_id` generado por el cliente, no el `message_id` de base de datos.

El `message_id` actual debe seguir siendo el identificador canonico generado por el backend al persistir el mensaje. No sirve para deduplicar retries porque el cliente no lo conoce antes de enviar el mensaje. En cambio, un `client_message_id` funciona como identificador de la operacion logica de envio: el cliente lo genera antes de mandar, lo mantiene estable durante retries/reconexion, y el backend lo usa para evitar duplicados.

Terminologia recomendada:

- `id`: ID canonico del mensaje, generado por la base de datos.
- `client_message_id`: UUID generado por el cliente para deduplicar una operacion de envio.
- `idempotency_key`: mantenerlo solo para REST, o renombrarlo gradualmente a `client_message_id` si se quiere unificar el modelo mental.

Para este proyecto, la ruta mas clara es:

- REST conserva `Idempotency-Key` por compatibilidad con lo ya implementado.
- WebSocket usa `client_message_id` dentro del payload.
- Ambos pueden guardar el valor en la columna existente `idempotency_key` inicialmente, o se puede agregar una columna nueva `client_message_id` si se quiere semantica mas explicita.

## Contrato WebSocket

Endpoint:

```text
WS /rooms/{room_id}/ws?token=<jwt>
```

Se usa `token` por query string porque `WebSocket` en navegador no permite enviar facilmente un header `Authorization`.

Evento para enviar mensaje:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

Evento emitido por el servidor:

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

Evento de error:

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

## Backend Scope

### 1. Connection Manager por sala

Crear `app/sockets/connection_manager.py`.

Responsabilidades:

- Mantener conexiones activas agrupadas por `room_id`.
- Registrar conexiones al aceptar el WebSocket.
- Remover conexiones al desconectar.
- Hacer broadcast solamente a conexiones del mismo room.
- Limpiar conexiones que fallen durante el envio.

Interfaz sugerida:

```python
class ConnectionManager:
    async def connect(self, room_id: int, websocket: WebSocket) -> None: ...
    def disconnect(self, room_id: int, websocket: WebSocket) -> None: ...
    async def broadcast(self, room_id: int, payload: dict) -> None: ...
```

### 2. Autenticacion y autorizacion antes de aceptar

El endpoint debe validar antes de `websocket.accept()`:

1. El token JWT existe.
2. El token es valido.
3. El usuario existe.
4. El room existe.
5. El usuario es miembro activo del room.

Si falla alguna condicion, cerrar la conexion con un codigo WebSocket apropiado. Para el MVP se puede usar:

- `1008` para policy violation: auth invalida o sin permisos.
- `1003` para payload no soportado.

La implementacion usa el JWT existente como fuente de autenticidad:

- El cliente envia `token` en query string.
- El backend decodifica el token con `decode_access_token`.
- El `sender_id` sale del `sub` del JWT, nunca del payload enviado por el cliente.
- El backend busca el usuario autenticado antes de aceptar la conexion.
- La membresia activa en el room se valida antes de aceptar la conexion.

### 3. Persistir antes de publicar

El servidor no debe publicar mensajes que no fueron persistidos. El flujo correcto es:

```text
receive event
validate event shape
validate MessageCreate
check room membership
dedupe by client_message_id
persist message
build response payload
broadcast to room
```

Tambien se revalida la membresia activa antes de procesar cada `message.create`. Esto cubre el caso donde el usuario abre un WebSocket valido, pero luego deja la sala desde otra pestana, otro dispositivo o una llamada REST.

Comportamiento recomendado para ese caso:

1. El usuario se conecta correctamente al WebSocket.
2. El usuario deja la sala mientras el WebSocket sigue abierto.
3. En el siguiente intento de enviar mensaje, el backend detecta que ya no es miembro activo.
4. El backend envia un evento `error` con `code = "membership_required"`.
5. El backend cierra el socket con `1008`.
6. El `finally` del endpoint remueve la conexion del connection manager.

Para una version posterior mas estricta, el endpoint REST `leave room` podria emitir una senal interna para cerrar inmediatamente las conexiones activas de ese usuario en ese room. Para el MVP, revalidar antes de cada mensaje es suficiente y mantiene el backend simple.

### 4. Dedupe con `client_message_id`

La garantia debe ser equivalente a la idempotencia REST:

- Mismo `room_id` + `sender_id` + `client_message_id` + mismo contenido: retornar/publicar el mensaje existente.
- Mismo `room_id` + `sender_id` + `client_message_id` + contenido distinto: emitir error de conflicto.
- Mismo contenido con distinto `client_message_id`: crear mensajes distintos, porque repetir texto en chat puede ser intencional.

Indice unico recomendado si se agrega columna nueva:

```text
room_id + sender_id + client_message_id
```

Si se reutiliza la columna actual:

```text
room_id + sender_id + idempotency_key
```

El hash del contenido debe seguir siendo calculado por el backend, no enviado por el cliente.

### 5. Schemas

Agregar schemas para eventos WebSocket, por ejemplo en `app/schemas/websocket.py`:

- `WebSocketMessageCreateEvent`
- `WebSocketErrorEvent`
- `WebSocketMessageCreatedEvent`

Tambien actualizar el schema de lectura de mensajes para incluir:

- `sender_username`
- `client_message_id` si se decide exponerlo

### 6. Servicio de mensajes

Agregar una funcion orientada a WebSocket en `app/services/messages.py`:

```python
def create_realtime_message(
    db: Session,
    room_id: int,
    payload: MessageCreate,
    *,
    sender_id: int,
    client_message_id: str,
):
    ...
```

Esta funcion debe reutilizar la misma logica de validacion que REST:

- Room existe.
- Usuario es miembro activo.
- Contenido valido.
- Dedupe/conflicto con hash de request.

### 7. Router WebSocket

Reemplazar el stub actual por un `APIRouter`:

```python
router = APIRouter(prefix="/rooms/{room_id}", tags=["websocket"])

@router.websocket("/ws")
async def room_websocket(...):
    ...
```

Registrar el router en `app/main.py`.

## Frontend Plan

El frontend debe hacer lo minimo necesario para consumir el contrato.

### 1. Variables

Agregar soporte para:

```text
VITE_WS_URL=ws://localhost:8000
```

Si no existe, derivar desde `VITE_API_URL`:

- `http://localhost:8000` -> `ws://localhost:8000`
- `https://api.example.com` -> `wss://api.example.com`

### 2. Hook `useRoomWebSocket`

Crear `frontend/src/hooks/useRoomWebSocket.ts`.

Responsabilidades:

- Leer token almacenado.
- Conectar a `/rooms/{roomId}/ws?token=<token>`.
- Exponer estado `connecting`, `connected`, `disconnected`, `error`.
- Exponer `sendMessage(content)`.
- Generar `client_message_id` por mensaje.
- Recibir `message.created` y anexar o reconciliar el mensaje en estado local.
- En error de auth, cerrar sesion o redirigir al login.

### 3. Integracion en `ChatPage`

Flujo recomendado:

1. `joinRoom(roomId)`.
2. Cargar historial por REST.
3. Abrir WebSocket.
4. Enviar mensajes por WebSocket cuando este conectado.
5. Esperar `message.created` para confirmar el mensaje.
6. Opcionalmente mostrar mensaje pendiente usando `client_message_id`.

Para el MVP, se puede evitar UI optimista y simplemente esperar el evento del servidor. Es menos vistoso, pero reduce duplicados y casos raros.

### 4. Reconciliacion

Si se implementa UI optimista:

- Crear mensaje temporal con `client_message_id`.
- Al recibir `message.created`, reemplazar el temporal por el mensaje persistido.
- Si llega error con el mismo `client_message_id`, marcar el mensaje como fallido.

Si no hay UI optimista:

- Solo agregar mensajes cuando llega `message.created`.
- Deduplicar por `id` por seguridad.

## Plan de Implementacion

1. Backend: crear connection manager.
2. Backend: definir schemas de eventos.
3. Backend: agregar `client_message_id` o reutilizar `idempotency_key`.
4. Backend: crear servicio `create_realtime_message`.
5. Backend: implementar `WS /rooms/{room_id}/ws`.
6. Backend: incluir router en `main.py`.
7. Backend: actualizar payload de mensajes con `sender_username`.
8. Frontend: agregar helper de WebSocket URL.
9. Frontend: crear `useRoomWebSocket`.
10. Frontend: integrar hook en `ChatPage`.
11. Docs: documentar contrato en README.
12. QA manual con dos sesiones en el mismo room.

## Pruebas Minimas

Backend:

- Conexion sin token es rechazada.
- Token invalido es rechazado.
- Usuario no miembro no puede conectar.
- Usuario miembro puede conectar.
- Mensaje valido se persiste antes de broadcast.
- Dos conexiones en el mismo room reciben `message.created`.
- Conexion en otro room no recibe el mensaje.
- Retry con mismo `client_message_id` y mismo contenido no duplica.
- Retry con mismo `client_message_id` y otro contenido devuelve error.
- Desconexion limpia la conexion sin romper otros broadcasts.

Frontend:

- Dos ventanas reciben mensajes en tiempo real.
- El remitente tambien recibe confirmacion del mensaje.
- Al refrescar, el historial REST contiene los mensajes enviados por WebSocket.
- Al desconectarse el WebSocket, la UI informa el estado o usa fallback REST.
