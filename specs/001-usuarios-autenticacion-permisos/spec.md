# Feature Specification: Usuarios, autenticación y permisos (etapa 1.1a)

**Feature Branch**: `001-usuarios-autenticacion-permisos`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Etapa 1.1a (usuarios, autenticación y permisos) según docs/plan-de-fases.md. Toma el alcance de docs/PRD.md (RF-44 a RF-46, matriz de permisos §4, RNF-05, RNF-08) y de docs/decisiones/0005-autenticacion-y-permisos.md. Respeta lo que el plan asigna a otras etapas (sesión sin conexión en 1.5, equipos y descuentos en 1.3). Pantallas según docs/guia-de-estilos.md."

**Requisitos del PRD**: RF-44, RF-45, RF-46, RNF-05, RNF-08 (también RNF-02 y RNF-07 en las pantallas). Principios de la constitución: II (auditoría) y IV (permisos en el servidor).

## Clarifications

### Session 2026-10-07

- Q: ¿Cuánto tiempo puede trabajar alguien sin que el sistema le vuelva a pedir la contraseña? → A: Una jornada: hasta 12 horas desde que ingresó su contraseña (FR-005).
- Q: ¿Una misma persona necesita combinar roles? → A: No; un solo rol por usuario (FR-009).
- Q: ¿La pantalla de consulta de auditoría entra en esta etapa o en la 1.7? → A: Entra en la 1.1a, con filtros por usuario, tipo de acción y fechas (US5, FR-025).
- Q: ¿Cómo se protege la creación del primer administrador mientras el sistema está vacío? → A: Con un código de instalación secreto, de un solo uso, que solo conoce el dueño y se configura en el servidor (FR-001).
- Q: ¿El empleado debe cambiar obligatoriamente la contraseña asignada por el admin la primera vez que entra? → A: Sí; hasta cambiarla no puede hacer ninguna otra operación (FR-016a).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Puesta en marcha e inicio de sesión (Priority: P1)

El dueño pone en marcha el sistema creando su cuenta de administrador, la primera y
única vez que el sistema está vacío. Desde ahí, cada persona entra con su nombre de
usuario y su contraseña, trabaja sin que se le pida entrar otra vez mientras su sesión
siga vigente, y puede cerrar sesión cuando termina (por ejemplo, al dejar el equipo del
mostrador a otro compañero).

**Why this priority**: sin identidad no hay permisos ni auditoría, y ninguna etapa
posterior (productos, compras, ventas, caja) puede registrar quién hizo qué.

**Independent Test**: con el sistema vacío, crear el administrador inicial, cerrar
sesión, volver a entrar con sus credenciales y comprobar que se rechazan las
credenciales incorrectas.

**Acceptance Scenarios**:

1. **Given** un sistema sin ningún usuario, **When** alguien abre la app, **Then** se le
   ofrece crear el administrador inicial (código de instalación, nombre completo,
   usuario, contraseña) y, si el código es correcto, queda con la sesión iniciada como
   Admin.
2. **Given** un sistema sin ningún usuario, **When** alguien intenta crear el
   administrador inicial con un código de instalación incorrecto o sin él, **Then** el
   sistema lo rechaza, no crea ningún usuario y el intento queda auditado.
3. **Given** que ya existe al menos un usuario, **When** alguien intenta crear de nuevo
   un administrador inicial, **Then** el sistema lo rechaza y no crea ningún usuario.
4. **Given** un usuario activo, **When** ingresa su usuario (sin importar mayúsculas o
   minúsculas) y su contraseña correcta, **Then** entra y ve su nombre y su rol.
5. **Given** un usuario, **When** ingresa una contraseña incorrecta, **Then** ve un
   mensaje genérico ("Usuario o contraseña incorrectos") que no revela si el usuario
   existe, y el intento queda auditado.
6. **Given** un usuario con 5 intentos fallidos seguidos, **When** intenta entrar otra
   vez, aunque sea con la contraseña correcta, **Then** se le informa que debe esperar
   15 minutos.
