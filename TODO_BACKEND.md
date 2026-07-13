# TODO Backend

Checklist actualizado de lo que falta o conviene cerrar en el backend antes de considerar el challenge completo.

## P0 - Plan tecnico core

- [ ] Agregar suite de tests automatizados del backend.
  - Auth: registro, login, token invalido y rutas protegidas.
  - Rooms: crear, listar, leer, actualizar y eliminar.
  - Membership: join, leave y re-join.
  - Messages REST: crear, listar, max length, contenido vacio/whitespace-only y permisos por membresia.
  - Idempotency REST: retry exitoso con mismo payload y `409 Conflict` con payload distinto.
  - WebSocket: conexion autenticada, rechazo sin token/token invalido, rechazo sin membresia, persistencia antes de broadcast, broadcast solo por room y desconexion.

- [ ] Agregar fixtures de base de datos para tests.
  - Usar una base aislada por test o transacciones con rollback.
  - Crear schema de forma reproducible desde modelos o migraciones.
  - Proveer helpers para crear usuarios, rooms, memberships, tokens y mensajes.

- [ ] Cerrar contrato de historial de mensajes.
  - Decidir si `GET /rooms/{room_id}/messages` debe incluir `sender_username`.
  - Si se incluye, actualizar schema, query/repository y frontend consumidor.
  - Mantener consistencia entre payload REST y `message.created` de WebSocket.

## P1 - Seguridad, robustez y operacion

- [x] Agregar rate limiting para envio de mensajes.
  - Aplicar a `POST /rooms/{room_id}/messages`.
  - Aplicar tambien a eventos `message.create` por WebSocket.
  - Devolver errores claros al exceder el limite.
  - Cubrir con tests.

- [x] Validar permisos y ciclo de vida en operaciones sensibles.
  - Confirmar que usuarios que dejaron un room no puedan leer, enviar ni recibir mensajes.
  - Confirmar comportamiento cuando el creador elimina un room con miembros o sockets activos.
  - Considerar cerrar o limpiar conexiones activas del room eliminado.

- [x] Agregar logging estructurado para errores importantes.
  - Auth fallida sin exponer secretos.
  - Errores de WebSocket.
  - Conflictos de idempotencia.
  - Fallas de base de datos.

- [x] Mejorar health checks.
  - Mantener `/health/db` como readiness con DB.
  - Agregar `/health` liviano sin DB para liveness.
  - Documentar la diferencia si aplica para despliegue.

- [x] Revisar estrategia de sanitizacion de contenido.
  - Confirmar maximo de 1000 caracteres.
  - Confirmar normalizacion de contenido vacio o whitespace-only.
  - Definir explicitamente si HTML literal se permite en backend y se escapa en cliente.

## P2 - Documentacion y DX

- [ ] Completar README con instrucciones de setup.
  - Requisitos locales.
  - Variables de entorno.
  - Comandos para levantar Postgres/API/frontend.
  - Comandos de migracion Alembic.
  - Comandos de tests.

- [ ] Documentar todos los endpoints REST.
  - Auth.
  - Users.
  - Rooms.
  - Room membership.
  - Messages.
  - Codigos de error esperados.

- [ ] Documentar flujo de mensajes end-to-end.
  - REST con idempotencia.
  - WebSocket en tiempo real.
  - Orden recomendado para clientes: cargar historial y luego conectar al WebSocket.

## Bonus opcionales

- [ ] Indicador de typing por WebSocket.
- [ ] Estado online/offline por usuario.
- [ ] Busqueda de mensajes por texto.
- [ ] Read receipts o delivery status.
- [ ] Paginacion por cursor para historial de mensajes.

## Estado actual observado

- [x] Registro y login con JWT.
- [x] Password hashing.
- [x] Rutas protegidas con usuario actual.
- [x] CRUD basico de rooms.
- [x] Join/leave de rooms.
- [x] Persistencia de mensajes por REST.
- [x] Idempotencia para creacion de mensajes REST.
- [x] WebSocket para mensajeria en tiempo real en `WS /rooms/{room_id}/ws`.
- [x] Autenticacion de WebSocket con JWT.
- [x] Validacion de membresia activa antes de aceptar conexiones WebSocket.
- [x] Validacion de membresia activa antes de procesar mensajes WebSocket.
- [x] Persistencia de mensajes antes de broadcast por WebSocket.
- [x] Broadcast limitado a conexiones activas del mismo room.
- [x] Limpieza de conexiones al desconectar o fallar envio.
- [x] Contrato de eventos WebSocket documentado en `docs/websocket.md`.
- [x] Idempotencia para mensajes WebSocket usando `client_message_id`.
- [x] Validacion para evitar `JWT_SECRET_KEY` por defecto en produccion.
- [x] Normalizacion de mensajes vacios o whitespace-only.
- [x] Limite de 1000 caracteres para contenido de mensajes.
- [x] `.env.example` con variables principales.
- [x] Docker Compose con Postgres, API y frontend.
- [x] Contenedor API ejecuta `alembic upgrade head` antes de iniciar.
- [x] Health check de base de datos en `/health/db`.
- [x] Modelos y migraciones base para users, rooms, room_members y messages.
