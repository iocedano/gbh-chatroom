# Rate Limiting Para Envio De Mensajes

Este proyecto limita que tan rapido un usuario puede enviar mensajes en una sala. El objetivo es proteger la API contra spam y envios abusivos de alto volumen sin bloquear el uso normal del chat.

La implementacion vive en `app/infra/rate_limit.py`, envuelve la libreria `limits` y se aplica a REST (`POST /rooms/{room_id}/messages`), WebSocket (`message.create`) y endpoints de auth.

## Algoritmo

El backend usa la libreria `limits` con estrategia **moving window** por defecto.

Para cada scope key, el limiter:

1. Revisa si otro evento cabe dentro de la ventana configurada.
2. Registra el evento cuando esta permitido.
3. Rechaza el evento cuando el limite ya fue alcanzado.

Requests rechazadas incluyen `retry_after_seconds`, derivado del tiempo de reset devuelto por `limits`.

```text
window_seconds = 60
max_events = 20

t=0s   -> permitido  (1/20)
t=3s   -> permitido  (2/20)
...
t=55s  -> permitido  (20/20)
t=56s  -> rechazado (retry despues de que el evento mas antiguo salga de la ventana)
t=61s  -> permitido  (evento de t=0s expiro)
```

El storage default `memory://` es local al proceso y apropiado para desarrollo y despliegues de una sola instancia. Ver [Despliegues Multi-Instancia](#despliegues-multi-instancia) para notas de produccion.

## Tipos Principales

### `LimitsRateLimiter`

```python
message_rate_limiter = LimitsRateLimiter(
    max_events=settings.message_rate_limit_max_events,
    window_seconds=settings.message_rate_limit_window_seconds,
    storage_uri=settings.rate_limit_storage_uri,
    strategy=settings.rate_limit_strategy,
)
```

API publica:

- `check(key: str) -> RateLimitResult`: evalua y consume un evento para `key` cuando esta permitido.
- `reset() -> None`: recrea el storage y limiter configurados. Se usa en tests.

`InMemoryRateLimiter` se mantiene como alias de compatibilidad para imports antiguos.

### `RateLimitResult`

- `allowed: bool`: si la request puede continuar.
- `retry_after_seconds: int`: segundos a esperar antes de reintentar cuando `allowed` es `False`.

## Configuracion

Variables de entorno:

| Variable | Default | Descripcion |
| --- | --- | --- |
| `MESSAGE_RATE_LIMIT_MAX_EVENTS` | `20` | Maximo de envios de mensajes por ventana |
| `MESSAGE_RATE_LIMIT_WINDOW_SECONDS` | `60` | Tamano de la ventana de mensajes en segundos |
| `AUTH_RATE_LIMIT_MAX_EVENTS` | `10` | Maximo de intentos register/login por ventana y username |
| `AUTH_RATE_LIMIT_WINDOW_SECONDS` | `60` | Tamano de la ventana de auth en segundos |
| `RATE_LIMIT_STORAGE_URI` | `memory://` | URI de storage de `limits`. Usa `redis://...` para limites compartidos en produccion |
| `RATE_LIMIT_STRATEGY` | `moving-window` | Una de `fixed-window`, `moving-window` o `sliding-window-counter` |

Settings se definen en `app/infra/settings.py` y se leen una vez al iniciar el proceso.

## Scope Keys

Los limites se aplican **por usuario y por sala**. El formato de la key depende del transporte:

```text
REST:      rest:{room_id}:{user_id}
WebSocket: ws:{room_id}:{user_id}
Register:  register:{username}
Login:     login:{username}
```

Esto significa:

- El mismo usuario tiene limites independientes en salas distintas.
- Usuarios distintos en la misma sala tienen limites independientes.
- Trafico REST y WebSocket usan contadores separados, incluso para el mismo usuario y sala.
- Intentos de register y login usan contadores separados por username.

## Comportamiento REST

Endpoint:

```http
POST /rooms/{room_id}/messages
```

Cuando se excede el limite:

- Status: `429 Too Many Requests`
- Body: `{"detail": "Message rate limit exceeded"}`
- Header: `Retry-After: <seconds>`

Implementacion: `app/api/routes/messages.py`

## Comportamiento WebSocket

Evento:

```json
{
  "type": "message.create",
  "client_message_id": "6f0c7c4a-1b46-4c36-9bd4-24d8b643245c",
  "content": "Hola"
}
```

Cuando se excede el limite:

- El mensaje no se persiste.
- El servidor emite un evento `error` con `code = "rate_limit_exceeded"`.
- El socket permanece abierto.

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

Implementacion:

- Capa de transporte: `app/api/routes/websocket.py`
- Manejo de dominio: `app/services/realtime.py`

## Orden De Request

Orden actual para crear mensajes REST:

```text
1. Autenticar usuario
2. Revisar rate limit
3. Validar sala, membresia e idempotencia dentro del message service
4. Crear o devolver mensaje existente
```

Orden actual para WebSocket `message.create`:

```text
1. Autenticar usuario
2. Validar membresia activa
3. Revisar rate limit
4. Validar payload e idempotencia
5. Crear mensaje y hacer broadcast
```

## Relacion Con Idempotencia

Rate limiting e idempotencia resuelven problemas distintos:

- **Rate limiting** protege la API contra volumen abusivo.
- **Idempotencia** protege retries legitimos contra mensajes duplicados.

Ver [idempotency.md](idempotency.md) para el contrato completo de idempotencia.

Comportamiento importante hoy:

- Un retry con el mismo `Idempotency-Key` o `client_message_id` todavia consume presupuesto de rate limit si llega al limiter antes del lookup idempotente.
- Si quieres que retries de la misma operacion logica no consuman rate limit, mueve el check del limiter despues del camino idempotente de "devolver mensaje existente".

Orden recomendado cuando ambas protecciones estan activas:

```text
1. Autenticar usuario
2. Validar que la sala existe
3. Validar membresia activa
4. Validar idempotency key / client_message_id
5. Si el mensaje existente coincide, devolverlo sin consumir rate limit
6. Si es un mensaje nuevo, aplicar rate limit
7. Crear mensaje
```

## Despliegues Multi-Instancia

Con `RATE_LIMIT_STORAGE_URI=memory://`, cada instancia de la aplicacion aplica su propio limite, asi que el throughput efectivo escala con el numero de replicas.

Para limites compartidos entre instancias, configura Redis usando el mismo formato de scope key:

```text
RATE_LIMIT_STORAGE_URI=redis://redis:6379/0

rest:{room_id}:{user_id}
ws:{room_id}:{user_id}
register:{username}
login:{username}
```

Mantener la interfaz `check(key) -> RateLimitResult` permite que los handlers no cambien.

## Extender El Patron

Para aplicar rate limit a una operacion nueva:

1. Crear una instancia de `LimitsRateLimiter` por politica de limite.
2. Elegir una scope key estable que identifique actor y recurso protegidos.
3. Llamar `check(key)` en el borde de ruta o servicio.
4. Mapear `RateLimitResult` a la respuesta del transporte:
   - REST: `429` + `Retry-After`
   - WebSocket: evento `error` con `code` estable

Ejemplos de scope keys:

```text
login:{username}
invite:{room_id}:{user_id}
```

## Tests

Los tests sobrescriben las instancias compartidas de limiter para mantener escenarios deterministas:

```python
messages_route.message_rate_limiter.max_events = 2
messages_route.message_rate_limiter.window_seconds = 60
messages_route.message_rate_limiter.reset()
```

Tests relevantes en `app/tests/test_p1_backend.py`:

- `test_rest_message_rate_limit_returns_429`
- `test_websocket_message_rate_limit_returns_error_event`

## Archivos Fuente

| Archivo | Responsabilidad |
| --- | --- |
| `app/infra/rate_limit.py` | `LimitsRateLimiter` y `RateLimitResult` |
| `app/infra/settings.py` | Configuracion por entorno |
| `app/api/routes/auth.py` | Rate limiting de auth |
| `app/api/routes/messages.py` | Rate limiting REST |
| `app/api/routes/websocket.py` | Wiring de rate limiting WebSocket |
| `app/services/realtime.py` | Check de limite a nivel dominio WebSocket |
