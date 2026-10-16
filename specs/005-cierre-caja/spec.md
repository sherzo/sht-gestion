# Feature Specification: Caja: egresos, cierre y cuadre (etapa 1.4)

**Feature Branch**: `005-cierre-caja`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Etapa 1.4 — Caja: egresos de caja con motivo (RF-32), cierre de caja con esperado por método de pago, contado o verificado y diferencias (RF-31), cierres inmutables y correcciones con movimientos nuevos (RF-33, RN-12), y reversión de anulaciones de ventas con la caja ya cerrada en la caja abierta del equipo desde el que el admin anula (RF-27, PRD v0.11). La apertura de caja (RF-29, RF-30, RN-16) ya se entregó en la 1.3. Terminada cuando el cierre de un día de prueba se completa en menos de 10 minutos y cuadra con las ventas, el vuelto, las anulaciones y los egresos (docs/plan-de-fases.md §1.4)."

**Requisitos del PRD**: RF-27 (reversión con la caja cerrada, PRD v0.11), RF-31 a RF-33 (RF-32 y la matriz de permisos con las aclaraciones del PRD v0.12), RN-12, RN-16 (también RF-29 y RF-30 ya entregados en la 1.3, RF-46 para la auditoría, RNF-02, RNF-05 y RNF-07; objetivo 3 y métrica "cierre de caja diario en menos de 10 minutos" del PRD §2). Decisiones técnicas previas: ADR-0003 (cola de salida e idempotencia) y ADR-0004 (dinero, cantidades y redondeo). Principios de la constitución: I (integridad monetaria), II (inmutabilidad de los cierres), III (las operaciones de caja viajan por la cola de salida para funcionar sin conexión en la 1.5), IV (permisos en el servidor, sin costos para el Vendedor) y VII (pruebas del cuadre de caja).

## Clarifications

### Session 2026-10-15

- Q: ¿Los egresos que registra el Vendedor deben requerir autorización del Admin, como los descuentos? → A: No; el Vendedor registra el egreso directamente, queda auditado y visible en el cierre, y solo el Admin lo anula.
- Q: ¿De qué métodos puede salir un egreso? → A: De cualquier método de pago (por ejemplo, un delivery pagado por pago móvil o Binance desde la cuenta del negocio). Los que no son en efectivo exigen referencia, como los cobros (RF-24); el tope del esperado aplica solo al efectivo, porque las cuentas pueden tener dinero de otros días (PRD v0.12, sesión 2026-10-16).
- Q: ¿Hace falta registrar dinero que entra a la caja sin ser una venta (cambio de USD por Bs en la gaveta, reposición de sencillo)? → A: No; solo egresos. Cualquier diferencia por cambio de moneda o reposición se explica en la observación del cierre.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cierre de caja con cuadre por método de pago (Priority: P1)

Al terminar el día, el vendedor cierra la caja de su equipo. El sistema le muestra, por
cada método de pago y en su moneda, lo que debería haber: el fondo inicial (en
efectivo), más lo cobrado, menos el vuelto entregado, menos las devoluciones por
anulaciones, menos los egresos. El vendedor cuenta el efectivo y verifica los pagos
electrónicos (pago móvil, punto de venta, Zelle, USDT) contra el banco o el lote del
punto, escribe lo contado o verificado por método y el sistema calcula la diferencia de
cada uno. Al confirmar, el cierre queda guardado y ya no se puede cambiar.

**Why this priority**: cuadrar la caja diaria por método de pago sin cálculos manuales es
un objetivo del negocio (PRD §2) y la condición para dar por terminada la etapa.

**Independent Test**: con caja abierta con 500,00 Bs y 20,00 USD de fondo, registrar
ventas pagadas en Efectivo USD, Pago móvil y Efectivo Bs (una con vuelto), cerrar la
caja y comprobar que el esperado de cada método coincide con el cálculo a mano;
escribir un contado con 1,00 USD de menos en Efectivo USD y ver la diferencia −1,00.
Intentar vender después del cierre y ver que pide abrir una caja nueva.