7. **Given** un usuario con la sesión iniciada, **When** cierra sesión, **Then** vuelve
   a la pantalla de inicio de sesión y esa sesión ya no sirve para ninguna operación.
8. **Given** un usuario con la sesión iniciada, **When** sigue trabajando dentro del
   tiempo de sesión definido, **Then** no se le pide volver a ingresar su contraseña.
9. **Given** cualquier usuario con la sesión iniciada, **When** cambia su propia
   contraseña ingresando la actual y la nueva, **Then** la nueva pasa a ser la única
   válida y sus otras sesiones abiertas se cierran.

---

### User Story 2 - Permisos por rol verificados en el servidor (Priority: P1)

Cada usuario tiene un rol (Admin, Vendedor o Almacén) y solo puede hacer lo que la
matriz de permisos del PRD (§4) le permite. La protección no depende de lo que muestre
la pantalla: aunque alguien intente una operación prohibida por otros medios, el
servidor la rechaza.

**Why this priority**: es la base de seguridad de todas las etapas siguientes
(principio IV). Si no se resuelve aquí, cada módulo nuevo tendría que reinventarla.

**Independent Test**: con un usuario de cada rol, intentar cada función disponible en
esta etapa (gestión de usuarios, consulta de auditoría, cambio de contraseña propia,
PIN del admin) directamente contra el servidor y comprobar que solo se permite lo que
indica la matriz.

**Acceptance Scenarios**:

1. **Given** un Vendedor o un usuario de Almacén con la sesión iniciada, **When**
   intenta crear, editar o desactivar usuarios, aun sin pasar por la pantalla, **Then**
   el servidor rechaza la operación con un mensaje de permiso insuficiente y no cambia
   nada.
2. **Given** una persona sin sesión, **When** intenta cualquier función interna,
   **Then** el servidor la rechaza; solo responden sin sesión las funciones
   expresamente públicas (estado del sistema e inicio de sesión).
3. **Given** cualquier función nueva que se agregue al sistema, **When** no declara qué
   roles pueden usarla, **Then** nadie puede usarla (se niega por defecto).
4. **Given** un usuario con la sesión iniciada, **When** el admin le cambia el rol o lo
   desactiva, **Then** desde su siguiente operación rigen los permisos nuevos o pierde
   el acceso.
5. **Given** un usuario con la sesión iniciada, **When** abre la app, **Then** el menú
   solo le muestra las secciones a las que su rol tiene acceso.

---

### User Story 3 - Gestión de usuarios por el admin (Priority: P2)

El admin da de alta a sus empleados con nombre, usuario, rol y una contraseña inicial;
puede corregir sus datos, cambiarles el rol, restablecerles la contraseña cuando la
olvidan y desactivarlos cuando dejan de trabajar en el negocio, sin perder el
historial de lo que hicieron.

**Why this priority**: necesaria para que Vendedor y Almacén usen el sistema, pero el
dueño puede probar el resto de la etapa con su propia cuenta.

**Independent Test**: como Admin, crear un Vendedor, entrar con él, desactivarlo desde
otra sesión y comprobar que pierde el acceso; reactivarlo y restablecerle la contraseña.

**Acceptance Scenarios**:

1. **Given** el Admin en la gestión de usuarios, **When** crea un usuario con nombre
   completo, usuario, rol y contraseña inicial, **Then** el usuario puede entrar de
   inmediato, se le exige cambiar esa contraseña antes de cualquier otra operación y la
   creación queda auditada.
2. **Given** un usuario existente, **When** el Admin intenta crear otro con el mismo
   nombre de usuario (aunque cambien mayúsculas o minúsculas), **Then** el sistema lo
   rechaza.
3. **Given** un usuario activo, **When** el Admin lo desactiva, **Then** sus sesiones se
   cierran, no puede volver a entrar, sigue apareciendo en el historial y en la
   auditoría, y la acción queda auditada.
4. **Given** un usuario desactivado, **When** el Admin lo reactiva, **Then** puede volver
   a entrar con su contraseña.
