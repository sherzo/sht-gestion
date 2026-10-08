# Investigación (fase 0): usuarios, autenticación y permisos

Decisiones técnicas que resuelven lo que la especificación deja abierto. Parten de
ADR-0005 (autenticación y permisos), ADR-0001 (stack) y el código de la etapa 1.0.

## R1. Hash de contraseñas y PIN

- **Decisión:** `argon2-cffi` (`PasswordHasher`, Argon2id) con los parámetros por
  defecto de la librería en producción (64 MiB, 3 iteraciones). En pruebas se usan
  parámetros mínimos, configurables, para que la suite sea rápida.
- **Razón:** es lo que fija ADR-0005; `argon2-cffi` es la implementación de referencia
  en Python, sin servicios externos. `check_needs_rehash` permite subir el costo más
  adelante sin migrar datos.
- **Alternativas:** `pwdlib` y `passlib` (capas extra sin beneficio; `passlib` está sin
  mantenimiento); bcrypt (ADR-0005 ya eligió Argon2id).

## R2. Token de acceso

- **Decisión:** JWT firmado con HS256 (`PyJWT`), vida de 15 minutos, con `sub`
  (usuario), `sid` (sesión), `role` y `exp`. El frontend lo guarda solo en memoria.
  El secreto de firma (`JWT_SECRET`) vive en Secret Manager (`jwt-secret`).
- **Razón:** ADR-0005. El JWT permite a la app conocer la identidad sin consultar a la
  API, lo que la etapa 1.5 necesita para trabajar sin conexión.
- **Alternativas:** token opaco consultado en cada petición (perdería la identidad sin
  conexión); RS256 (dos claves sin necesidad: solo la API firma y verifica).

## R3. Verificación en cada petición (FR-013, FR-006, FR-016a, SC-004)

- **Decisión:** el JWT no es la fuente de verdad de los permisos. En cada petición
  autenticada la API lee, en una sola consulta por clave primaria, el usuario y su
  sesión (`sid`), y rechaza si el usuario está inactivo, la sesión fue cerrada o
  revocada, o la sesión venció. El rol que se aplica es el de la base de datos, no el
  del token. Si el usuario tiene contraseña temporal, solo se permiten las operaciones
  de la lista blanca (ver contrato).
- **Razón:** la especificación exige que desactivar, cambiar el rol o cerrar sesión
  tenga efecto desde la siguiente operación, no al vencer el token (15 minutos). El
  costo es una consulta por petición, irrelevante con pocos usuarios.
- **Alternativas:** lista de tokens revocados (más compleja e igual consulta la base);
  aceptar hasta 15 minutos de desfase (no cumple SC-004).

## R4. Sesión de 12 horas y token de renovación

- **Decisión:** una tabla `user_session` representa la jornada: se crea al ingresar la
  contraseña (inicio de sesión o instalación) y vence a las 12 horas
  (`expires_at = started_at + 12 h`, FR-005). El token de renovación es opaco (32 bytes
  aleatorios), se guarda como hash SHA-256 en `refresh_token`, rota en cada uso y nunca
  extiende la sesión más allá de `expires_at`.
- **Reutilización:** si llega un token ya rotado, se revoca la sesión completa (posible
  robo), salvo que haya sido rotado hace menos de 30 segundos (dos pestañas que renuevan
  a la vez): en ese caso se emite otro token de la misma sesión. El frontend además
  serializa la renovación entre pestañas con la Web Locks API.
- **Razón:** ADR-0005 (rotación, hash, revocable) más la duración aclarada en la
  especificación. Separar la sesión del token permite revocar la jornada entera de una
  vez (cerrar sesión, desactivar, cambiar contraseña).
- **Alternativas:** sesión deslizante (renovar extiende el plazo; contradice la
  aclaración de 12 horas); un solo token sin rotación (ADR-0005 exige rotación).

## R5. Cookie del token de renovación sin dominio propio

- **Decisión:** la cookie (`sht_refresh`, `HttpOnly`, ruta `/api/v1/auth`) toma su
  `SameSite`, `Secure` y dominio de la configuración:
  - local: `SameSite=Lax`, sin `Secure` (localhost:3000 y localhost:8000 son el mismo
    sitio);
  - producción con dominio propio: `SameSite=Strict`, `Secure` (ADR-0005);
  - producción **provisional** (`*.pages.dev` y `*.run.app` son sitios distintos):
    `SameSite=None`, `Secure`.