**Acceptance Scenarios**:

1. **Given** una caja con fondo 500,00 Bs y 20,00 USD, una venta cobrada con 50,00 USD
   en Efectivo USD y vuelto de 2,30 USD en Efectivo USD, y otra cobrada con 730,00 Bs
   por Pago móvil, **When** el vendedor inicia el cierre, **Then** ve esperado
   Efectivo USD 67,70, Efectivo Bs 500,00, Pago móvil 730,00 Bs y 0,00 en los demás
   métodos (RF-31).
2. **Given** el resumen del cierre, **When** el vendedor escribe lo contado o
   verificado en cada método, **Then** el sistema muestra la diferencia de cada uno
   (contado − esperado), en su moneda, como sobrante (+) o faltante (−).
3. **Given** un método con diferencia distinta de cero, **When** el vendedor confirma
   el cierre, **Then** el sistema le pide una observación antes de guardarlo.
4. **Given** el cierre confirmado, **When** se consulta, **Then** muestra quién abrió y
   quién cerró, cuándo, el fondo, el esperado, lo contado y la diferencia por método, y
   la observación (RF-31).
5. **Given** una caja cerrada, **When** alguien intenta modificar o borrar el cierre o
   sus montos (incluso directamente en la base de datos), **Then** no es posible
   (RF-33, RN-12).
6. **Given** una caja cerrada, **When** el vendedor intenta vender en ese equipo,
   **Then** el sistema le pide abrir una caja nueva (RF-30).
7. **Given** el cierre con diferencias, **When** se guarda, **Then** el Admin recibe
   una alerta con la caja, el equipo, quién cerró y la diferencia de cada método.
8. **Given** un usuario de Almacén, **When** intenta cerrar una caja o ver su cuadre,
   **Then** el servidor lo rechaza.

---

### User Story 2 - Egresos de caja (Priority: P1)

Durante el día sale dinero de la caja que no es vuelto: compra de agua o artículos de
limpieza, pago de un delivery, retiro del dueño. El vendedor registra cada egreso con el
método del que sale (efectivo, pago móvil, Binance u otro), el monto, el motivo y, si no
es efectivo, la referencia. El egreso resta del esperado de ese método al cerrar.

**Why this priority**: sin egresos registrados la caja nunca cuadra; son frecuentes en
un negocio pequeño.

**Independent Test**: con caja abierta y 20,00 USD de fondo, registrar un egreso de
5,00 USD en Efectivo USD con el motivo "Compra de botellones de agua"; comprobar que el
esperado de Efectivo USD baja a 15,00 y que el egreso aparece en el cierre y en la
auditoría. Registrar un egreso de 300,00 Bs por Pago móvil con referencia y ver que resta
de ese método. Intentar un egreso sin motivo, o por Pago móvil sin referencia, y ver que
se rechaza.

**Acceptance Scenarios**:

1. **Given** una caja abierta, **When** el vendedor registra un egreso de 5,00 USD en
   Efectivo USD con motivo, **Then** queda registrado con quién, cuándo, el método, el
   monto y el motivo, y resta 5,00 del esperado de Efectivo USD (RF-32).
2. **Given** un egreso sin motivo, con monto cero o negativo, o en un método que no es
   efectivo y sin referencia, **When** se intenta registrar, **Then** se rechaza.
3. **Given** un egreso en efectivo mayor que el efectivo esperado en ese método en ese
   momento, **When** se intenta registrar, **Then** se rechaza indicando el efectivo
   disponible. En los demás métodos no hay tope: la cuenta puede tener dinero de otros
   días.
4. **Given** un egreso registrado por error, **When** el Admin lo anula con motivo
   mientras la caja sigue abierta, **Then** el egreso no se borra: queda anulado, deja
   de restar del esperado y la anulación queda en la auditoría (RF-33).