5. **Given** un usuario que olvidó su contraseña, **When** el Admin le asigna una nueva,
   **Then** las sesiones abiertas de ese usuario se cierran, la contraseña anterior deja
   de servir, al entrar se le exige cambiar la nueva y la acción queda auditada (sin
   guardar ninguna contraseña en la auditoría).
6. **Given** que solo queda un Admin activo, **When** se intenta desactivarlo o quitarle
   el rol de Admin, **Then** el sistema lo impide.
7. **Given** el Admin, **When** intenta desactivarse a sí mismo, **Then** el sistema lo
   impide.
8. **Given** el Admin, **When** cambia el rol de un usuario, **Then** el cambio queda
   auditado con el rol anterior y el nuevo.
9. **Given** la lista de usuarios, **When** el Admin la consulta, **Then** ve nombre,
   usuario, rol, estado (activo o inactivo) y fecha de su último ingreso, y puede
   filtrar por rol y estado.

---

### User Story 4 - PIN del admin para autorizaciones (Priority: P2)

Cada administrador tiene un PIN numérico, distinto de su contraseña, que usará para
autorizar en el momento acciones de otros usuarios (en la etapa 1.3, los descuentos del
vendedor, RN-07). En esta etapa el admin define y cambia su PIN, y el sistema ofrece la
verificación del PIN con límite de intentos, lista para que la usen las etapas
siguientes.

**Why this priority**: es parte de RF-44 y la etapa 1.3 depende de ella, pero ninguna
operación de esta etapa la necesita todavía.

**Independent Test**: como Admin, definir el PIN; verificar un PIN correcto y uno
incorrecto; con 5 fallos seguidos comprobar que el PIN queda bloqueado aunque luego se
ingrese el correcto.

**Acceptance Scenarios**:

1. **Given** un Admin sin PIN, **When** lo define (4 a 6 dígitos) confirmando con su
   contraseña, **Then** el PIN queda activo y la acción queda auditada.
2. **Given** un Admin con PIN, **When** lo cambia confirmando con su contraseña,
   **Then** el PIN anterior deja de servir.
3. **Given** una autorización que pide el PIN de un Admin, **When** se ingresa el PIN
   correcto, **Then** se acepta y queda registrado qué Admin autorizó.
4. **Given** 5 intentos fallidos seguidos del PIN de un Admin, **When** se intenta otra
   vez, **Then** el PIN queda bloqueado por 15 minutos, aun con el PIN correcto, y cada
   intento (acertado o fallido) queda auditado.
5. **Given** un Vendedor o un usuario de Almacén, **When** intenta definir un PIN,
   **Then** el sistema lo rechaza: solo los Admin tienen PIN.

---

### User Story 5 - Registro y consulta de auditoría (Priority: P3)

Las acciones sensibles quedan registradas con quién, cuándo, qué cambió (antes y
después) y el motivo cuando aplica. En esta etapa se registran las acciones sobre
usuarios, sesiones y PIN; el registro queda preparado para que las etapas siguientes
agreguen cambios de precio, descuentos, anulaciones, ajustes y tasas (RF-46).

**Why this priority**: el registro en sí es obligatorio desde el primer día
(principio II), pero su consulta solo aporta valor cuando haya más actividad.

**Independent Test**: realizar acciones sensibles con distintos usuarios y comprobar
que cada una aparece en la auditoría con usuario, fecha y detalle, y que una acción
cuyo registro falla no se realiza.

**Acceptance Scenarios**:

1. **Given** cualquier acción sensible de esta etapa (ver FR-020), **When** se
   realiza, **Then** queda un registro con usuario, fecha y hora (`dd/mm/aaaa hh:mm`,
   hora de Caracas), tipo de acción, elemento afectado y valores anteriores y nuevos.
2. **Given** una acción sensible, **When** no puede registrarse en la auditoría,
   **Then** la acción tampoco se realiza.
3. **Given** un registro de auditoría, **When** alguien intenta modificarlo o borrarlo,
   **Then** no es posible, ni siquiera para un Admin.
4. **Given** el Admin, **When** consulta la auditoría, **Then** puede filtrar por usuario, tipo de acción y rango de fechas, con
   los registros más recientes primero.