- **Riesgo aceptado:** con la configuración provisional, Safari (iPhone, Mac) bloquea la
  cookie entre sitios: allí la renovación falla y hay que volver a entrar cada 15
  minutos. Chrome y Edge funcionan. Es coherente con ADR-0005: producción sin dominio
  propio es solo para pruebas.
- **Protección contra CSRF:** `refresh` y `logout` exigen `Content-Type:
  application/json`, lo que obliga al navegador a hacer la consulta previa de CORS; un
  sitio no autorizado no puede completar la petición ni leer la respuesta.
- **Pendiente fuera de esta etapa:** al comprar el dominio, verificar cómo se apunta
  `api.<dominio>` a Cloud Run sin costo (mapeo de dominio de Cloud Run o proxy de
  Cloudflare) antes del uso real (fin de la etapa 1.2).

## R6. Bloqueos por intentos fallidos (FR-004, FR-028, SC-006)

- **Inicio de sesión: mismo comportamiento para todos los nombres.** El bloqueo se
  calcula desde `audit_log` por nombre de usuario normalizado, exista o no: se cuentan
  los `auth.login_failed` de ese nombre posteriores a su último `auth.login_succeeded`.
  Con 5 o más, el nombre queda bloqueado hasta 15 minutos después del fallo más
  reciente; mientras dura, no se verifica la contraseña y el intento se audita como
  `auth.login_locked` (no cuenta como fallo). Así el aviso de bloqueo no revela si el
  usuario existe (FR-003, FR-004). `app_user` no guarda contadores de inicio de sesión.
- **Tiempo de respuesta:** con un nombre inexistente se calcula igualmente un hash de
  referencia, para que el tiempo no delate al usuario (FR-003).
- **PIN:** contadores en `app_user` (`pin_failed_attempts`, `pin_locked_until`). Al
  quinto fallo seguido se bloquea 15 minutos; un acierto reinicia el contador. Aquí se
  acepta que el bloqueo distinga a un admin real: solo usuarios con sesión pueden
  verificar un PIN y los nombres de los admin no son secretos dentro del negocio.
- Mientras dura cualquier bloqueo, ni la credencial correcta sirve.
- **Alternativas:** límite por IP (Cloud Run detrás de proxies, poco fiable y con pocos
  usuarios no aporta); servicio externo de rate limiting (costo, RNF-03).

## R7. Instalación con código secreto (FR-001)

- **Decisión:** `SETUP_CODE` en Secret Manager (`setup-code`). `POST /setup` compara con
  `hmac.compare_digest`, toma un bloqueo transaccional (`pg_advisory_xact_lock`) y
  comprueba que no exista ningún usuario antes de crear el administrador. Si falta
  `SETUP_CODE`, la instalación está deshabilitada. Los fallos se auditan
  (`setup.failed`) y se cuentan desde la auditoría: con 5 fallos en los últimos 15
  minutos se rechaza todo intento hasta que pase el plazo.
- **Razón:** no hace falta una tabla nueva y el bloqueo evita que dos instalaciones
  simultáneas creen dos administradores.
- **Después de instalar:** el código deja de servir porque ya existen usuarios; se
  recomienda destruir el secreto (procedimiento en `docs/despliegue.md`).

## R8. Recuperación del único admin y comando de soporte

- **Decisión:** módulo `app/cli.py` con `reset-password <usuario>`: genera una
  contraseña temporal (FR-016a), cierra las sesiones del usuario y lo audita como acción
  de sistema. Se ejecuta desde la computadora del dueño con la cadena de conexión de
  migraciones. Procedimiento en `docs/despliegue.md`.
- **Alternativas:** pantalla de recuperación (no hay correo ni segundo factor que la
  proteja).

## R9. Permisos declarados y negación por defecto (FR-010, FR-011, SC-003)

- **Decisión:** cada endpoint declara su acceso con una dependencia:
  `require_roles(Role.ADMIN, ...)`, `require_authenticated()` o `public()`. Una prueba
  recorre todas las rutas de la aplicación y falla si alguna no tiene exactamente una
  declaración. Otra prueba parametrizada recorre la matriz de permisos del contrato y
  verifica, por endpoint, cada rol y la petición sin sesión.
- **Razón:** principio IV y ADR-0005 ("lo que no declara roles no se expone"). La prueba
  convierte la regla en algo que la CI hace cumplir.
- **Respuestas por rol (FR-014):** en esta etapa ningún endpoint devuelve costos. La
  regla se deja escrita en la convención de esquemas (`docs/arquitectura.md`) para
  1.1b.