5. **Given** un equipo sin caja abierta, **When** se intenta registrar un egreso,
   **Then** se rechaza.
6. **Given** un egreso, **When** se registra o se anula, **Then** queda en la
   auditoría (RF-46).

---

### User Story 3 - Anulación de una venta con la caja ya cerrada (Priority: P2)

El Admin anula una venta de un día anterior, cuya caja ya está cerrada. El stock vuelve
como siempre, pero el dinero se devuelve desde la caja abierta del equipo desde el que el
Admin anula, porque es de ahí de donde sale físicamente. El cierre anterior no cambia.

**Why this priority**: es la regla decidida en el PRD v0.11; sin ella, una anulación
posterior al cierre no tendría dónde reflejar el dinero o alteraría un cierre
inmutable.

**Independent Test**: cerrar la caja del día con una venta `A-000001` cobrada en
Efectivo USD; abrir caja nueva en el mismo equipo y anular `A-000001` como Admin;
comprobar que el stock vuelve, que el cierre anterior sigue idéntico y que la caja
nueva muestra la devolución restando de su esperado de Efectivo USD.

**Acceptance Scenarios**:

1. **Given** una venta cuya caja sigue abierta, **When** el Admin la anula desde
   cualquier sesión, **Then** las devoluciones van a la caja de la venta, como en la
   etapa 1.3 (RF-27).
2. **Given** una venta cuya caja ya está cerrada, **When** el Admin la anula desde un
   equipo registrado con caja abierta, **Then** las devoluciones por los pagos (neto del
   vuelto) se registran en la caja abierta de ese equipo y el cierre de la caja original
   no cambia (RF-27, RF-33).
3. **Given** una venta cuya caja ya está cerrada, **When** el Admin intenta anularla
   desde un navegador que no es un equipo registrado, o desde un equipo sin caja
   abierta, **Then** el sistema no lo permite y le indica que debe hacerlo desde un
   equipo con caja abierta (y abrirla si hace falta).
4. **Given** una anulación de una venta de caja cerrada, **When** se consulta la venta,
   **Then** se ve en qué caja se devolvió el dinero; y al consultar el cierre original,
   se ve que esa venta fue anulada después del cierre, sin que cambien sus montos.

---

### User Story 4 - Consulta de cajas y cierres (Priority: P2)

El Admin consulta las cajas por fecha, equipo, quién abrió o cerró y estado (abierta o
cerrada), y abre el detalle de cada una: fondo, ventas, cobros por método, vuelto,
devoluciones, egresos y, si está cerrada, el cuadre con las diferencias. El Vendedor ve
la caja abierta de su equipo y los cierres que él mismo hizo hoy.

**Why this priority**: el Admin necesita revisar las diferencias y el historial de
cierres, pero el negocio puede cerrar caja sin esta consulta los primeros días.

**Independent Test**: con cajas de dos equipos y dos días, comprobar que el Admin filtra
y ve todas con su cuadre, y que el Vendedor solo ve la caja abierta de su equipo y sus
cierres de hoy, sin costos.

**Acceptance Scenarios**:

1. **Given** cajas de varios días y equipos, **When** el Admin filtra por rango de
   fechas y equipo, **Then** ve solo esas cajas, con fechas `dd/mm/aaaa` y montos
   `1.234,56`, y las que tienen diferencias resaltadas.
2. **Given** el detalle de una caja, **When** lo abre el Admin, **Then** ve el
   movimiento de dinero por método (fondo, cobros, vuelto, devoluciones, egresos) y la
   lista de pagos electrónicos con su referencia, y puede ir a cada venta.
3. **Given** un Vendedor, **When** consulta cajas, **Then** solo recibe la caja abierta
   de su equipo y los cierres que hizo hoy (hora de Caracas), nunca costos ni márgenes.