---

### Edge Cases

- **Sistema sin conexión al iniciar sesión**: iniciar sesión requiere conexión; se
  muestra un mensaje claro. La sesión sin conexión es de la etapa 1.5.
- **Sesión vencida a mitad de un trabajo**: se pide entrar de nuevo sin perder lo que
  el usuario estaba escribiendo en el formulario abierto.
- **Usuario desactivado o con rol cambiado mientras tiene la sesión abierta**: la
  siguiente operación se rechaza o se evalúa con el rol nuevo.
- **El mismo usuario en dos equipos a la vez**: se permite; cerrar sesión en uno no
  cierra la del otro (salvo cambio o restablecimiento de contraseña, o desactivación).
- **Nombres de usuario con mayúsculas, espacios o acentos**: el usuario se compara sin
  distinguir mayúsculas; se aceptan letras sin acento, números, punto, guion y guion
  bajo, de 3 a 30 caracteres. El nombre de un usuario desactivado no se reutiliza, para
  que la auditoría y el historial no se confundan.
- **Último Admin activo**: no puede desactivarse ni cambiar de rol (US3).
- **Admin que olvidó su PIN**: lo redefine él mismo confirmando con su contraseña.
- **Único Admin que olvidó su contraseña**: no hay recuperación por correo; se resuelve
  con un procedimiento técnico documentado, fuera de la interfaz.
- **Intentos fallidos repartidos**: el contador de fallos de contraseña y de PIN se
  reinicia con un acierto.
- **Usuario con contraseña temporal que cierra la pantalla sin cambiarla**: en su
  siguiente ingreso se le vuelve a exigir el cambio.
- **Usuario Admin que también vende**: un Admin puede hacer todo lo que hace un
  Vendedor o Almacén (matriz §4).

## Requirements *(mandatory)*

### Functional Requirements

**Puesta en marcha e inicio de sesión (RF-44)**

- **FR-001**: El sistema MUST permitir crear un administrador inicial únicamente
  cuando no existe ningún usuario y con un código de instalación secreto que solo
  conoce el dueño y se configura en el servidor; una vez creado, esa opción deja de
  existir y el código ya no sirve. Los intentos con un código incorrecto se rechazan y
  quedan auditados, con el mismo límite de intentos de FR-004.
- **FR-002**: Los usuarios MUST iniciar sesión con nombre de usuario y contraseña; el
  nombre de usuario se compara sin distinguir mayúsculas y minúsculas.
- **FR-003**: Ante credenciales incorrectas, el sistema MUST mostrar un mensaje que no
  revele si el usuario existe.
- **FR-004**: Tras 5 intentos fallidos seguidos de contraseña con un mismo nombre de
  usuario, exista o no, el sistema MUST bloquear el inicio de sesión con ese nombre por
  15 minutos, con la misma respuesta en ambos casos (FR-003).
- **FR-005**: La sesión MUST mantenerse sin pedir de nuevo la contraseña durante una
  jornada: hasta 12 horas desde que el usuario ingresó su contraseña. Al cumplirse,
  el sistema pide entrar otra vez.
- **FR-006**: Los usuarios MUST poder cerrar sesión; una sesión cerrada no sirve para
  ninguna operación posterior.
- **FR-007**: Cualquier usuario MUST poder cambiar su propia contraseña indicando la
  actual; al hacerlo se cierran sus demás sesiones.
- **FR-008**: Las contraseñas MUST tener al menos 8 caracteres y MUST guardarse de forma
  que nadie, ni siquiera el Admin, pueda leerlas (RNF-05).

**Roles y permisos (RNF-05, principio IV)**

- **FR-009**: Cada usuario MUST tener exactamente un rol: Admin, Vendedor o Almacén.
  No se combinan roles.
- **FR-010**: El servidor MUST verificar el rol en cada operación según la matriz de
  permisos del PRD §4; la interfaz solo oculta lo que el rol no puede usar.
- **FR-011**: Toda función del sistema MUST declarar qué roles pueden usarla; una
  función sin declaración MUST quedar inaccesible para todos.
