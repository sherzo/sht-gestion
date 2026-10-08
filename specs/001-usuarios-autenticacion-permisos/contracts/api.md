# Contrato de la API: usuarios, autenticación y permisos

Prefijo `/api/v1`. JSON en inglés (ADR-0006). La fuente de verdad ejecutable es el
OpenAPI que genera FastAPI; este documento fija el comportamiento esperado y la matriz
de permisos que verifican las pruebas.

## Convenciones

- **Autenticación:** `Authorization: Bearer <access_token>` (R2). La renovación usa la
  cookie `sht_refresh` (R5); las peticiones con cookie exigen `Content-Type:
  application/json`.
- **Errores:** `{"detail": {"code": "<código>", "message": "<texto en español>"}}`. Los
  errores de validación (422) usan el mismo formato, con `fields` adicional:
  `{"detail": {"code": "validation_error", "message": "…", "fields": {"username": "…"}}}`.
- **Fechas:** ISO 8601 con zona horaria (UTC). El frontend las muestra en
  `America/Caracas`.

### Errores comunes

| HTTP | `code` | Cuándo |
|---|---|---|
| 401 | `not_authenticated` | Falta el token, es inválido o venció |
| 401 | `session_ended` | La sesión fue cerrada, revocada o pasó de 12 horas, o el usuario está inactivo |
| 403 | `forbidden` | El rol no tiene permiso (FR-010) |
| 403 | `password_change_required` | El usuario tiene contraseña temporal y la operación no está en la lista blanca (FR-016a) |
| 422 | `validation_error` | Datos inválidos |

### Respuesta de sesión (`SessionResponse`)

Devuelta por instalación, inicio de sesión y renovación; además fija la cookie
`sht_refresh`.

```json
{
  "access_token": "eyJ…",
  "token_type": "bearer",
  "expires_in": 900,
  "session_expires_at": "2026-10-08T10:30:00Z",
  "user": {
    "id": "0192…",
    "username": "maria",
    "full_name": "María Pérez",
    "role": "seller",
    "must_change_password": true
  }
}
```

## Endpoints

### Instalación (FR-001)

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `GET /setup/status` | — | `200 {"setup_required": bool}`; `true` solo si no hay usuarios y existe `SETUP_CODE` |
| `POST /setup` | `{setup_code, full_name, username, password}` | `201 SessionResponse` |

Errores de `POST /setup`: `409 setup_not_available` (ya hay usuarios o falta
`SETUP_CODE`), `403 invalid_setup_code`, `429 setup_locked` (5 fallos en 15 minutos).

### Sesión (FR-002 a FR-007)

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `POST /auth/login` | `{username, password}` | `200 SessionResponse` |
| `POST /auth/refresh` | `{}` (usa la cookie) | `200 SessionResponse` con token rotado |
| `POST /auth/logout` | `{}` | `204`; revoca la sesión y borra la cookie |
| `GET /auth/me` | — | `200` usuario (como `SessionResponse.user`) y `session_expires_at` |
| `POST /auth/password` | `{current_password, new_password}` | `204`; quita la marca temporal y revoca las **otras** sesiones |

Errores:

- `login`: `401 invalid_credentials` (mismo mensaje exista o no el usuario, y para
  usuarios inactivos), `423 account_locked` con `locked_until` tras 5 fallos seguidos
  con el mismo nombre, exista o no (FR-004).
- `refresh`: `401 session_ended` (cookie ausente, token desconocido, sesión vencida o
  revocada, reutilización detectada).
- `password` y `PUT /auth/pin`: `400 invalid_current_password`; al quinto fallo con la
  contraseña actual en la misma sesión, `401 session_ended` y la sesión se cierra.
  `password` además `422 validation_error` (menos de 8 caracteres, o igual a la actual).

### PIN del admin (FR-026 a FR-029)

| Método y ruta | Cuerpo | Respuesta |
|---|---|---|
| `PUT /auth/pin` | `{current_password, pin}` | `204`; `pin` de 4 a 6 dígitos |
| `POST /auth/pin/verify` | `{admin_username, pin}` | `200 {"authorized_by": {"id", "full_name"}}` |

Errores de `verify`: `403 pin_invalid` (PIN incorrecto, admin inexistente, inactivo o
sin PIN, con el mismo mensaje), `423 pin_locked` con `locked_until`. Las etapas
siguientes reutilizan el mismo servicio dentro de sus propias operaciones (por ejemplo,
el descuento autorizado de la etapa 1.3), para que la autorización y la acción ocurran
en la misma transacción.

### Usuarios (FR-015 a FR-019)

| Método y ruta | Cuerpo / parámetros | Respuesta |
|---|---|---|
| `GET /users` | `?role=&is_active=` | `200 [UserSummary]` ordenados por nombre |
| `POST /users` | `{full_name, username, role, password}` | `201 UserSummary`; contraseña temporal |
| `GET /users/{id}` | — | `200 UserSummary` |
| `PATCH /users/{id}` | `{full_name?, role?, is_active?}` | `200 UserSummary` |
| `POST /users/{id}/password` | `{new_password}` | `204`; temporal, revoca sus sesiones |

`UserSummary`: `{id, username, full_name, role, is_active, must_change_password,
has_pin, last_login_at, created_at}`.

Errores: `409 username_taken`, `409 cannot_reset_own_password` (el admin usa
`POST /auth/password`), `409 last_admin` (desactivar o cambiar el rol del último
admin activo), `409 cannot_deactivate_self`, `404 user_not_found`.

### Auditoría (FR-025)

| Método y ruta | Parámetros | Respuesta |
|---|---|---|
| `GET /audit-log` | `?user_id=&action=&date_from=&date_to=&page=1&page_size=50` | `200 {"items": [AuditEntry], "total": int, "page": int, "page_size": int}` |

- `date_from` y `date_to` son fechas (`AAAA-MM-DD`) en `America/Caracas`, inclusivas.
- `action` acepta un código exacto (`user.created`), varios separados por coma o un
  prefijo con punto (`auth.`).
- `page_size` máximo 100. Orden: más recientes primero.
- `AuditEntry`: `{id, occurred_at, user: {id, username, full_name} | null, action,
  entity_type, entity_id, before, after, reason, details}`.

### Salud (existente)

`GET /health` y `GET /health/db`, públicos.

## Matriz de permisos (SC-003)

`✅` permitido · `❌` 403 `forbidden` · anónimo sin token → 401 `not_authenticated`
salvo los públicos.

| Endpoint | Anónimo | Admin | Vendedor | Almacén | Con contraseña temporal |
|---|:-:|:-:|:-:|:-:|:-:|
| `GET /health`, `GET /health/db` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /setup/status`, `POST /setup` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /auth/login`, `POST /auth/refresh` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `POST /auth/logout`, `GET /auth/me`, `POST /auth/password` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `PUT /auth/pin` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `POST /auth/pin/verify` | ❌ | ✅ | ✅ | ✅ | ❌ |
| `GET/POST /users`, `GET/PATCH /users/{id}`, `POST /users/{id}/password` | ❌ | ✅ | ❌ | ❌ | ❌ |
| `GET /audit-log` | ❌ | ✅ | ❌ | ❌ | ❌ |

La última columna aplica a cualquier rol: con contraseña temporal solo se permiten las
filas marcadas (lista blanca de FR-016a).

Toda ruta nueva debe declarar su acceso (`public`, `require_authenticated` o
`require_roles`); la prueba de cobertura de permisos falla si falta (R9).