---

### User Story 5 - Cierre de una caja por el Admin desde otro equipo (Priority: P3)

Si un equipo se daña, se pierde o se revoca con la caja abierta, esa caja quedaría
abierta para siempre. El Admin puede cerrarla desde su propia sesión, escribiendo lo
contado y verificado, con una observación obligatoria.

**Why this priority**: es un caso poco frecuente, pero sin él una caja huérfana no
podría cerrarse nunca.

**Independent Test**: revocar un equipo con caja abierta; como Admin, cerrar esa caja
desde otro navegador con observación; comprobar que queda cerrada con quién la cerró y
desde dónde.

**Acceptance Scenarios**:

1. **Given** una caja abierta en otro equipo, **When** el Admin la cierra desde su
   sesión con lo contado y una observación, **Then** queda cerrada como cualquier
   cierre, marcando que se cerró fuera de su equipo.
2. **Given** un Vendedor, **When** intenta cerrar la caja de otro equipo, **Then** el
   servidor lo rechaza.
3. **Given** una caja cerrada por el Admin desde otro equipo, **When** llega al
   servidor una venta de esa caja creada antes del cierre (por ejemplo, desde la cola
   del equipo), **Then** la venta se registra igual en su caja, el cierre no cambia y se
   genera una alerta "Operación posterior al cierre" para el Admin.

---

### Edge Cases

- **Operaciones pendientes de envío en el equipo**: el cierre no se permite mientras el
  equipo tenga ventas, egresos u otras operaciones de esa caja sin enviar o rechazadas
  sin resolver; se indica cuáles son.
- **Venta a medio hacer al cerrar**: el borrador vive solo en la pantalla de venta; al
  ir a cerrar ya no existe y nunca se registra en la caja cerrada.
- **Solicitud de descuento pendiente al cerrar**: queda sin uso porque su venta no se
  registró; el Admin la ve en Pendientes y la rechaza.
- **Operaciones pendientes de otro vendedor**: una venta o un egreso de otro usuario
  espera en la cola a que ese usuario vuelva a ingresar en el equipo y bloquea el
  cierre; la pantalla indica quién debe ingresar. Si no puede, el Admin cierra la caja
  desde otro equipo (User Story 5).
- **Caja abierta de un día anterior**: se puede vender y cerrar normalmente; el sistema
  avisa que la caja está abierta desde otro día. El cierre muestra la fecha de apertura
  y la de cierre.
- **Caja sin movimientos**: se puede cerrar; el esperado es el fondo inicial.
- **Método sin movimientos**: aparece con esperado 0,00 y no exige escribir contado (se
  toma 0,00 salvo que el vendedor escriba otro valor).
- **Contado negativo**: no se acepta.
- **Vuelto entregado en un método electrónico** (por ejemplo, pago móvil al cliente):
  resta del esperado de ese método.
- **Anulación de una venta de la misma caja todavía abierta**: la devolución resta del
  esperado (pago) y el vuelto devuelto suma (RF-27); el cuadre lo refleja.
- **Anulación de una venta de caja cerrada que se pagó en un método distinto al
  disponible**: la devolución se registra en el mismo método y moneda del pago original,
  aunque la caja nueva no tenga efectivo suficiente; el sistema lo advierte, pero no lo
  impide (el dinero ya fue devuelto al cliente).
- **Dos vendedores en el mismo equipo**: cualquiera de los dos puede registrar egresos y
  cerrar la caja; el cierre guarda quién la abrió y quién la cerró (RN-16).
- **Tasa BCV**: el esperado y el contado se manejan en la moneda de cada método; el
  cierre no convierte entre monedas ni usa la tasa del día. El resumen puede mostrar un
  total de referencia en USD solo con la tasa guardada en cada pago (RN-05).
- **Sobrepago** (vuelto menor que el excedente, etapa 1.3): el dinero que entró queda en
  la caja; el esperado lo incluye.