- **FR-012**: Sin sesión, solo MUST responder las funciones expresamente públicas
  (estado del sistema, inicio de sesión y creación del administrador inicial mientras
  el sistema esté vacío).
- **FR-013**: Desactivar un usuario o cambiar su rol MUST tener efecto desde su
  siguiente operación, aunque tenga una sesión abierta.
- **FR-014**: Las respuestas a Vendedor y Almacén MUST NOT incluir costos ni márgenes;
  esta regla queda establecida como base para las etapas que introduzcan esos datos.

**Gestión de usuarios (RF-45)**

- **FR-015**: El Admin MUST poder crear usuarios con nombre completo, nombre de usuario
  único, rol y contraseña inicial.
- **FR-016**: El Admin MUST poder editar el nombre completo y el rol, desactivar y
  reactivar usuarios y asignarles una contraseña nueva; los usuarios nunca se borran.
- **FR-016a**: Una contraseña asignada por el Admin (al crear el usuario o al
  restablecerla) MUST ser temporal: al entrar con ella, el usuario solo puede cambiarla
  por una propia, y el servidor rechaza cualquier otra operación hasta que lo haga. La
  contraseña nueva MUST ser distinta de la temporal.
- **FR-017**: Desactivar un usuario o restablecer su contraseña MUST cerrar todas sus
  sesiones abiertas.
- **FR-018**: El sistema MUST impedir que quede sin ningún Admin activo y que un Admin
  se desactive a sí mismo.
- **FR-019**: El Admin MUST poder ver la lista de usuarios con nombre, usuario, rol,
  estado y fecha del último ingreso, filtrable por rol y estado.

**Auditoría (RF-46, RNF-08)**

- **FR-020**: El sistema MUST auditar, en esta etapa: creación del administrador
  inicial e intentos con código de instalación incorrecto; inicios de sesión exitosos y fallidos; bloqueos por intentos fallidos;
  creación, edición, cambio de rol, desactivación y reactivación de usuarios;
  restablecimiento y cambio de contraseña; definición y cambio de PIN; y cada
  verificación de PIN, acertada o fallida.
- **FR-021**: Cada registro de auditoría MUST incluir usuario que actuó (si lo hay),
  fecha y hora, tipo de acción, elemento afectado, valores anteriores y nuevos y motivo
  cuando aplique; MUST NOT incluir contraseñas ni PIN.
- **FR-022**: Una acción sensible y su registro de auditoría MUST ocurrir juntos: si el
  registro falla, la acción no se realiza.
- **FR-023**: Los registros de auditoría MUST ser inmutables: nadie puede editarlos ni
  borrarlos.
- **FR-024**: El registro de auditoría MUST admitir los tipos de acción de etapas
  siguientes (precios, descuentos y su autorización, anulaciones, ajustes, tasas) sin
  rediseño.
- **FR-025**: El Admin MUST poder consultar la auditoría filtrando por usuario, tipo de
  acción y rango de fechas, con los
  registros más recientes primero.

**PIN del admin (RF-44, RN-07)**

- **FR-026**: Cada Admin MUST poder definir y cambiar un PIN de 4 a 6 dígitos,
  confirmando con su contraseña; solo los Admin tienen PIN.
- **FR-027**: El sistema MUST ofrecer la verificación del PIN de un Admin para
  autorizar acciones, registrando qué Admin autorizó.
- **FR-028**: Tras 5 verificaciones fallidas seguidas del PIN de un Admin, el sistema
  MUST bloquear ese PIN por 15 minutos.
- **FR-029**: El PIN MUST guardarse de forma que nadie pueda leerlo (RNF-05).

**Pantallas (RNF-02, RNF-07)**

- **FR-030**: La app MUST ofrecer las pantallas de: administrador inicial, inicio de
  sesión, inicio (con nombre, rol y menú según el rol), cambio de contraseña propia,
  PIN del admin, gestión de usuarios y consulta de auditoría, siguiendo `docs/guia-de-estilos.md`.
