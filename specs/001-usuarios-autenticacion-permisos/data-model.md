# Modelo de datos: usuarios, autenticación y permisos

Afina la sección 3.1 de `docs/modelo-de-datos.md` para esta etapa. Convenciones
generales (UUIDv7, enumeraciones como `text` con `CHECK`, `timestamptz`, nada se borra):
modelo de datos §1. Se aplica con la migración `0002_usuarios_y_auditoria`.

## `app_user` (RF-44, RF-45)

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid PK | UUIDv7 |
| `username` | text | Único. Normalizado en minúsculas; `^[a-z0-9._-]{3,30}$` (`CHECK`). No se reutiliza |
| `full_name` | text | 1–100 caracteres, sin espacios al inicio ni al final |
| `role` | text | `CHECK (role IN ('admin','seller','warehouse'))`. Exactamente uno (FR-009) |
| `password_hash` | text | Argon2id (R1) |
| `must_change_password` | bool | `true` si la contraseña la asignó un admin (FR-016a) |
| `pin_hash` | text, nulo | Solo admin: `CHECK (pin_hash IS NULL OR role = 'admin')` |
| `pin_failed_attempts` | int | ≥ 0 |
| `pin_locked_until` | timestamptz, nulo | Bloqueo de 15 min tras 5 fallos (FR-028) |
| `is_active` | bool | Desactivar en lugar de borrar |
| `last_login_at` | timestamptz, nulo | Para la lista de usuarios (FR-019) |
| `created_at`, `created_by` | timestamptz, uuid → `app_user` nulo | `created_by` nulo para el admin inicial |
| `updated_at` | timestamptz | |

**Invariantes del servicio (no expresables con `CHECK` simple):**

- Siempre existe al menos un admin activo (FR-018): desactivar o cambiar el rol del
  último admin activo se rechaza, con bloqueo de fila para que dos peticiones simultáneas
  no lo dejen en cero.
- Un admin no se desactiva a sí mismo (FR-018).
- Al dejar de ser admin, se borra `pin_hash` (el `CHECK` lo exige) y se audita.

**Estados:**

```text
           crear (admin)                   desactivar
[no existe] ──────────────▶ [activo, temporal] ────────────▶ [inactivo]
                               │   ▲                           │
              cambia su clave  │   │ admin restablece clave     │ reactivar
                               ▼   │                           ▼
                            [activo] ◀─────────────────────── (vuelve con su estado
                                                               de contraseña previo)
```

El administrador inicial nace `activo` sin contraseña temporal.

## `user_session` (FR-005, FR-006, FR-013; R4)

Una jornada de trabajo de un usuario en un navegador.

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid PK | Va en el JWT como `sid` |
| `user_id` | uuid → `app_user` | |
| `device_id` | uuid, nulo | Para la etapa 1.3 (equipos); sin FK hasta que exista `device` |
| `started_at` | timestamptz | Momento en que se ingresó la contraseña |
| `expires_at` | timestamptz | `started_at + 12 h`; `CHECK (expires_at > started_at)` |
| `revoked_at` | timestamptz, nulo | |
| `revoked_reason` | text, nulo | `CHECK` en `logout`, `password_changed`, `password_reset`, `user_deactivated`, `token_reuse` |
| `last_seen_at` | timestamptz | Última renovación |

Vigente si `revoked_at IS NULL AND expires_at > now()`. Índice por `(user_id)` para
revocar todas las sesiones de un usuario.

## `refresh_token` (R4)

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid PK | |
| `session_id` | uuid → `user_session` | |
| `token_hash` | text | SHA-256 del token; único |
| `created_at` | timestamptz | |
| `rotated_at` | timestamptz, nulo | Momento en que se usó y se reemplazó |
| `replaced_by_id` | uuid → `refresh_token`, nulo | |