- **Equipo revocado con caja abierta**: no registra egresos ni cierra desde ese equipo;
  el Admin la cierra desde otro equipo (User Story 5).
- **Cambio de moneda o reposición de sencillo en la gaveta**: no se registra; genera
  diferencias opuestas en Efectivo Bs y Efectivo USD (o un sobrante) que el vendedor
  explica en la observación obligatoria del cierre (FR-010).
- **Corrección después del cierre**: el cierre no se edita; un error se corrige con un
  movimiento nuevo en la caja abierta (por ejemplo, un egreso) o se explica en la
  observación (RF-33).

## Requirements *(mandatory)*

### Functional Requirements

**Egresos**

- **FR-001**: Admin y Vendedor MUST poder registrar un egreso en la caja abierta de su
  equipo, con cualquier método de pago, monto mayor que cero en la moneda del método y
  motivo obligatorio de 5 a 200 caracteres (RF-32). Los métodos que no son en efectivo
  MUST exigir la referencia de la operación (1 a 60 caracteres), como los cobros (RF-24). El egreso del
  Vendedor MUST NOT requerir autorización del Admin; queda auditado y visible en el
  cierre.
- **FR-002**: Un egreso en efectivo (Efectivo Bs o Efectivo USD) MUST NOT superar el
  efectivo esperado de ese método en la caja en ese momento. Los demás métodos no tienen
  tope.
- **FR-003**: Los egresos MUST ser inmutables. El Admin MUST poder anular un egreso con
  motivo mientras su caja esté abierta; la anulación deja el egreso visible como anulado
  y lo excluye del esperado (RF-33, RN-12). Con la caja cerrada, el egreso ya no se
  anula.
- **FR-004**: Los egresos MUST viajar por la cola de salida con su identificador del
  equipo; reenviar un egreso MUST NOT duplicarlo (ADR-0003).

**Cierre y cuadre**

- **FR-005**: Admin y Vendedor MUST poder cerrar la caja abierta de su equipo (RF-31).
- **FR-006**: El sistema MUST calcular el esperado de cada uno de los seis métodos de
  pago en su moneda: fondo inicial (solo Efectivo Bs y Efectivo USD) + cobros − vuelto
  entregado − devoluciones por anulación + vuelto devuelto por anulación − egresos no
  anulados, considerando solo los movimientos de esa caja (RF-31).
- **FR-007**: El cálculo del esperado MUST dar el mismo resultado en el equipo y en el
  servidor, con casos de prueba compartidos que ambos ejecutan (ADR-0004, principio
  VII).
- **FR-008**: Al cerrar, el usuario MUST ver el esperado por método y escribir lo
  contado (efectivo) o verificado (métodos electrónicos) por método, con monto mayor o
  igual que cero; el sistema MUST mostrar la diferencia (contado − esperado) por método
  antes de confirmar.
- **FR-009**: Para ayudar a verificar, el cierre MUST mostrar por cada método
  electrónico la lista de cobros, vueltos y devoluciones con su referencia y venta.
- **FR-010**: Si algún método tiene diferencia distinta de cero según el esperado que ve
  el usuario, el cierre MUST exigir una observación (5 a 500 caracteres); sin
  diferencias, la observación es opcional. Si el servidor recalcula otro esperado
  (FR-012), el cierre se guarda igual y la alerta avisa al Admin.
- **FR-011**: El cierre MUST guardar quién lo hizo, cuándo, desde qué equipo, y por cada
  método el esperado, lo contado y la diferencia; la caja pasa a cerrada en la misma
  operación (RF-31).
- **FR-012**: El servidor MUST recalcular el esperado al recibir el cierre; si difiere
  del que vio el usuario (por ejemplo, llegó una operación que el equipo no tenía), el
  cierre se guarda con el esperado del servidor, se conserva el del equipo y se genera
  una alerta para el Admin.