- **FR-031**: Las pantallas MUST poder usarse en teléfono, tablet y PC, en español, con
  fechas `dd/mm/aaaa` y hora de Caracas.

### Key Entities *(include if feature involves data)*

- **Usuario**: persona que usa el sistema. Nombre completo, nombre de usuario único,
  rol, estado (activo o inactivo), si su contraseña es temporal (FR-016a), fecha del
  último ingreso, contador de intentos fallidos y bloqueo temporal. Si es Admin, puede tener un PIN con su propio contador
  de intentos y bloqueo. Nunca se borra.
- **Rol**: Admin, Vendedor o Almacén; determina qué funciones puede usar según la matriz
  de permisos del PRD §4.
- **Sesión**: periodo en que un usuario puede operar sin volver a ingresar su
  contraseña. Se cierra al cerrar sesión, al cambiar o restablecer la contraseña, al
  desactivar al usuario o al vencer.
- **Registro de auditoría**: hecho inmutable sobre una acción sensible: quién, cuándo,
  qué acción, sobre qué elemento, valores antes y después, y motivo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Admin crea un usuario nuevo y ese usuario inicia sesión, en total, en
  menos de 2 minutos.
- **SC-002**: El inicio de sesión responde en menos de 3 segundos con una conexión
  normal.
- **SC-003**: El 100 % de las funciones de la etapa tiene pruebas automatizadas con
  cada rol y sin sesión, y ninguna permite una operación fuera de la matriz de
  permisos (criterio de terminado de la etapa 1.1a).
- **SC-004**: Un usuario desactivado no completa ninguna operación desde el momento de
  su desactivación.
- **SC-005**: El 100 % de las acciones de FR-020 aparece en la auditoría con usuario,
  fecha y detalle, y ningún registro de auditoría contiene contraseñas ni PIN.
- **SC-006**: Después de 5 intentos fallidos, ni la contraseña ni el PIN correctos
  sirven hasta que pasan 15 minutos.
- **SC-007**: Todas las pantallas de la etapa se usan en un teléfono de 360 px de ancho
  y en PC sin desplazamiento horizontal y con los contrastes de la guía de estilos.
- **SC-008**: Un usuario que entra al inicio de su jornada no vuelve a ingresar su
  contraseña durante 12 horas de trabajo, y pasadas las 12 horas se le pide de nuevo.
- **SC-009**: Ningún usuario completa una operación distinta de cambiar su contraseña
  mientras use una contraseña temporal asignada por el Admin.

## Assumptions

- Los usuarios se identifican con un nombre de usuario creado por el Admin, sin correo
  ni teléfono; por eso no hay recuperación de contraseña por correo (ADR-0005).
- Puede haber más de un Admin; cada uno tiene su propio PIN.
- Los registros de auditoría se conservan indefinidamente (el volumen esperado es bajo:
  pocos usuarios).
- Un Admin puede hacer todo lo que hacen Vendedor y Almacén (matriz §4).
- Bloqueo por intentos fallidos: 5 intentos y 15 minutos, tanto para la contraseña como
  para el PIN (ADR-0005 fija 5 intentos para el PIN; se aplica lo mismo a la
  contraseña).
- La contraseña inicial o restablecida la comunica el Admin al empleado en persona y es
  temporal (FR-016a); la del administrador inicial la elige él mismo y no es temporal.
- El único Admin que olvida su contraseña se recupera con un procedimiento técnico
  documentado en `docs/despliegue.md`, no desde la interfaz.
- **Fuera de alcance** (otras etapas): sesión sin conexión y funcionamiento offline
  (1.5); registro de equipos de mostrador y series (1.3); flujo de autorización de
  descuentos y uso real del PIN (1.3); auditoría de precios, ajustes, anulaciones y
  tasas (cada una en su etapa); compra del dominio propio.
- **Dependencias**: ADR-0005 (autenticación y permisos), `docs/modelo-de-datos.md`
  (usuarios y auditoría), `docs/guia-de-estilos.md` y el despliegue de la etapa 1.0.
  Mientras no exista el dominio propio, producción solo se usa para pruebas
  (ADR-0005).