Un token es utilizable si `rotated_at IS NULL` y su sesión está vigente. Si llega uno
con `rotated_at` hace más de 30 s, se revoca la sesión (`token_reuse`). No se borran:
el volumen es bajo (una fila cada 15 minutos por usuario conectado).

## `audit_log` (RF-46; solo inserción)

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | uuid PK | UUIDv7 (ordenable por tiempo) |
| `occurred_at` | timestamptz | `now()` de la transacción |
| `user_id` | uuid → `app_user`, nulo | Quién actuó; nulo en intentos anónimos y acciones de sistema |
| `device_id` | uuid, nulo | Etapa 1.3 |
| `action` | text | Código en inglés (tabla de abajo); `CHECK` de formato `^[a-z_]+\.[a-z_]+$` |
| `entity_type` | text, nulo | Ej. `app_user` |
| `entity_id` | uuid, nulo | |
| `before` | jsonb, nulo | Valores anteriores (sin contraseñas ni PIN) |
| `after` | jsonb, nulo | Valores nuevos (sin contraseñas ni PIN) |
| `reason` | text, nulo | Motivo, cuando la acción lo exige (etapas siguientes) |
| `details` | jsonb, nulo | Contexto adicional (ej. usuario probado en un intento fallido) |

- Trigger `audit_log_immutable`: `BEFORE UPDATE OR DELETE` → error.
- `sht_api` sin `DELETE` ni `TRUNCATE` (despliegue §3).
- Índices: `(occurred_at DESC)`, `(user_id, occurred_at DESC)`, `(action, occurred_at DESC)`
  y `((details->>'username'), occurred_at DESC) WHERE action IN ('auth.login_failed',
  'auth.login_succeeded')`, para calcular el bloqueo de inicio de sesión por nombre
  (FR-004, R6). El bloqueo de inicio de sesión no tiene columnas en `app_user`.

### Acciones auditadas en esta etapa (FR-020)

| `action` | Quién (`user_id`) | Elemento | `before` / `after` / `details` |
|---|---|---|---|
| `setup.admin_created` | El admin creado | `app_user` | `after`: usuario, nombre, rol |
| `setup.failed` | nulo | — | `details`: motivo (`invalid_code`) |
| `auth.login_succeeded` | El usuario | `app_user` | `details`: `username` (normalizado), `session_id` |
| `auth.login_failed` | El usuario si existe, si no nulo | `app_user` o — | `details`: `username` (normalizado, el probado), `consecutive_failures` |
| `auth.login_locked` | El usuario si existe, si no nulo | `app_user` o — | `details`: `username`, `locked_until` |
| `auth.password_changed` | El usuario | `app_user` | — |
| `auth.pin_set` | El admin | `app_user` | `details`: `first_time` (bool) |
| `auth.pin_verified` | Quien pidió la verificación | `app_user` (admin) | `details`: admin que autorizó |
| `auth.pin_failed` | Quien pidió la verificación | `app_user` (admin) | `details`: intentos |
| `auth.pin_locked` | Quien pidió la verificación | `app_user` (admin) | `details`: bloqueado hasta |
| `user.created` | El admin | `app_user` | `after`: usuario, nombre, rol |
| `user.updated` | El admin | `app_user` | `before`/`after`: nombre |
| `user.role_changed` | El admin | `app_user` | `before`/`after`: rol |
| `user.deactivated` | El admin | `app_user` | — |
| `user.reactivated` | El admin | `app_user` | — |
| `user.password_reset` | El admin, o nulo si fue por comando | `app_user` | `details`: `source` (`admin` o `cli`) |

Las etapas siguientes agregan sus acciones (`product.price_changed`, `sale.voided`,
`exchange_rate.corrected`, …) sin cambiar la tabla (FR-024).

## Relación con otras tablas

- `app_user` será referenciado por `sale.seller_id`, `created_by` de casi todas las
  tablas y `discount_authorization` (etapas 1.1b–1.4).
- `user_session.device_id` y `audit_log.device_id` reciben su FK cuando la etapa 1.3 cree
  `device`.
