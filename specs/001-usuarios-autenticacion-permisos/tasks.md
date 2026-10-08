---

description: "Tareas de la etapa 1.1a: usuarios, autenticación y permisos"
---

# Tasks: Usuarios, autenticación y permisos (etapa 1.1a)

**Input**: documentos de diseño en `specs/001-usuarios-autenticacion-permisos/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R14), data-model.md, contracts/api.md, quickstart.md

**Tests**: se incluyen. La especificación los exige (SC-003: matriz de permisos con pruebas automatizadas) y la constitución también (principio VII: permisos por rol en el servidor). Cada prueba nombra en su docstring el RF del PRD y el FR/SC de la especificación que verifica (tabla de abajo). Las pruebas de cada historia se escriben primero y deben fallar antes de implementar.

**Organization**: tareas agrupadas por historia de usuario de spec.md (US1–US5), cada una probable por separado.

**Trazabilidad con el PRD** (constitución, "Flujo de trabajo" y principio VII):

| FR de la especificación | RF/RN/RNF del PRD |
|---|---|
| FR-001 a FR-008 | RF-44, RNF-05 |
| FR-009 a FR-014 | RNF-05 (matriz de permisos del PRD §4) |
| FR-015 a FR-019 y FR-016a | RF-45 |
| FR-020 a FR-025 | RF-46, RNF-08 |
| FR-026 a FR-029 | RF-44, RN-07 |
| FR-030 y FR-031 | RNF-02, RNF-07 |

Los commits y las docstrings de las pruebas citan el RF del PRD y el FR de la especificación, por ejemplo `RF-44/FR-004`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US5)
- Rutas relativas a la raíz del repositorio

## Path Conventions

- Backend: `backend/app/`, `backend/tests/`, `backend/migrations/`
- App interna: `frontend/src/`
- Compartido: `packages/shared/src/`
- Comandos del backend desde `backend/` (`uv run …`); los de Node desde la raíz (`pnpm …`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias y configuración que todo lo demás usa.

- [X] T001 Agregar dependencias del backend con `uv add argon2-cffi pyjwt tzdata` en `backend/pyproject.toml` y `backend/uv.lock` (R1, R2; `tzdata` hace falta para `zoneinfo` en Windows y en la imagen slim)
- [X] T002 [P] Agregar `lucide-react` a `frontend/package.json` con `pnpm add lucide-react --filter @sht/frontend` (R12)
- [X] T003 [P] Agregar `openapi-typescript` como dependencia de desarrollo de la raíz y el script `"api:types"` en `package.json` que ejecuta `scripts/api-types.mjs`: exporta el OpenAPI con `uv run python -c "import json; from app.main import app; print(json.dumps(app.openapi()))"` (en `backend/`) a un archivo temporal y genera `packages/shared/src/api/schema.d.ts` (R12)
- [X] T004 [P] Documentar las variables nuevas en `backend/.env.example`: `JWT_SECRET` (cadena aleatoria larga), `SETUP_CODE`, `REFRESH_COOKIE_SAMESITE=lax`, `REFRESH_COOKIE_SECURE=false`, con comentarios en español (R5, R7)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelo de datos, seguridad, auditoría, declaración de permisos y base de pruebas que necesitan todas las historias.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T005 Ampliar `Settings` en `backend/app/core/config.py`: `jwt_secret: SecretStr | None`, `setup_code: SecretStr | None`, `access_token_minutes = 15`, `session_hours = 12`, `refresh_reuse_grace_seconds = 30`, `refresh_cookie_name = "sht_refresh"`, `refresh_cookie_samesite: Literal["strict","lax","none"] = "strict"`, `refresh_cookie_secure = True`, `refresh_cookie_domain: str | None = None`, `argon2_time_cost`, `argon2_memory_cost`, `argon2_parallelism` (por defecto los de `argon2-cffi`); un validador que exige `jwt_secret` cuando `environment` es `staging` o `production` (R2, R5)
- [X] T006 [P] Crear `backend/app/core/clock.py` con `utcnow() -> datetime` (con zona UTC), el único reloj que usan los servicios para que las pruebas puedan simular el paso del tiempo (12 horas, 15 minutos, 30 segundos)
- [X] T007 [P] Crear `backend/app/core/errors.py` con `ApiError(status_code, code, message, **extra)` y registrar en `backend/app/main.py` los manejadores: `ApiError` → `{"detail": {"code", "message", …extra}}`; `RequestValidationError` → 422 `{"detail": {"code": "validation_error", "message": "Hay datos inválidos", "fields": {campo: mensaje en español}}}` (contrato, "Convenciones")
- [X] T008 [P] Crear `backend/app/domain/roles.py` con `class Role(StrEnum)`: `ADMIN = "admin"`, `SELLER = "seller"`, `WAREHOUSE = "warehouse"` (FR-009)
- [X] T009 [P] Crear `backend/app/domain/lockout.py` con `MAX_ATTEMPTS = 5`, `LOCK_MINUTES = 15`, `is_locked(locked_until, now) -> bool` y `register_failure(attempts, now) -> tuple[int, datetime | None]` (al quinto fallo seguido devuelve el bloqueo hasta `now + 15 min`; lo usa el PIN) y `login_locked_until(consecutive_failures, last_failure_at) -> datetime | None` (con 5 o más fallos desde el último acierto, bloqueo hasta `last_failure_at + 15 min`; lo usa el inicio de sesión), y sus pruebas unitarias en `backend/tests/test_lockout.py` (FR-004, FR-028, R6)
- [X] T010 [P] Crear `backend/app/domain/business_time.py` con `CARACAS = ZoneInfo("America/Caracas")`, `business_date(instant) -> date` y `day_bounds_utc(start: date, end: date) -> tuple[datetime, datetime]` (inicio del primer día y fin exclusivo del último, en UTC), y sus pruebas en `backend/tests/test_business_time.py`, incluido un instante de las 23:30 de Caracas que en UTC ya es el día siguiente (arquitectura §4.2, R10)
- [X] T011 [P] Crear `backend/app/core/security.py`: `PasswordHasher` de Argon2id con los parámetros de `Settings`; `hash_secret`/`verify_secret` (contraseñas y PIN), `verify_dummy()` contra un hash de referencia para igualar tiempos con usuarios inexistentes (FR-003); `create_access_token(user_id, session_id, role)` HS256 con `sub`, `sid`, `role`, `exp` a 15 minutos; `decode_access_token`; `new_refresh_token() -> tuple[str, str]` (32 bytes con `secrets.token_urlsafe` y su SHA-256 en hexadecimal); `hash_refresh_token(token)` (R1, R2, R4)
- [X] T012 Crear `backend/app/db/base.py` (`DeclarativeBase` con convención de nombres de restricciones) y `backend/app/db/models.py` con `AppUser`, `UserSession`, `RefreshToken` y `AuditLog` exactamente como en data-model.md: `id` UUIDv7 con `uuid.uuid7()`; `username` "Único. Normalizado en minúsculas; `^[a-z0-9._-]{3,30}$`"; `full_name` "1–100 caracteres"; `role` `CHECK (role IN ('admin','seller','warehouse'))`; `pin_hash` `CHECK (pin_hash IS NULL OR role = 'admin')`; contadores `≥ 0`; `user_session.expires_at` `CHECK (expires_at > started_at)`; `revoked_reason` en `logout`, `password_changed`, `password_reset`, `user_deactivated`, `token_reuse`; `refresh_token.token_hash` único; `audit_log.action` con `CHECK` de formato `^[a-z_]+\.[a-z_]+$`; `before`, `after`, `details` como `jsonb`. Apuntar `target_metadata = Base.metadata` en `backend/migrations/env.py`
- [X] T013 Crear la migración `backend/migrations/versions/0002_usuarios_y_auditoria.py` (revisión `0002`, anterior `0001`) con las cuatro tablas, sus `CHECK`, el índice único de `username`, los índices `user_session(user_id)`, `audit_log(occurred_at DESC)`, `audit_log(user_id, occurred_at DESC)`, `audit_log(action, occurred_at DESC)`, el índice parcial `audit_log((details->>'username'), occurred_at DESC) WHERE action IN ('auth.login_failed', 'auth.login_succeeded')` (R6), y la función más el trigger `audit_log_immutable` `BEFORE UPDATE OR DELETE` que lanza error; `downgrade` lo quita todo. Comprobar `alembic upgrade head`, `downgrade base` y `upgrade head` contra el Postgres local (R10, FR-023)
- [X] T014 Agregar en `backend/app/db/session.py` un `sessionmaker` y la dependencia `get_db()` que entrega una `Session` por petición y hace rollback si hay una excepción; los servicios confirman con `commit()` explícito
- [X] T015 Crear `backend/app/services/audit.py` con `record_audit(db, *, action, user_id=None, entity_type=None, entity_id=None, before=None, after=None, reason=None, details=None)`, que agrega el registro a la sesión actual sin confirmar (misma transacción que la acción, FR-022) y rechaza con error cualquier clave que contenga `password` o `pin` salvo booleanos de metadatos permitidos (`first_time`) (FR-021)
- [X] T016 Crear `backend/app/api/deps.py`: `public()`, `require_authenticated(allow_temporary_password=False)` y `require_roles(*roles)`, cada una una dependencia de FastAPI marcada con el atributo `access` para la prueba de cobertura. `current_user` lee el Bearer, valida el JWT y en una sola consulta trae `AppUser` y `UserSession` (`sid`). Responde 401 `not_authenticated` (token ausente o inválido), 401 `session_ended` (usuario inactivo, sesión revocada o `expires_at <= utcnow()`), 403 `password_change_required` (contraseña temporal fuera de la lista blanca) y 403 `forbidden` (rol de la base de datos, no del token, fuera de los permitidos). Devuelve `CurrentUser(user, session)` (R3, FR-010, FR-013, FR-016a)
- [X] T017 Declarar `public()` en `backend/app/api/health.py` (los dos endpoints) y preparar en `backend/app/main.py` el registro de los routers `setup`, `auth`, `users` y `audit` a medida que existan
- [X] T018 Crear `backend/tests/conftest.py`: salta las pruebas `db` sin `DATABASE_URL`; aplica `alembic upgrade head` una vez por sesión; antes de cada prueba hace `TRUNCATE app_user, user_session, refresh_token, audit_log CASCADE`; fija `JWT_SECRET`, `SETUP_CODE=codigo-de-prueba`, Argon2 con costo mínimo y `REFRESH_COOKIE_SECURE=false`; fixture `clock` que reemplaza `app.core.clock.utcnow`; fábricas `make_user(role, *, username, password="clave-segura-1", must_change_password=False, is_active=True)` y `auth_headers(user)` (inicia sesión por la API y devuelve el encabezado Bearer); y un router solo de pruebas montado en `/api/v1/_test/` con `admin-only` (`require_roles(Role.ADMIN)`) y `any-user` (`require_authenticated()`), para probar permisos sin depender de otras historias
- [X] T019 Crear `backend/tests/test_route_declarations.py`: recorre `app.routes` (`APIRoute`) y falla si alguna ruta no tiene exactamente una dependencia con atributo `access` (FR-011, R9)
- [X] T020 [P] Crear en `packages/shared/src/format.ts` la función `formatDateTime(iso: string): string` con formato `dd/mm/aaaa hh:mm` en `America/Caracas` usando `Intl.DateTimeFormat("es-VE", …)`, y exportarla desde `packages/shared/src/index.ts` (RNF-07)
- [X] T021 [P] Crear `packages/shared/src/roles.ts` con `type Role = "admin" | "seller" | "warehouse"` y `ROLE_LABELS` (`Administrador`, `Vendedor`, `Almacén`), exportados desde `packages/shared/src/index.ts`
- [X] T022 [P] Crear los componentes base en `frontend/src/components/ui/` según `docs/guia-de-estilos.md`: `button.tsx` (variantes `primary`, `accent`, `secondary`, `danger`; alto mínimo 44 px; estado de carga), `field.tsx` (etiqueta, campo, ayuda y error accesibles con `aria-describedby`), `alert.tsx` (`success`, `warning`, `danger`, `info` sobre su fondo suave, con ícono de `lucide-react` y texto), `dialog.tsx` (`<dialog>` nativo con foco atrapado y cierre con Escape) y `data-table.tsx` (tabla en PC y tarjetas apiladas por debajo de 640 px)

**Checkpoint**: base lista. `uv run pytest` pasa (lockout, fecha de negocio, declaración de rutas) y la migración sube y baja.

---

## Phase 3: User Story 1 - Puesta en marcha e inicio de sesión (Priority: P1) 🎯 MVP

**Goal**: instalar el sistema con el código, entrar y salir con usuario y contraseña, mantener la jornada de 12 horas y cambiar la propia contraseña.

**Independent Test**: con la base vacía, instalar el admin con el código, cerrar sesión, volver a entrar, comprobar que se rechazan credenciales incorrectas y que la sesión se renueva sin pedir contraseña hasta las 12 horas.

### Tests for User Story 1 ⚠️

> Escribir primero y comprobar que fallan.

- [X] T023 [P] [US1] Pruebas de instalación en `backend/tests/test_setup.py`: `GET /setup/status` vale `true` solo con base vacía y `SETUP_CODE` definido; código incorrecto → 403 `invalid_setup_code` y registro `setup.failed`; 5 fallos en 15 minutos → 429 `setup_locked`; código correcto → 201 con `SessionResponse`, cookie `sht_refresh` y registro `setup.admin_created`; segunda instalación → 409 `setup_not_available`; sin `SETUP_CODE` → 409 (FR-001, US1 escenarios 1–3)
- [X] T024 [P] [US1] Pruebas de sesión en `backend/tests/test_auth_session.py`: inicio de sesión sin distinguir mayúsculas; contraseña incorrecta, usuario inexistente y usuario inactivo → 401 `invalid_credentials` con el mismo mensaje; 5 fallos → 423 `account_locked` aunque luego la contraseña sea correcta, y se libera a los 15 minutos (`clock`); un nombre inexistente también se bloquea tras 5 fallos, con la misma respuesta 423 que uno real (FR-003, FR-004); un acierto reinicia la cuenta; registros `auth.login_succeeded`, `auth.login_failed` (con `username` normalizado) y `auth.login_locked`; `last_login_at` actualizado; `refresh` rota el token; pasadas 12 horas desde el ingreso `refresh` → 401 `session_ended` aunque se haya renovado (SC-008); reutilizar un token rotado hace más de 30 s revoca la sesión y uno rotado hace menos de 30 s no; `refresh` sin `Content-Type: application/json` se rechaza; `logout` → 204 y el token de acceso deja de servir de inmediato (401 `session_ended`); `GET /auth/me` devuelve el usuario y `session_expires_at` (FR-002 a FR-006, SC-006)
- [X] T025 [P] [US1] Pruebas de cambio de contraseña propia en `backend/tests/test_password.py`: contraseña actual incorrecta → 400 `invalid_current_password`; menos de 8 caracteres o igual a la actual → 422; éxito → 204, quita `must_change_password`, revoca las otras sesiones del usuario pero no la actual, y registra `auth.password_changed` sin contraseñas en `before`/`after`/`details` (FR-007, FR-008, FR-016a)

### Implementation for User Story 1

- [X] T026 [US1] Crear `backend/app/services/auth.py`: `setup_status`, `setup_admin` (compara con `hmac.compare_digest`, `pg_advisory_xact_lock`, comprueba que no existan usuarios, cuenta los `setup.failed` de los últimos 15 minutos desde `audit_log`), `login` (normaliza el usuario, `verify_dummy()` si no existe, bloqueo calculado desde `audit_log` por nombre normalizado, exista o no, con `domain/lockout.login_locked_until` como regla; durante el bloqueo no verifica la contraseña y audita `auth.login_locked`; los fallos se confirman en su propia transacción antes de responder el error; pone `last_login_at` al entrar), `start_session` (crea `user_session` con `expires_at = started_at + 12 h` y el primer `refresh_token`), `refresh` (rotación, ventana de 30 s, revocación por `token_reuse`, nunca pasa de `expires_at`), `logout`, `change_password` y `revoke_user_sessions(user_id, reason, except_session_id=None)`, todo con `record_audit` en la misma transacción (R4, R6, R7, FR-001 a FR-007)
- [X] T027 [US1] Crear `backend/app/api/setup.py` (`GET /setup/status`, `POST /setup`, ambos `public()`) y `backend/app/api/auth.py` (`POST /auth/login` y `POST /auth/refresh` `public()`; `POST /auth/logout`, `GET /auth/me` y `POST /auth/password` con `require_authenticated(allow_temporary_password=True)`), con los esquemas Pydantic del contrato (`SessionResponse`, usuario de sesión), el helper que fija y borra la cookie con nombre, ruta `/api/v1/auth`, `HttpOnly`, `SameSite`, `Secure` y dominio de `Settings`, y la exigencia de `Content-Type: application/json` en `refresh` y `logout`. Registrar los routers en `backend/app/main.py`
- [X] T028 [US1] Crear `frontend/src/lib/api/client.ts`: `apiFetch` con base `NEXT_PUBLIC_API_URL`, encabezado `Authorization` con el token en memoria, `credentials: "include"` solo en `/auth/*` y `/setup`, `Content-Type: application/json`, renovación única ante 401 `not_authenticated` seguida de un reintento, y clase `ApiError` con `status`, `code`, `message` y `fields`
- [X] T029 [US1] Crear `frontend/src/lib/auth/auth-context.tsx` y `frontend/src/lib/auth/use-auth.ts`: estado `loading | anonymous | authenticated | setup_required`; al montar consulta `/setup/status` y luego `POST /auth/refresh`; `login`, `logout`, `setSession`; renovación programada antes de `expires_in` y serializada entre pestañas con `navigator.locks.request("sht-refresh", …)`; token solo en memoria (R4, R12). Envolver la app con el proveedor en `frontend/src/app/layout.tsx`
- [X] T030 [US1] Crear `frontend/src/components/require-auth.tsx`: muestra carga mientras `loading`; redirige a `/instalacion` si `setup_required`, a `/ingresar` si `anonymous` y a `/cambiar-clave` si `must_change_password`; acepta `roles?: Role[]` y, si el rol no está, muestra "No tienes permiso para ver esta sección" (solo oculta, el servidor protege)
- [X] T031 [P] [US1] Crear `frontend/src/app/instalacion/page.tsx`: formulario con código de instalación, nombre completo, usuario, contraseña y confirmación; mensajes para `invalid_setup_code`, `setup_locked` y `setup_not_available`; al terminar entra como Admin y va a `/`
- [X] T032 [P] [US1] Crear `frontend/src/app/ingresar/page.tsx`: logo, usuario y contraseña; mensaje genérico para `invalid_credentials`; aviso con la hora de desbloqueo para `account_locked`; aviso "Para iniciar sesión necesitas conexión a internet" si `navigator.onLine` es `false`
- [X] T033 [P] [US1] Crear `frontend/src/app/cambiar-clave/page.tsx`: contraseña actual, nueva y confirmación (mínimo 8 caracteres, distinta de la actual); en modo obligatorio explica por qué debe cambiarla y no muestra el menú; al terminar va a `/`
- [X] T034 [US1] Crear `frontend/src/components/app-shell.tsx` (barra superior `bg-primary` con `logo-horizontal-negativo.svg`, nombre y rol del usuario y botón "Cerrar sesión") y reemplazar `frontend/src/app/page.tsx` por la página de inicio protegida con `RequireAuth` dentro de `AppShell`, con saludo, rol y hora de vencimiento de la jornada (`formatDateTime`)
- [X] T035 [US1] Ejecutar `pnpm api:types` para generar `packages/shared/src/api/schema.d.ts` y tipar con él las respuestas usadas en `frontend/src/lib/api/client.ts` y `frontend/src/lib/auth/`

**Checkpoint**: US1 funciona sola: instalación, ingreso, renovación, cierre de sesión y cambio de contraseña, en la API y en la app.

---

## Phase 4: User Story 2 - Permisos por rol verificados en el servidor (Priority: P1)

**Goal**: cada operación se autoriza en el servidor según la matriz; los cambios de rol o estado rigen desde la siguiente petición; el menú muestra solo lo permitido.

**Independent Test**: con un usuario de cada rol, uno con contraseña temporal y una petición sin sesión, recorrer los endpoints de la matriz y comprobar respuestas permitidas, 401 o 403 según `contracts/api.md`.

### Tests for User Story 2 ⚠️

- [X] T036 [P] [US2] Crear `backend/tests/test_permissions_matrix.py` dirigido por datos: una tabla `MATRIX` con `(método, ruta, cuerpo de ejemplo, actores permitidos)` para los actores `anonymous`, `admin`, `seller`, `warehouse` y `temporary_password`, con las filas de `contracts/api.md` de salud, instalación y sesión; por cada fila y actor verifica 401 `not_authenticated`, 403 `forbidden`, 403 `password_change_required` o una respuesta distinta de 401/403. Las historias siguientes agregan sus filas (SC-003, FR-010, FR-012, FR-016a)
- [X] T037 [P] [US2] Crear `backend/tests/test_session_revocation.py` con las rutas de prueba `/_test/`: desactivar al usuario en la base → su siguiente petición da 401 `session_ended`; cambiar su rol de `admin` a `seller` → `admin-only` da 403 en la siguiente petición sin renovar el token; un JWT con `role: "admin"` de un usuario `seller` no da acceso (el rol sale de la base) (FR-013, SC-004, R3)

### Implementation for User Story 2

- [X] T038 [US2] Agregar en `frontend/src/components/app-shell.tsx` la configuración `NAV_ITEMS` (`Inicio` y `Mi cuenta` para todos los roles; `Usuarios` y `Auditoría` solo admin) con íconos de `lucide-react`, mostrando únicamente los ítems del rol actual, como barra lateral en PC y menú desplegable en el teléfono (US2 escenario 5)
- [X] T039 [US2] En `frontend/src/lib/api/client.ts` y `frontend/src/lib/auth/`: ante 401 `session_ended`, o si falla la renovación, abrir un diálogo de reingreso (`frontend/src/components/reauth-dialog.tsx`) sobre la página actual, sin desmontarla ni perder lo escrito, y al entrar reintentar la petición pendiente. Si entra un usuario distinto al anterior, descartar la petición pendiente e ir a `/`. Si el reingreso falla porque el usuario fue desactivado (`invalid_credentials`) o el usuario elige "Salir", cerrar la sesión local y redirigir a `/ingresar`. Ante 403 `forbidden`, mostrar un mensaje de permiso insuficiente (caso límite "Sesión vencida a mitad de un trabajo", US2 escenarios 1 y 4)

**Checkpoint**: la matriz y la revocación pasan; el menú de Vendedor y Almacén no muestra Usuarios ni Auditoría.

---

## Phase 5: User Story 3 - Gestión de usuarios por el admin (Priority: P2)

**Goal**: el admin crea, edita, cambia de rol, desactiva y reactiva usuarios y restablece contraseñas temporales; el único admin se recupera por comando.

**Independent Test**: como Admin, crear un Vendedor, entrar con él (debe cambiar la contraseña), desactivarlo desde otra sesión y comprobar que pierde el acceso; reactivarlo y restablecerle la contraseña.

### Tests for User Story 3 ⚠️

- [X] T040 [P] [US3] Crear `backend/tests/test_users.py`: alta con contraseña temporal (`must_change_password = true`) y registro `user.created`; `username` normalizado a minúsculas y validado con `^[a-z0-9._-]{3,30}$` (422 si no cumple); duplicado sin distinguir mayúsculas → 409 `username_taken`, también contra usuarios inactivos; lista filtrable por `role` e `is_active`, ordenada por nombre; `GET /users/{id}` inexistente → 404 `user_not_found`; cambio de nombre → `user.updated` con `before`/`after`; cambio de rol → `user.role_changed` y, si deja de ser admin, `pin_hash` queda nulo; desactivar → revoca sus sesiones (`user_deactivated`) y registra `user.deactivated`; reactivar → `user.reactivated`; desactivarse a sí mismo → 409 `cannot_deactivate_self`; desactivar o cambiar el rol del último admin activo → 409 `last_admin`; restablecer contraseña → temporal, revoca sesiones (`password_reset`), registra `user.password_reset` con `source: "admin"` y sin contraseñas; un usuario con contraseña temporal recibe 403 `password_change_required` en `GET /users` hasta cambiarla (FR-015 a FR-019, FR-016a, SC-009)
- [X] T041 [P] [US3] Crear `backend/tests/test_cli.py`: `reset-password <usuario>` deja una contraseña temporal que permite entrar, revoca las sesiones y registra `user.password_reset` con `user_id` nulo y `source: "cli"`; usuario inexistente → código de salida distinto de 0 (R8)
- [X] T042 [US3] Agregar a `MATRIX` en `backend/tests/test_permissions_matrix.py` las filas de `/users` y `/users/{id}` del contrato (solo admin)

### Implementation for User Story 3

- [X] T043 [US3] Crear `backend/app/services/users.py`: `list_users(role, is_active)`, `get_user`, `create_user` (contraseña temporal), `update_user(full_name, role, is_active)` con bloqueo `FOR UPDATE` de los admins activos para garantizar "Siempre existe al menos un admin activo", rechazo de la autodesactivación, borrado de `pin_hash` al dejar de ser admin, revocación de sesiones al desactivar, y `reset_password` (temporal más revocación), todo con `record_audit` en la misma transacción (FR-015 a FR-018, data-model "Invariantes del servicio")
- [X] T044 [US3] Crear `backend/app/api/users.py` con `GET /users`, `POST /users`, `GET /users/{id}`, `PATCH /users/{id}` y `POST /users/{id}/password`, todos `require_roles(Role.ADMIN)`, con `UserSummary` (`id, username, full_name, role, is_active, must_change_password, has_pin, last_login_at, created_at`) y los errores del contrato; registrar el router en `backend/app/main.py`
- [X] T045 [US3] Crear `backend/app/cli.py` (`uv run python -m app.cli reset-password <usuario>`): genera una contraseña temporal con `secrets`, la aplica con `services/users.reset_password` como acción de sistema (`user_id` nulo, `source: "cli"`) y la imprime una sola vez (R8)
- [X] T046 [US3] Crear `frontend/src/app/usuarios/page.tsx` (con `RequireAuth roles={["admin"]}`): `DataTable` con nombre, usuario, rol (`ROLE_LABELS`), estado, marca "Contraseña temporal" y último ingreso (`formatDateTime`); filtros por rol y estado; diálogo "Nuevo usuario" (nombre, usuario, rol, contraseña inicial); diálogo de edición (nombre, rol, activo) con los mensajes de `last_admin`, `cannot_deactivate_self` y `username_taken`; diálogo "Restablecer contraseña" que avisa que el usuario deberá cambiarla
- [X] T047 [US3] Ejecutar `pnpm api:types` y tipar las llamadas de `frontend/src/app/usuarios/page.tsx`

**Checkpoint**: US3 funciona sola y la matriz incluye los endpoints de usuarios.

---

## Phase 6: User Story 4 - PIN del admin para autorizaciones (Priority: P2)

**Goal**: cada admin define y cambia su PIN; el sistema verifica un PIN con bloqueo y registra quién autorizó.

**Independent Test**: como Admin, definir el PIN, verificar uno correcto y uno incorrecto, y comprobar que tras 5 fallos queda bloqueado aunque luego se ingrese el correcto.

### Tests for User Story 4 ⚠️

- [X] T048 [P] [US4] Crear `backend/tests/test_pin.py`: `PUT /auth/pin` exige la contraseña actual (400 `invalid_current_password`) y un PIN de 4 a 6 dígitos (422); registra `auth.pin_set` con `first_time`; un Vendedor recibe 403; `POST /auth/pin/verify` correcto → 200 con `authorized_by` y registro `auth.pin_verified` con quien pidió y el admin que autorizó; PIN incorrecto, admin inexistente, inactivo o sin PIN → 403 `pin_invalid` con el mismo mensaje; 5 fallos → 423 `pin_locked` aunque luego sea correcto, liberado a los 15 minutos (`clock`); un acierto reinicia el contador; registros `auth.pin_failed` y `auth.pin_locked` sin el PIN (FR-026 a FR-029, SC-006)
- [X] T049 [US4] Agregar a `MATRIX` en `backend/tests/test_permissions_matrix.py` las filas `PUT /auth/pin` (solo admin) y `POST /auth/pin/verify` (los tres roles, no con contraseña temporal)

### Implementation for User Story 4

- [X] T050 [US4] Crear `backend/app/services/pin.py` con `set_pin(db, user, current_password, pin)` y `verify_admin_pin(db, requester, admin_username, pin) -> AppUser`, reutilizable por la etapa 1.3 dentro de sus propias transacciones; los fallos actualizan el contador y se auditan en una transacción propia antes de devolver el error (R6, R10)
- [X] T051 [US4] Agregar en `backend/app/api/auth.py` `PUT /auth/pin` (`require_roles(Role.ADMIN)`) y `POST /auth/pin/verify` (`require_authenticated()`), con los errores `pin_invalid` y `pin_locked` (con `locked_until`) del contrato
- [X] T052 [US4] Crear `frontend/src/app/mi-cuenta/page.tsx` (todos los roles): datos del usuario, enlace a "Cambiar contraseña" y, solo para admin, sección "PIN de autorización" para definirlo o cambiarlo con la contraseña actual, más "Probar PIN" con el resultado (autorizado, incorrecto o bloqueado hasta `hh:mm`)
- [X] T053 [US4] Ejecutar `pnpm api:types` y tipar las llamadas de `frontend/src/app/mi-cuenta/page.tsx`

**Checkpoint**: US4 funciona sola; el servicio de verificación queda listo para los descuentos de la etapa 1.3.

---

## Phase 7: User Story 5 - Registro y consulta de auditoría (Priority: P3)

**Goal**: toda acción sensible queda registrada de forma inmutable y el admin la consulta con filtros.

**Independent Test**: realizar acciones con distintos usuarios, comprobar que aparecen en `/auditoria` con usuario, fecha y detalle; que no se pueden modificar; y que una acción cuyo registro falla no ocurre.

### Tests for User Story 5 ⚠️

- [X] T054 [P] [US5] Crear `backend/tests/test_audit.py`: un recorrido completo (instalación, ingresos, alta, cambio de rol, desactivación, restablecimiento, cambio de contraseña, PIN) genera todas las acciones de FR-020; ninguna fila de `audit_log` contiene en `before`, `after` o `details` las contraseñas ni el PIN usados (SC-005); `UPDATE` y `DELETE` sobre `audit_log` fallan en la base (FR-023); si `record_audit` lanza un error, el usuario no se crea (FR-022); `GET /audit-log` filtra por `user_id`, por `action` exacta y por prefijo (`auth.`), y por `date_from`/`date_to` en hora de Caracas (un registro de las 23:30 del 07/10 en Caracas entra en el filtro del 07/10); orden de más reciente a más antiguo; paginación con `total`; `page_size` mayor que 100 → 422
- [X] T055 [US5] Agregar a `MATRIX` en `backend/tests/test_permissions_matrix.py` la fila `GET /audit-log` (solo admin)

### Implementation for User Story 5

- [X] T056 [US5] Agregar en `backend/app/services/audit.py` `query_audit(db, user_id, action, date_from, date_to, page, page_size)`, usando `domain/business_time.day_bounds_utc` y aceptando prefijo de acción cuando el valor termina en `.`
- [X] T057 [US5] Crear `backend/app/api/audit.py` con `GET /audit-log` (`require_roles(Role.ADMIN)`), validación de `page_size` entre 1 y 100 y `AuditEntry` con el usuario (`id, username, full_name`) del contrato; registrar el router en `backend/app/main.py`
- [X] T058 [P] [US5] Crear `packages/shared/src/audit-actions.ts` con `AUDIT_ACTION_LABELS` en español para las 16 acciones de data-model.md (ej. `user.role_changed` → "Cambio de rol") y su agrupación (`Instalación`, `Sesión`, `PIN`, `Usuarios`), exportado desde `packages/shared/src/index.ts`
- [X] T059 [US5] Crear `frontend/src/app/auditoria/page.tsx` (con `RequireAuth roles={["admin"]}`): filtros por usuario (lista de `/users`), tipo de acción (agrupado) y rango de fechas; `DataTable` con fecha (`formatDateTime`), usuario, acción (`AUDIT_ACTION_LABELS`) y un resumen legible de `before`/`after`/`details`; paginación; estado vacío "No hay registros con estos filtros"
- [X] T060 [US5] Ejecutar `pnpm api:types` y tipar las llamadas de `frontend/src/app/auditoria/page.tsx`

**Checkpoint**: las cinco historias funcionan; la matriz cubre los 15 endpoints nuevos más los de salud.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: despliegue, documentación (RNF-09) y validación final.

- [X] T061 Actualizar `.github/workflows/deploy-api.yml`: agregar `JWT_SECRET=jwt-secret:latest,SETUP_CODE=setup-code:latest` a `--set-secrets` y `REFRESH_COOKIE_SAMESITE=none@REFRESH_COOKIE_SECURE=true` a `--set-env-vars` (configuración provisional sin dominio propio, R5)
- [X] T062 **Manual (dueño), antes de integrar a `main`:** crear en Secret Manager los secretos `jwt-secret` (64 caracteres hexadecimales aleatorios) y `setup-code`, y dar a la cuenta de servicio de la API el rol `roles/secretmanager.secretAccessor` sobre ambos, siguiendo el procedimiento de T064
- [X] T063 [P] Actualizar `docs/PRD.md` a v0.7: precisar en RF-44 la jornada de 12 horas y la instalación con código, y en RF-45 la contraseña temporal; agregar la línea al historial (principio V, R14)
- [X] T064 [P] Actualizar `docs/despliegue.md`: secretos `jwt-secret` y `setup-code` (creación, permisos, rotación), instalación inicial y destrucción de `setup-code` después, recuperación del único admin con `uv run python -m app.cli reset-password <usuario>` usando la cadena de migraciones, configuración de la cookie según el ambiente y la limitación de Safari sin dominio propio (R5, R7, R8)
- [X] T065 [P] Actualizar `docs/modelo-de-datos.md` §3.1 con las columnas nuevas de `app_user`, la tabla `user_session`, el `refresh_token` ajustado y el `audit_log` con `details` (data-model.md)
- [X] T066 [P] Actualizar `docs/arquitectura.md`: glosario (sesión `user_session`, código de instalación, contraseña temporal), convención de declaración de permisos por endpoint (§4.4 y §5) y regla de esquemas de respuesta por rol para la etapa 1.1b (R9)
- [X] T067 [P] Actualizar `docs/guia-de-estilos.md` §9 (y la sección de componentes): componentes base de `frontend/src/components/ui/`, íconos `lucide-react` y patrón de menú por rol (R12)
- [X] T068 [P] Actualizar `CHANGELOG.md` en "Sin publicar" con la etapa 1.1a (RF-44, RF-45, RF-46) y `docs/plan-de-fases.md` con el estado de la 1.1a
- [X] T069 Ejecutar `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest` (con `DATABASE_URL`), la migración subir–bajar–subir, `pnpm typecheck` y `pnpm build`, y corregir lo que falle
- [X] T070 Recorrer los escenarios manuales 1–16 de `quickstart.md` en local, en PC y con ancho de teléfono, y anotar cualquier desviación como tarea nueva
- [X] T071 [P] Crear `docs/decisiones/0008-sesion-y-verificacion-por-peticion.md` (complementa ADR-0005, que sigue vigente): jornada de 12 h con la tabla `user_session`, verificación del usuario y la sesión en la base en cada petición (R3), cookie `SameSite=None; Secure` mientras no haya dominio propio y `Strict` después (R5), código de instalación (R7) y bloqueo de inicio de sesión por nombre calculado desde la auditoría (R6). Agregarlo al índice de `docs/decisiones/README.md`
- [X] T072 Ejecutar `/security-review` y `/code-review` sobre la rama `001-usuarios-autenticacion-permisos`, corregir los hallazgos confirmados y repetir T069. Requisito para integrar a `main` (constitución, "Flujo de trabajo")
- [ ] T073 **Después de integrar a `main` (dueño y asistente):** con el despliegue terminado, seguir la sección "Producción" de `quickstart.md`: instalar desde `https://sht-gestion-app.pages.dev` con el código, medir el inicio de sesión con la instancia activa (SC-002 < 3 s) y anotar el arranque en frío (R13), probar en Chrome o Edge y reemplazar el valor del secreto `setup-code` (`docs/despliegue.md` §9.1). Registrar los tiempos en `CHANGELOG.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de Setup; bloquea todas las historias.
- **US1 (fase 3)**: depende de la fase 2. Es el MVP: sin sesión no se puede usar ninguna otra historia desde la app.
- **US2 (fase 4)**: depende de la fase 2; sus pruebas de la API usan las rutas `/_test/` y no dependen de otras historias. El frontend (T038, T039) depende de US1 (`app-shell.tsx`, `client.ts`).
- **US3, US4, US5 (fases 5–7)**: dependen de la fase 2; sus pantallas usan `RequireAuth`, `AppShell` y el cliente de US1. Las filas de la matriz (T042, T049, T055) dependen de T036 (US2).
- **Polish (fase 8)**: depende de las historias que se entreguen. T062 (manual) debe estar hecho antes de integrar a `main`, o el despliegue de la API fallará al no encontrar los secretos. T072 (revisión) va justo antes de integrar y T073 (validación en producción) después.

### User Story Dependencies

- **US1 (P1)**: solo la fase 2.
- **US2 (P1)**: la fase 2 (API); US1 para su parte de frontend.
- **US3 (P2)**: la fase 2 y US1 (pantallas); T042 después de T036.
- **US4 (P2)**: la fase 2 y US1 (pantallas); T049 después de T036.
- **US5 (P3)**: la fase 2 y US1 (pantallas); su recorrido completo (T054) es más útil después de US3 y US4, pero cada acción se prueba con las fábricas de `conftest.py`.

### Within Each User Story

- Pruebas primero (deben fallar) → servicios → endpoints → frontend → tipos generados.
- Cada historia termina con su checkpoint antes de pasar a la siguiente prioridad.

### Parallel Opportunities

- Fase 1: T002, T003, T004 en paralelo después de T001.
- Fase 2: T006–T011 y T020–T022 en paralelo; T012 → T013 → T014 → T015 → T016 en secuencia.
- Dentro de cada historia, las pruebas marcadas [P] en paralelo; en US1, las pantallas T031–T033 en paralelo.
- Con la fase 2 terminada, el backend de US3, US4 y US5 puede avanzar en paralelo (archivos distintos), coordinando las filas de `MATRIX`.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 juntas:
Task: "Pruebas de instalación en backend/tests/test_setup.py"
Task: "Pruebas de sesión en backend/tests/test_auth_session.py"
Task: "Pruebas de cambio de contraseña propia en backend/tests/test_password.py"

# Pantallas de US1 juntas (después de T028–T030):
Task: "frontend/src/app/instalacion/page.tsx"
Task: "frontend/src/app/ingresar/page.tsx"
Task: "frontend/src/app/cambiar-clave/page.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 (Setup) y fase 2 (Foundational).
2. Fase 3 (US1): instalación, ingreso, jornada y cambio de contraseña.
3. **Parar y validar**: escenarios 1–3, 13 y 14 de `quickstart.md`.
4. Seguir con US2: con US1 y US2 el sistema ya es seguro para construir encima.

### Incremental Delivery

1. Setup + Foundational → base lista.
2. US1 → MVP de acceso.
3. US2 → matriz de permisos y revocación inmediata (criterio de terminado de la etapa).
4. US3 → empleados con su propio usuario.
5. US4 → PIN listo para la etapa 1.3.
6. US5 → consulta de auditoría.
7. Polish → secretos, documentación, ADR-0008, validación, revisión (T072), integración a `main` y validación en producción (T073).

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Cada commit referencia los RF/FR que toca, en español.
- Las rutas `/_test/` existen solo en las pruebas; no se registran en `app/main.py`.
- Las pruebas que necesitan Postgres llevan la marca `db` y se saltan sin `DATABASE_URL`.
- Producción sin dominio propio es solo para pruebas (ADR-0005); probar en Chrome o Edge.