- **FR-013**: El cierre MUST viajar por la cola de salida con su identificador del
  equipo; reenviarlo MUST NOT duplicarlo ni cerrar otra caja (ADR-0003).
- **FR-014**: El equipo MUST NOT permitir cerrar mientras tenga operaciones de esa caja
  pendientes de envío o rechazadas sin resolver, y MUST indicar cuáles son.
- **FR-015**: Una caja cerrada y su cierre MUST ser inmutables, también ante cambios
  directos en la base de datos; no admite ventas, egresos ni un segundo cierre (RF-33,
  RN-12).
- **FR-016**: Un cierre con alguna diferencia distinta de cero MUST generar una alerta
  para el Admin con la caja, el equipo, quién cerró y la diferencia por método.
- **FR-017**: Tras el cierre, el equipo MUST quedar sin caja abierta: para vender o
  registrar egresos hay que abrir una caja nueva (RF-30).
- **FR-018**: El Admin MUST poder cerrar desde su sesión una caja abierta de otro equipo
  (vigente o revocado), con lo contado y una observación obligatoria; el cierre queda
  marcado como hecho fuera del equipo. El Vendedor MUST NOT cerrar cajas de otro equipo.
- **FR-019**: Si llega una venta o un egreso para una caja ya cerrada (creado en el
  equipo antes de que el Admin la cerrara desde otro lugar), el servidor MUST
  registrarlo en su caja sin cambiar el cierre y MUST generar una alerta "Operación
  posterior al cierre" para el Admin (principio III: no se pierde una venta).

**Anulación con la caja cerrada**

- **FR-020**: Al anular una venta cuya caja sigue abierta, las devoluciones MUST ir a esa
  caja, como en la etapa 1.3 (RF-27).
- **FR-021**: Al anular una venta cuya caja ya está cerrada, las devoluciones de los
  pagos y el vuelto devuelto MUST registrarse, en sus mismos métodos y monedas, en la
  caja abierta del equipo desde el que el Admin anula; el cierre original MUST NOT
  cambiar (RF-27, RF-33, PRD v0.11).
- **FR-022**: Si la caja de la venta está cerrada y el Admin no está en un equipo
  registrado y vigente con caja abierta, la anulación MUST rechazarse indicando que debe
  hacerse desde un equipo con caja abierta.
- **FR-023**: La venta anulada MUST mostrar en qué caja se registraron las devoluciones,
  y el detalle de la caja original MUST indicar las ventas anuladas después de su
  cierre, sin cambiar sus montos.

**Consulta, permisos y auditoría**

- **FR-024**: El Admin MUST poder consultar cajas por rango de fechas, equipo, quién
  abrió o cerró, estado y si tienen diferencias, y abrir su detalle con el movimiento de
  dinero por método, los pagos con referencia, los egresos, las anulaciones y el cuadre.
- **FR-025**: El Vendedor MUST ver solo la caja abierta de su equipo (con su esperado
  actual por método) y los cierres que él hizo hoy (hora de Caracas), sin costos ni
  márgenes; el servidor lo impone (matriz de permisos).
- **FR-026**: El Almacén MUST NOT registrar egresos, cerrar cajas ni consultarlas.
- **FR-027**: Se MUST auditar: registro y anulación de egresos, cierre de caja (con las
  diferencias), cierre por el Admin desde otro equipo y anulación de una venta con
  devolución en otra caja (RF-46).
- **FR-028**: Montos con formato `1.234,56` en la moneda de cada método, fechas
  `dd/mm/aaaa` y hora de Caracas (RNF-07); egresos y cierre usables en PC, tablet y
  teléfono (RNF-02).

### Key Entities *(include if feature involves data)*

- **Caja**: la de la etapa 1.3 (equipo, quién abrió, cuándo, fondo inicial en Bs y USD)
  más estado cerrada, quién cerró, cuándo, desde qué equipo y observación.
