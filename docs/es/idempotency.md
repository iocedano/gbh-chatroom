# Idempotencia En El Envio De Mensajes

Este proyecto usa el header `Idempotency-Key` para crear mensajes. El objetivo es permitir retries seguros sin crear mensajes duplicados cuando un cliente hace timeout, se reconecta, envia dos veces o no recibe la primera respuesta.

## Contrato API

Los clientes deben enviar un `Idempotency-Key` unico para cada operacion logica de `POST /rooms/{room_id}/messages`.

```http
POST /rooms/{room_id}/messages
Authorization: Bearer <access_token>
Idempotency-Key: 8f4b1b7e-9e3a-4d8c-9c7f-123456789abc
Content-Type: application/json
```

```json
{
  "content": "Hola"
}
```

Comportamiento recomendado del cliente:

- Generar un UUID nuevo o una key de alta entropia para cada mensaje nuevo.
- Reutilizar la misma key solo al reintentar la misma request logica.
- No reutilizar una key para un body distinto.
- Mantener la key estable mientras el mensaje este pendiente en UI optimista.

## Garantias Del Backend

El backend trata `Idempotency-Key` como un identificador opaco generado por el cliente. No confia en la key por si sola.

Para cada envio, el backend almacena:

- `idempotency_key`: valor recibido en el header.
- `idempotency_request_hash`: hash SHA-256 generado por el servidor desde el scope y contenido normalizados.

El constraint unico de base de datos es:

```text
room_id + sender_id + idempotency_key
```

Este scope evita colisiones entre usuarios o salas distintas y mantiene idempotentes los retries del mismo usuario en la misma sala.

## Comportamiento De Respuesta

Comportamiento esperado:

- Key nueva + request valida: crea y devuelve el mensaje nuevo.
- Misma key + mismo request hash: devuelve el mensaje existente.
- Misma key + request hash distinto: devuelve `409 Conflict`.
- Falta `Idempotency-Key`: FastAPI devuelve `422 Unprocessable Entity`.
- Formato de key invalido: devuelve `400 Bad Request`.

El caso `409 Conflict` es intencional. Evita que una misma key represente varias operaciones distintas.

## Practicas De Seguridad

Usa la idempotency key solo como primitiva de deduplicacion. No es un mecanismo de autorizacion y nunca debe reemplazar autenticacion, validacion de membresia o rate limiting.

Salvaguardas actuales:

- Se valida autenticacion antes de crear mensajes.
- Se valida membresia activa antes de crear mensajes.
- La idempotency key queda scoped por usuario autenticado y sala.
- El backend calcula el request hash; el cliente no lo provee.
- El constraint unico de base de datos protege contra inserts duplicados concurrentes.
- `IntegrityError` se maneja para que retries en carrera puedan devolver el mensaje existente.
- Reutilizar la misma key con contenido distinto devuelve `409 Conflict`.

## Relacion Con Rate Limiting

Idempotencia y rate limiting resuelven problemas distintos:

- Idempotencia protege retries legitimos contra mensajes duplicados.
- Rate limiting protege la API contra spam o envios abusivos de alto volumen.

Ver [rate-limiting.md](rate-limiting.md) para el patron completo de rate limiting, configuracion y comportamiento por transporte.

Hoy la creacion REST de mensajes revisa el rate limit antes del lookup idempotente, asi que un retry con el mismo `Idempotency-Key` todavia puede consumir presupuesto de rate limit. El mismo tradeoff esta documentado en [rate-limiting.md](rate-limiting.md).

Si el producto necesita que retries de la misma operacion logica no consuman rate limit, usa este orden:

```text
1. Autenticar usuario
2. Validar que la sala existe
3. Validar membresia activa
4. Validar Idempotency-Key
5. Buscar mensaje idempotente existente
6. Si el mensaje existente coincide, devolverlo sin consumir rate limit
7. Si es un mensaje nuevo, aplicar rate limit
8. Crear mensaje
```

Esto evita castigar a clientes por reintentar la misma request logica.

## Contenido Duplicado Con Keys Distintas

La idempotencia no puede rechazar de forma segura todos los mensajes con el mismo body. En chat, enviar el mismo texto dos veces puede ser intencional.

Ejemplo:

```text
Idempotency-Key: abc
content: Hola

Idempotency-Key: xyz
content: Hola
```

Estas son operaciones logicas distintas. Si el producto necesita proteccion contra doble click accidental, usa una ventana corta de deduplicacion suave basada en:

```text
sender_id + room_id + content_hash + short time window
```

Ventana recomendada:

```text
1000-2000 ms
```

Esa deduplicacion suave debe estar separada de la garantia fuerte de idempotencia, porque repetir mensajes identicos puede ser una intencion valida del usuario.

## Notas De Storage

La implementacion actual guarda metadata de idempotencia directamente en `messages`, lo cual es apropiado porque crear mensajes es la unica operacion idempotente soportada hoy.

Si la idempotencia se expande a muchos endpoints, considera una tabla separada `idempotency_keys` con:

- scope de usuario autenticado
- scope de operacion
- idempotency key
- request hash
- status de respuesta
- body de respuesta o referencia al recurso
- timestamp de expiracion

Para despliegues multi-instancia, Redis tambien puede ser util para locks de corta duracion, pero el constraint de base de datos debe seguir siendo la fuente de verdad para mensajes persistidos.