## R10. Auditoría inmutable (FR-020 a FR-024)

- **Decisión:** tabla `audit_log` de solo inserción. La inmutabilidad se impone en la
  base: un trigger rechaza `UPDATE` y `DELETE`, y el rol `sht_api` no tiene permiso
  `DELETE` ni `TRUNCATE`. La función `record_audit(session, ...)` agrega el registro en
  la misma transacción que la acción; si falla, la transacción entera se deshace.
  Los fallos de inicio de sesión y de PIN se guardan en una transacción propia (con el
  aumento del contador, en el caso del PIN) y después se responde el error.
- **Códigos de acción** en inglés con punto (`user.created`), según ADR-0006; los textos
  en español viven en el frontend.
- **Consulta:** filtros por usuario, acción y rango de fechas; las fechas se interpretan
  en `America/Caracas` con la utilidad única de fecha de negocio (arquitectura §4.2),
  que se crea en esta etapa. Paginación por página y tamaño (volumen bajo).

## R11. Identificadores y nombres de usuario

- **Decisión:** UUIDv7 con `uuid.uuid7()` de Python 3.14 (modelo de datos §1.1).
  `username` se guarda normalizado en minúsculas, con índice único; validación
  `^[a-z0-9._-]{3,30}$` después de normalizar. Los usuarios desactivados conservan su
  nombre, así que nunca se reutiliza.

## R12. Frontend

- **Estado de sesión:** contexto de React con el token en memoria. Al cargar la app se
  intenta `POST /auth/refresh`; si falla, se va a `/ingresar`. Cliente HTTP único en
  `frontend/src/lib/api/` que agrega el token, renueva una vez ante un 401 y reintenta.
- **Tipos de la API:** generados del OpenAPI de FastAPI con `openapi-typescript` en
  `packages/shared/src/api/schema.d.ts` (arquitectura §2), con un script del monorepo.
- **Rutas (export estático, sin rutas dinámicas):** `/instalacion`, `/ingresar`, `/`
  (inicio), `/cambiar-clave`, `/mi-cuenta` (contraseña y PIN), `/usuarios`,
  `/auditoria`. La edición de usuarios se hace en diálogos dentro de `/usuarios`.
- **Componentes base** (guía de estilos §9, etapa 1.1a): botón, campo con etiqueta y
  error, mensaje de estado, diálogo, tabla responsive y menú por rol, en
  `frontend/src/components/ui/`. Íconos con `lucide-react` (licencia ISC, se incluyen
  solo los usados).
- **Formato:** `formatDateTime` (`dd/mm/aaaa hh:mm`, `America/Caracas`) en
  `packages/shared` (arquitectura §4.3).
- **Pruebas del frontend:** no se agrega un ejecutor de pruebas en esta etapa; las
  reglas críticas (permisos) se prueban en el servidor. Se valida con tipos, build y la
  guía de `quickstart.md`. El ejecutor llega con el módulo de dinero (etapa 1.3).

## R13. Rendimiento del inicio de sesión (SC-002)

- **Riesgo:** Cloud Run escala a cero; el primer inicio de sesión del día puede sumar el
  arranque en frío (2–5 s) al hash Argon2 (~0,1 s).
- **Decisión:** se mantiene `min-instances 0` (RNF-03) con `--cpu-boost`. SC-002 se mide
  con la instancia activa; el arranque en frío se registra en `quickstart.md` y se
  revisa al cerrar la etapa. Si molesta en el uso real, la opción es una instancia
  mínima en horario de trabajo, con su ADR de costo.

## R14. Cambios a documentos existentes

- PRD v0.7: precisar en RF-44/RF-45 la sesión de 12 horas, la contraseña temporal y la
  instalación con código (aclaraciones de la especificación; principio V).
- `docs/modelo-de-datos.md`: columnas nuevas de `app_user`, tabla `user_session`,
  ajustes de `refresh_token` y `audit_log`.
- `docs/arquitectura.md`: glosario (sesión, código de instalación, contraseña temporal)
  y convención de permisos por endpoint.
- `docs/despliegue.md`: secretos `jwt-secret` y `setup-code`, instalación inicial,
  recuperación del admin y configuración de la cookie.
- `docs/guia-de-estilos.md` §9: componentes e íconos definidos en esta etapa.
- ADR-0005 sigue vigente; los detalles de esta etapa (jornada con `user_session`,
  verificación por petición, cookie provisional, código de instalación y bloqueo por
  nombre) se registran en ADR-0008.