- **Egreso**: caja, método de pago, monto en su moneda, motivo, referencia (si no es
  efectivo), quién y cuándo; con
  su anulación (quién, cuándo y motivo) si la tiene.
- **Conteo del cierre**: una fila por método de pago de la caja cerrada: esperado según
  el servidor, esperado que vio el equipo, contado o verificado y diferencia.
- **Pago** (de la 1.3): las devoluciones por anulación ahora pueden pertenecer a una caja
  distinta de la de la venta.
- **Operación de la cola de salida**: suma los tipos registro de egreso y cierre de
  caja. La anulación de un egreso la hace el Admin con conexión y no viaja por la cola.
- **Alerta**: se amplía con diferencia en el cierre, esperado distinto entre el equipo y
  el servidor, y operación posterior al cierre.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El cierre de un día de prueba (al menos 30 ventas con los seis métodos,
  vuelto, 2 anulaciones y 3 egresos) se completa en menos de 10 minutos, contando el
  efectivo y verificando los pagos electrónicos (PRD §2, plan de fases §1.4).
- **SC-002**: En ese día de prueba, el esperado de cada método coincide exactamente con
  el cálculo independiente a partir de las ventas, el vuelto, las anulaciones y los
  egresos (0 céntimos de diferencia).
- **SC-003**: El 100 % de los casos compartidos del esperado da el mismo resultado en el
  equipo y en el servidor.
- **SC-004**: Reenviar 10 veces el mismo egreso o el mismo cierre deja exactamente un
  egreso o un cierre.
- **SC-005**: Ningún cierre, conteo ni egreso puede modificarse ni borrarse, verificado
  con cambios directos en la base de datos.
- **SC-006**: Tras anular una venta de una caja cerrada, el cierre original conserva
  exactamente sus montos y la caja abierta refleja la devolución en su esperado.
- **SC-007**: Cada permiso de esta etapa (registrar y anular egresos, cerrar caja propia
  y de otro equipo, consultar cajas) está cubierto por pruebas por rol en el servidor, y
  ninguna respuesta al Vendedor contiene costos ni márgenes.
- **SC-008**: Todo cierre con diferencias, esperado distinto u operación posterior al
  cierre genera su alerta (0 casos sin alerta en las pruebas).

## Assumptions

- La apertura de caja, el fondo inicial y una caja abierta por equipo ya existen desde la
  1.3; esta etapa no los cambia.
- El cierre funciona con conexión en esta etapa, pero egresos y cierre ya viajan por la
  cola de salida para no rehacerlos en la 1.5, igual que la venta y la apertura.
- El cierre no es "a ciegas": el PRD indica que el sistema muestra lo esperado y el
  vendedor escribe lo contado (RF-31).
- Los egresos pueden salir de cualquier método de pago (Clarifications). Un pago a un
  proveedor por una compra no es un egreso de caja: es parte de las compras.
- Los egresos del Vendedor no requieren autorización del Admin; quedan auditados y
  visibles en el cierre. Solo el Admin anula egresos.
- No hay ingresos de caja distintos de las ventas ni cambios de moneda dentro de la
  gaveta (por ejemplo, reponer sencillo o cambiar USD por Bs a mitad del día) porque el
  PRD no los contempla; el fondo se fija al abrir y la diferencia que eso cause se
  explica en la observación del cierre (confirmado en Clarifications).
- No hay categorías de egreso en esta etapa: el motivo es texto libre.
- Una caja puede quedar abierta más de un día; no se cierra automáticamente.
- El cierre no convierte monedas: cada método se cuadra en su propia moneda (USDT se
  cuenta como USD 1:1, RN-04).
- El reporte de ventas por método de pago (RF-39) es de la etapa 1.7; aquí solo se
  consulta cada caja.
- La impresión del cierre es Fase 2 (junto con la nota de entrega); en esta etapa se
  consulta en pantalla.
