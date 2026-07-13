# TODO Frontend

Lista de pendientes para el frontend de GBH Chat. El MVP actual cubre auth, salas y mensajes vía REST.

## Completado

- [x] Scaffold Vite + React + TypeScript
- [x] Tailwind CSS (UI simple)
- [x] Cliente API con JWT (`Authorization: Bearer`)
- [x] Auth: registro, login, logout, rutas protegidas
- [x] Salas: listar, crear, entrar (`join`)
- [x] Chat: historial REST, enviar mensajes, botón actualizar
- [x] Header `Idempotency-Key` al enviar mensajes
- [x] Manejo básico de errores (`401`, `403`, `409`)
- [x] CORS habilitado en backend para `localhost:5173`

## Pendiente — Prioridad alta

- [ ] **WebSocket**: mensajes en tiempo real (`useRoomWebSocket`)
- [ ] **Mostrar username del remitente**: el API devuelve `sender_id`, no `username`
  - Opción A: extender `MessageRead` en backend con `sender_username`
  - Opción B: cachear usuarios en frontend con `GET /users/{id}`
- [ ] **Nombre de sala en ChatPage**: hoy muestra `Sala #id`; usar `GET /rooms/{id}` para el nombre
- [ ] **Salir de sala (leave)**: botón en UI que llame `POST /rooms/{id}/leave`
- [ ] **Docker**: servicio `web` en `docker-compose.yml` para el frontend

## Pendiente — Prioridad media

- [ ] **Paginación de mensajes**: `offset` / `limit` en `GET /rooms/{id}/messages`
- [ ] **Auto-scroll** al enviar o recibir mensajes
- [ ] **Estados de carga** más granulares (skeletons, disabled states)
- [ ] **Validación de formularios** con mensajes inline (min 3 chars usuario, min 8 password)
- [ ] **Persistencia de sesión**: verificar token expirado y redirigir a login
- [ ] **Tests**: componentes críticos (LoginForm, MessageInput) y cliente API

## Pendiente — Bonus (opcional del task)

- [ ] Typing indicator
- [ ] Indicador online/offline
- [ ] Read receipts / delivery status
- [ ] Búsqueda de mensajes
- [ ] Polling automático como fallback sin WebSocket
- [ ] Reconexión automática de WebSocket

## Cómo correr

```bash
# Terminal 1 — Backend
docker compose up

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

Abrir http://localhost:5173

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | URL base del API REST |

Cuando se agregue WebSocket:

| Variable | Default | Descripción |
|----------|---------|-------------|
| `VITE_WS_URL` | `ws://localhost:8000` | URL base del WebSocket |
