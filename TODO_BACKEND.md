# TODO Backend

Checklist de lo que falta o conviene cerrar en el backend antes de considerar el challenge completo.

## P0 - Requisitos core pendientes

- [ ] Implementar WebSocket para mensajeria en tiempo real.
  - Endpoint sugerido: `WS /rooms/{room_id}/ws`.
  - Autenticar la conexion con JWT.
  - Validar que el usuario sea miembro activo del room antes de aceptar mensajes.
  - Persistir cada mensaje antes de publicarlo a los clientes conectados.
  - Enviar payload con `id`, `content`, `room_id`, `sender_id`, `sender_username` y `created_at`.
  - Manejar desconexiones sin romper el broadcast del room.

- [ ] Crear un connection manager por room.
  - Mantener conexiones activas agrupadas por `room_id`.
  - Permitir broadcast solo a clientes del mismo room.
  - Limpiar conexiones al desconectar o fallar el envio.

- [ ] Definir contrato de eventos WebSocket.
  - Eventos minimos: `message.created`, `error`.
  - Opcionales: `user.joined`, `user.left`, `typing.started`, `typing.stopped`.
  - Documentar formato de request/response en README.

## P1 - Seguridad y robustez

- [ ] Reemplazar el `JWT_SECRET_KEY` por defecto en entornos no locales.
  - La app no deberia iniciar en produccion con `change-me-in-development`.
  - Documentar `JWT_SECRET_KEY` y `ACCESS_TOKEN_EXPIRE_MINUTES`.

- [ ] Agregar rate limiting para envio de mensajes.
  - Aplicar a `POST /rooms/{room_id}/messages`.
  - Aplicar tambien a mensajes por WebSocket cuando exista.
  - Devolver error claro al exceder el limite.

- [ ] Revisar estrategia de sanitizacion de contenido.
  - Confirmar maximo de 1000 caracteres.
  - Normalizar contenido vacio o whitespace-only.
  - Definir si se permite HTML literal o si se escapa en cliente.

- [ ] Validar permisos en operaciones sensibles.
  - Confirmar que usuarios que dejaron un room no puedan leer, enviar ni recibir mensajes.
  - Confirmar comportamiento cuando el creador elimina un room con miembros activos.

## P1 - Tests

- [ ] Agregar suite de tests automatizados.
  - Auth: registro, login, token invalido y rutas protegidas.
  - Rooms: crear, listar, join, leave, update/delete solo por creador.
  - Messages: crear, listar, max length, permisos por membresia.
  - Idempotency: retry exitoso con mismo payload y `409` con payload distinto.
  - WebSocket: conexion autenticada, broadcast por room y desconexion.

- [ ] Agregar fixtures de base de datos para tests.
  - Usar una base aislada o transacciones por test.
  - Ejecutar migraciones o crear schema de forma reproducible.

## P2 - Documentacion y DX

- [ ] Completar README con instrucciones de setup.
  - Requisitos locales.
  - Variables de entorno.
  - Comandos para levantar Postgres/API.
  - Comandos de migracion Alembic.
  - Comandos de tests.

- [ ] Documentar todos los endpoints REST.
  - Auth.
  - Users.
  - Rooms.
  - Room membership.
  - Messages.
  - Codigos de error esperados.

- [ ] Documentar flujo de mensajes.
  - REST con idempotencia.
  - WebSocket en tiempo real.
  - Orden recomendado para clientes: cargar historial y luego conectar al WS.

- [ ] Agregar archivo `.env.example`.
  - `DATABASE_URL`.
  - `JWT_SECRET_KEY`.
  - `ACCESS_TOKEN_EXPIRE_MINUTES`.

## P2 - Operacion

- [ ] Asegurar que el contenedor API ejecute migraciones o documentar el paso obligatorio.
  - Opcion A: comando separado `alembic upgrade head`.
  - Opcion B: entrypoint que espere DB y aplique migraciones.

- [ ] Agregar logging estructurado para errores importantes.
  - Auth fallida sin exponer secretos.
  - Errores de WebSocket.
  - Conflictos de idempotencia.
  - Fallas de base de datos.

- [ ] Mejorar health checks.
  - Mantener `/health/db`.
  - Agregar `/health` liviano sin DB si hace falta.
  - Considerar readiness/liveness separados para despliegue.

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
- [x] Modelos y migraciones base para users, rooms, room_members y messages.
- [x] Docker Compose con Postgres y API.
