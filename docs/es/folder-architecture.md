# Folder Architecture

Este documento describe como esta organizado el repo y que responsabilidad tiene cada carpeta.

## Vista General

```text
.
|-- app/                 # Backend FastAPI
|-- frontend/            # Frontend React/Vite
|-- docs/                # Documentacion tecnica
|-- docker-compose.yml   # Stack local con Postgres, API y frontend
|-- README.md            # Setup, contratos REST y resumen arquitectonico
`-- TODO_BACKEND.md      # Checklist tecnico del backend
```

La separacion principal es por runtime:

- `app/` contiene la API, dominio backend, persistencia, migraciones y tests.
- `frontend/` contiene la aplicacion de navegador y sus clientes HTTP/WebSocket.
- `docs/` contiene referencias tecnicas mas profundas que el README.

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

Punto de entrada de FastAPI.

Responsabilidades:

- Crear la instancia `FastAPI`.
- Configurar CORS.
- Registrar routers REST y WebSocket.
- Exponer health checks.

### `app/api/`

Capa de transporte HTTP/WebSocket.

- `routes/`: endpoints REST y WebSocket. Traducen requests a llamadas de servicios y excepciones de dominio a codigos HTTP o eventos WebSocket.
- `dependencies.py`: dependencias compartidas de FastAPI, como `get_current_user`.
- `middleware/`: middleware HTTP reutilizable si el proyecto lo necesita.

Regla practica: esta capa debe ser delgada. Validacion de transporte y mapping de errores viven aqui; reglas de negocio viven en `services/`.

### `app/services/`

Capa de aplicacion/dominio.

Responsabilidades:

- Auth, hashing, JWT y validacion de tokens.
- Reglas de salas, membresia y permisos.
- Creacion/listado de mensajes.
- Idempotencia.
- Flujo realtime de WebSocket.
- Traduccion de casos de dominio a excepciones especificas.

Los servicios orquestan repositorios y encapsulan decisiones del producto. Por ejemplo, `messages.py` valida membresia, construye el hash de idempotencia y maneja conflictos antes de persistir.

### `app/repositories/`

Capa de acceso a datos.

Responsabilidades:

- Encapsular queries SQLAlchemy.
- Crear, leer, actualizar y listar modelos.
- Mantener detalles de persistencia fuera de rutas y servicios.

Regla practica: los repositorios no deben decidir permisos ni reglas de negocio. Reciben parametros ya validados por servicios.

### `app/models/`

Modelos SQLAlchemy.

Responsabilidades:

- Definir tablas, columnas, relaciones e indices/constraints.
- Representar el estado persistido en Postgres.

Los modelos son la fuente para migraciones autogeneradas con Alembic, aunque cada migracion generada debe revisarse.

### `app/schemas/`

Schemas Pydantic de entrada/salida.

Responsabilidades:

- Validar payloads REST y WebSocket reutilizables.
- Normalizar campos simples, como `content.strip()` o nombres de salas.
- Definir respuestas publicas sin exponer secretos ni hashes.

### `app/infra/`

Infraestructura compartida.

Responsabilidades:

- Configuracion (`settings.py`).
- Conexion y sesiones de base de datos (`database.py`).
- Rate limiting (`rate_limit.py`).

Esta carpeta contiene integraciones tecnicas transversales, no reglas especificas de una entidad.

### `app/sockets/`

Estado y utilidades para conexiones WebSocket.

Responsabilidades:

- Agrupar conexiones activas por `room_id`.
- Hacer broadcast dentro de una sala.
- Cerrar conexiones de una sala eliminada.

### `app/alembic/`

Migraciones de base de datos.

- `versions/`: historial versionado de cambios de schema.
- `env.py`: configuracion de Alembic para cargar modelos y URL de base de datos.

### `app/tests/`

Suite backend.

Responsabilidades:

- Tests de auth, users, rooms, memberships, messages, idempotencia, rate limiting y WebSocket.
- Fixtures de base de datos y helpers de entidades.
- Validar contratos publicos y casos de error.

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

Clientes de integracion con el backend.

Responsabilidades:

- Construir requests HTTP.
- Centralizar `VITE_API_URL`.
- Construir URLs WebSocket.
- Mantener detalles de fetch fuera de componentes.

### `frontend/src/hooks/`

Estado y efectos reutilizables.

Responsabilidades:

- Auth client-side.
- Ciclo de vida WebSocket por sala.
- Envio y recepcion de eventos realtime.

### `frontend/src/pages/`

Pantallas conectadas a rutas.

Responsabilidades:

- Orquestar datos necesarios para una vista.
- Combinar hooks, clientes API y componentes.
- Manejar loading/error a nivel de pagina.

### `frontend/src/components/`

Componentes de UI reutilizables o especificos de pantalla.

Responsabilidades:

- Renderizar formularios, listas, banners e inputs.
- Emitir callbacks hacia paginas/hooks.
- Mantener logica visual separada de integraciones HTTP.

### `frontend/src/types/`

Tipos TypeScript compartidos.

Responsabilidades:

- Contratos del frontend para users, rooms, messages y eventos WebSocket.
- Reducir duplicacion entre clientes API, hooks y componentes.

## Flujo De Dependencias

Backend:

```text
routes -> services -> repositories -> models
   |          |              |
   |          |              `-- database session
   |          `-- schemas, infra, sockets segun el caso
   `-- dependencies, schemas
```

Frontend:

```text
pages -> hooks -> api
  |        |
  |        `-- types
  `-- components -> types
```

Reglas de direccion:

- Rutas dependen de servicios; servicios no dependen de rutas.
- Servicios dependen de repositorios; repositorios no dependen de servicios.
- Schemas pueden usarse en rutas y servicios, pero no deben importar rutas.
- Componentes UI no deberian construir URLs ni conocer detalles de fetch.
- Hooks pueden coordinar efectos y estado; componentes renderizan y delegan.

## Donde Agregar Codigo Nuevo

- Nuevo endpoint REST: `app/api/routes/`, schema en `app/schemas/`, reglas en `app/services/`, queries en `app/repositories/`.
- Nueva entidad persistida: modelo en `app/models/`, migracion en `app/alembic/versions/`, repositorio y tests.
- Nueva regla de negocio: `app/services/`.
- Nueva integracion transversal: `app/infra/`.
- Nuevo evento WebSocket: contrato en `docs/websocket.md`, manejo en `app/services/realtime.py` y transporte en `app/api/routes/websocket.py`.
- Nueva llamada frontend al backend: `frontend/src/api/`.
- Nuevo estado/effect compartido: `frontend/src/hooks/`.
- Nueva pantalla: `frontend/src/pages/`.
- Nueva pieza visual reutilizable: `frontend/src/components/`.
